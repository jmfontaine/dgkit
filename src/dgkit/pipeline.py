from contextlib import ExitStack
from pathlib import Path
from typing import IO, Callable, Iterator, cast

from lxml import etree
from rich.progress import (
    BarColumn,
    DownloadColumn,
    Progress,
    ProgressColumn,
    Task,
    TaskID,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
    TransferSpeedColumn,
)
from rich.text import Text

from dgkit.filters import Filter, FilterChain
from dgkit.parsers import get_parser
from dgkit.readers import GzipReader
from dgkit.summary import Summary, SummaryCollector
from dgkit.types import (
    Compression,
    DatabaseType,
    Element,
    FileFormat,
    Parser,
    Reader,
    Writer,
)
from dgkit.validation import TrackingElement, UnhandledElementError
from dgkit.writers import (
    FILE_WRITERS,
    get_database_writer,
    get_file_writer,
)


# Only labels have nested elements (sublabels contain <label> elements).
# Other entity types (artist, master, release) don't need parent checking.
_ENTITIES_WITH_NESTING = {"label"}


def find_elements(
    stream: IO[bytes], tag: str, limit: int | None = None
) -> Iterator[etree._Element]:
    """Yield root-level XML elements matching tag from stream.

    For labels, filters out nested elements (e.g., <label> inside <sublabels>).
    Other entity types don't have nesting and skip the parent check for performance.
    """
    check_parent = tag in _ENTITIES_WITH_NESTING
    context = etree.iterparse(stream, events=("end",), tag=tag)
    count = 0
    for _, elem in context:
        # Only labels need parent checking to filter sublabels
        if check_parent:
            parent = elem.getparent()
            if parent is None or parent.tag != "labels":
                continue

        yield elem
        elem.clear()
        while elem.getprevious() is not None:
            del elem.getparent()[0]
        count += 1
        if limit is not None and count >= limit:
            break


class ElementCountColumn(ProgressColumn):
    """Progress column showing completed/total with thousands separators."""

    def render(self, task: Task) -> Text:
        completed = int(task.completed)
        total = int(task.total) if task.total is not None else "?"
        if isinstance(total, int):
            return Text(f"{completed:,}/{total:,}", style="progress.download")
        return Text(f"{completed:,}/{total}", style="progress.download")


def execute(
    *,
    limit: int | None,
    parser: Parser,
    path: Path,
    reader: Reader,
    writer: Writer,
    fail_on_unhandled: bool = False,
    filter: Filter | None = None,
    on_progress_bytes: Callable[[int], None] | None = None,
    on_progress_element: Callable[[], None] | None = None,
    strict: bool = False,
    summary: SummaryCollector | None = None,
) -> None:
    """Execute the pipeline."""
    with reader.open(path) as stream:
        for elem in find_elements(stream, parser.tag, limit):
            # Wrap element for tracking if strict mode is enabled
            tracking_elem = TrackingElement(elem) if strict else None
            parse_elem = cast(Element, tracking_elem if tracking_elem else elem)

            try:
                records = list(parser.parse(parse_elem))
            except ValueError as e:
                if fail_on_unhandled:
                    raise
                element_id = elem.findtext("id") or elem.get("id") or "?"
                message = f"Parse error in {parser.tag} id={element_id}: {e}"
                if summary:
                    summary.record_unhandled(message)
                if on_progress_bytes is not None:
                    on_progress_bytes(reader.bytes_read)
                if on_progress_element:
                    on_progress_element()
                continue

            for record in records:
                if summary:
                    summary.record_read()
                if filter is not None:
                    filtered = filter(record)
                    if filtered is None:
                        if summary:
                            summary.record_dropped()
                        continue
                    if filtered is not record:
                        if summary:
                            summary.record_modified()
                    record = filtered
                writer.write(record)
                if summary:
                    summary.record_written()

            # Check for unhandled elements in strict mode
            if tracking_elem is not None:
                unaccessed = tracking_elem.get_unaccessed()
                if unaccessed:
                    element_id = elem.findtext("id") or elem.get("id") or "?"
                    paths = ", ".join(sorted(unaccessed))
                    message = f"Unhandled in {parser.tag} id={element_id}: {paths}"
                    if fail_on_unhandled:
                        raise UnhandledElementError(element_id, parser.tag, unaccessed)
                    if summary:
                        summary.record_unhandled(message)

            if on_progress_bytes is not None:
                on_progress_bytes(reader.bytes_read)
            if on_progress_element:
                on_progress_element()


COMPRESSION_EXTENSIONS: dict[Compression, str] = {
    Compression.bz2: ".bz2",
    Compression.gzip: ".gz",
    Compression.none: "",
}


def create_progress_bytes() -> Progress:
    """Create a Rich Progress bar for byte-based file processing."""
    return Progress(
        TextColumn("[bold blue]{task.description}"),
        BarColumn(),
        DownloadColumn(),
        TransferSpeedColumn(),
        TimeRemainingColumn(),
    )


def create_progress_elements() -> Progress:
    """Create a Rich Progress bar for element-based processing."""
    return Progress(
        TextColumn("[bold blue]{task.description}"),
        BarColumn(),
        ElementCountColumn(),
        TimeElapsedColumn(),
        TimeRemainingColumn(),
    )


class ProgressTracker:
    """Encapsulates progress bar setup and callbacks."""

    def __init__(
        self,
        stack: ExitStack,
        limit: int | None,
        show_progress: bool,
        valid_paths: list[Path],
    ) -> None:
        self._use_elements = limit is not None
        self._show_progress = show_progress
        self._bytes_completed = 0
        self._progress: Progress | None = None
        self._task_id: TaskID | None = None

        if show_progress:
            if self._use_elements:
                assert limit is not None  # _use_elements implies limit is set
                total = limit * len(valid_paths)
                self._progress = stack.enter_context(create_progress_elements())
            else:
                total = sum(p.stat().st_size for p in valid_paths)
                self._progress = stack.enter_context(create_progress_bytes())
            self._task_id = self._progress.add_task("Processing", total=total)

    def get_reader(self) -> Reader:
        """Get the reader for processing files."""
        return GzipReader()

    def on_bytes(self, bytes_read: int) -> None:
        """Callback for byte-based progress updates."""
        if self._progress and self._task_id is not None:
            self._progress.update(
                self._task_id, completed=self._bytes_completed + bytes_read
            )

    def on_element(self) -> None:
        """Callback for element-based progress updates."""
        if self._progress and self._task_id is not None:
            self._progress.advance(self._task_id)

    def advance_file(self, path: Path) -> None:
        """Update bytes_completed after processing a file."""
        self._bytes_completed += path.stat().st_size

    @property
    def bytes_callback(self) -> Callable[[int], None] | None:
        """Get bytes callback if byte-based progress is active."""
        return (
            self.on_bytes if (self._show_progress and not self._use_elements) else None
        )

    @property
    def element_callback(self) -> Callable[[], None] | None:
        """Get element callback if element-based progress is active."""
        return self.on_element if (self._show_progress and self._use_elements) else None


def build_output_path(
    input_path: Path,
    format: FileFormat,
    output_dir: Path,
    compression: Compression = Compression.none,
) -> Path:
    """Build output path from input filename and output directory."""
    stem = input_path.name.removesuffix(".xml.gz")
    ext = COMPRESSION_EXTENSIONS[compression]
    return output_dir / f"{stem}.{format.value}{ext}"


def build_database_path(paths: list[Path], output_dir: Path) -> Path:
    """Build database path from input filenames."""
    if not paths:
        raise ValueError("No input files provided")
    stem = paths[0].name.removesuffix(".xml.gz")
    return output_dir / f"{stem}.db"


def _log(message: str, verbose: bool) -> None:
    """Log a message if verbose mode is enabled."""
    if verbose:
        import sys

        print(f"[convert] {message}", file=sys.stderr)


def convert(
    *,
    format: FileFormat,
    paths: list[Path],
    compression: Compression = Compression.none,
    entity_type: str | None = None,
    fail_on_unhandled: bool = False,
    filters: list[Filter] | None = None,
    limit: int | None = None,
    output_dir: Path = Path("."),
    show_progress: bool = False,
    show_summary: bool = True,
    strict: bool = False,
    verbose: bool = False,
) -> Summary | None:
    """Convert XML dumps to a file format."""
    import time

    valid_paths = [p for p in paths if p.is_file()]
    writer_cls = FILE_WRITERS[format]
    filter = FilterChain(filters) if filters else None

    _log(f"Processing {len(valid_paths)} file(s) with format={format.value}", verbose)

    with ExitStack() as stack:
        summary = (
            stack.enter_context(SummaryCollector(options={"strict": strict}))
            if show_summary
            else None
        )
        tracker = ProgressTracker(stack, limit, show_progress, valid_paths)

        if writer_cls.aggregates_inputs:
            with get_file_writer(format, path=None) as writer:
                for path in valid_paths:
                    _log(f"Starting {path.name}", verbose)
                    file_start = time.perf_counter()
                    execute(
                        fail_on_unhandled=fail_on_unhandled,
                        filter=filter,
                        limit=limit,
                        on_progress_bytes=tracker.bytes_callback,
                        on_progress_element=tracker.element_callback,
                        parser=get_parser(path, entity_type),
                        path=path,
                        reader=tracker.get_reader(),
                        strict=strict,
                        summary=summary,
                        writer=writer,
                    )
                    file_elapsed = time.perf_counter() - file_start
                    _log(f"Finished {path.name} in {file_elapsed:.2f}s", verbose)
                    tracker.advance_file(path)
        else:
            for path in valid_paths:
                output_path = build_output_path(path, format, output_dir, compression)
                _log(f"Starting {path.name} -> {output_path.name}", verbose)
                file_start = time.perf_counter()
                with get_file_writer(
                    format, compression=compression, path=output_path
                ) as writer:
                    execute(
                        fail_on_unhandled=fail_on_unhandled,
                        filter=filter,
                        limit=limit,
                        on_progress_bytes=tracker.bytes_callback,
                        on_progress_element=tracker.element_callback,
                        parser=get_parser(path, entity_type),
                        path=path,
                        reader=tracker.get_reader(),
                        strict=strict,
                        summary=summary,
                        writer=writer,
                    )
                file_elapsed = time.perf_counter() - file_start
                _log(f"Finished {path.name} in {file_elapsed:.2f}s", verbose)
                tracker.advance_file(path)

        return summary.result() if summary else None


def load(
    database: DatabaseType,
    paths: list[Path],
    dsn: str,
    batch_size: int = 10000,
    commit_interval: int | None = None,
    entity_type: str | None = None,
    fail_on_unhandled: bool = False,
    filters: list[Filter] | None = None,
    limit: int | None = None,
    show_progress: bool = False,
    show_summary: bool = True,
    strict: bool = False,
    verbose: bool = False,
) -> Summary | None:
    """Load XML dumps into a database."""
    valid_paths = [p for p in paths if p.is_file()]
    filter = FilterChain(filters) if filters else None

    with ExitStack() as stack:
        summary = (
            stack.enter_context(SummaryCollector(options={"strict": strict}))
            if show_summary
            else None
        )
        tracker = ProgressTracker(stack, limit, show_progress, valid_paths)

        with get_database_writer(
            database,
            batch_size=batch_size,
            commit_interval=commit_interval,
            dsn=dsn,
            verbose=verbose,
        ) as writer:
            for path in valid_paths:
                execute(
                    fail_on_unhandled=fail_on_unhandled,
                    filter=filter,
                    limit=limit,
                    on_progress_bytes=tracker.bytes_callback,
                    on_progress_element=tracker.element_callback,
                    parser=get_parser(path, entity_type),
                    path=path,
                    reader=tracker.get_reader(),
                    strict=strict,
                    summary=summary,
                    writer=writer,
                )
                tracker.advance_file(path)

        return summary.result() if summary else None
