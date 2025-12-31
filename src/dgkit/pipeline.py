import re

from lxml import etree
from pathlib import Path
from typing import Callable, IO, Iterator

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

from dgkit.benchmark import Summary, SummaryCollector
from dgkit.filters import Filter, FilterChain
from dgkit.parsers import get_parser
from dgkit.readers import GzipReader, TrackingGzipReader
from dgkit.types import (
    Compression,
    DatabaseType,
    FileFormat,
    Parser,
    Reader,
    Writer,
)
from dgkit.writers import (
    DATABASE_WRITERS,
    FILE_WRITERS,
    get_database_writer,
    get_file_writer,
)


def find_elements(
    stream: IO[bytes], tag: str, limit: int | None = None
) -> Iterator[etree._Element]:
    """Yield XML elements matching tag from stream."""
    context = etree.iterparse(stream, events=("end",), tag=tag)
    count = 0
    for _, elem in context:
        yield elem
        elem.clear()
        while elem.getprevious() is not None:
            del elem.getparent()[0]
        count += 1
        if limit is not None and count >= limit:
            break


def is_trackable(reader: Reader) -> bool:
    """Check if a reader supports progress tracking."""
    return hasattr(reader, "bytes_read") and hasattr(reader, "total_size")


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
    path: Path,
    parser: Parser,
    reader: Reader,
    writer: Writer,
    limit: int | None,
    filter: Filter | None = None,
    summary: SummaryCollector | None = None,
    on_progress_bytes: Callable[[int], None] | None = None,
    on_progress_element: Callable[[], None] | None = None,
):
    """Execute the pipeline."""
    track_bytes = on_progress_bytes is not None and is_trackable(reader)
    with reader.open(path) as stream:
        for elem in find_elements(stream, parser.tag, limit):
            for record in parser.parse(elem):
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
            if track_bytes:
                on_progress_bytes(reader.bytes_read)  # type: ignore[union-attr]
            if on_progress_element:
                on_progress_element()


COMPRESSION_EXTENSIONS: dict[Compression, str] = {
    Compression.none: "",
    Compression.bz2: ".bz2",
    Compression.gzip: ".gz",
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


DATABASE_FILENAME_PATTERN = re.compile(r"(discogs_\d{8})_\w+\.xml\.gz")


def build_database_path(paths: list[Path], output_dir: Path) -> Path:
    """Build database path from input filenames (e.g., discogs_20251201.db)."""
    for path in paths:
        match = DATABASE_FILENAME_PATTERN.match(path.name)
        if match:
            return output_dir / f"{match.group(1)}.db"
    raise ValueError("No valid input file found to derive database name")


def convert(
    format: FileFormat,
    paths: list[Path],
    limit: int | None = None,
    output_dir: Path = Path("."),
    compression: Compression = Compression.none,
    filters: list[Filter] | None = None,
    show_summary: bool = True,
    show_progress: bool = False,
) -> Summary | None:
    """Convert XML dumps to a file format."""
    valid_paths = [p for p in paths if p.is_file()]
    writer_cls = FILE_WRITERS[format]
    filter = FilterChain(filters) if filters else None
    summary = SummaryCollector() if show_summary else None

    if summary:
        summary.__enter__()

    # Use element-based progress when limit is set, bytes-based otherwise
    use_element_progress = limit is not None
    progress: Progress | None = None
    task_id: TaskID | None = None

    if show_progress:
        if use_element_progress:
            total = limit * len(valid_paths)
            progress = create_progress_elements()
        else:
            total = sum(p.stat().st_size for p in valid_paths)
            progress = create_progress_bytes()
        progress.start()
        task_id = progress.add_task("Processing", total=total)

    try:
        bytes_completed = 0

        def on_progress_bytes(bytes_read: int) -> None:
            nonlocal bytes_completed
            if progress and task_id is not None:
                progress.update(task_id, completed=bytes_completed + bytes_read)

        def on_progress_element() -> None:
            if progress and task_id is not None:
                progress.advance(task_id)

        if writer_cls.aggregates_inputs:
            with get_file_writer(format, path=None) as writer:
                for path in valid_paths:
                    reader = TrackingGzipReader() if (show_progress and not use_element_progress) else GzipReader()
                    parser = get_parser(path)
                    execute(
                        limit=limit,
                        path=path,
                        parser=parser,
                        reader=reader,
                        writer=writer,
                        filter=filter,
                        summary=summary,
                        on_progress_bytes=on_progress_bytes if (show_progress and not use_element_progress) else None,
                        on_progress_element=on_progress_element if (show_progress and use_element_progress) else None,
                    )
                    bytes_completed += path.stat().st_size
        else:
            for path in valid_paths:
                reader = TrackingGzipReader() if (show_progress and not use_element_progress) else GzipReader()
                parser = get_parser(path)
                output_path = build_output_path(path, format, output_dir, compression)
                with get_file_writer(
                    format, path=output_path, compression=compression
                ) as writer:
                    execute(
                        limit=limit,
                        path=path,
                        parser=parser,
                        reader=reader,
                        writer=writer,
                        filter=filter,
                        summary=summary,
                        on_progress_bytes=on_progress_bytes if (show_progress and not use_element_progress) else None,
                        on_progress_element=on_progress_element if (show_progress and use_element_progress) else None,
                    )
                bytes_completed += path.stat().st_size
    finally:
        if progress:
            progress.stop()

    return summary.result() if summary else None


def load(
    database: DatabaseType,
    paths: list[Path],
    dsn: str,
    limit: int | None = None,
    filters: list[Filter] | None = None,
    batch_size: int = 10000,
    show_summary: bool = True,
    show_progress: bool = False,
) -> Summary | None:
    """Load XML dumps into a database."""
    valid_paths = [p for p in paths if p.is_file()]
    filter = FilterChain(filters) if filters else None
    summary = SummaryCollector() if show_summary else None

    if summary:
        summary.__enter__()

    # Use element-based progress when limit is set, bytes-based otherwise
    use_element_progress = limit is not None
    progress: Progress | None = None
    task_id: TaskID | None = None

    if show_progress:
        if use_element_progress:
            total = limit * len(valid_paths)
            progress = create_progress_elements()
        else:
            total = sum(p.stat().st_size for p in valid_paths)
            progress = create_progress_bytes()
        progress.start()
        task_id = progress.add_task("Processing", total=total)

    try:
        bytes_completed = 0

        def on_progress_bytes(bytes_read: int) -> None:
            nonlocal bytes_completed
            if progress and task_id is not None:
                progress.update(task_id, completed=bytes_completed + bytes_read)

        def on_progress_element() -> None:
            if progress and task_id is not None:
                progress.advance(task_id)

        with get_database_writer(database, dsn=dsn, batch_size=batch_size) as writer:
            for path in valid_paths:
                reader = TrackingGzipReader() if (show_progress and not use_element_progress) else GzipReader()
                parser = get_parser(path)
                execute(
                    limit=limit,
                    path=path,
                    parser=parser,
                    reader=reader,
                    writer=writer,
                    filter=filter,
                    summary=summary,
                    on_progress_bytes=on_progress_bytes if (show_progress and not use_element_progress) else None,
                    on_progress_element=on_progress_element if (show_progress and use_element_progress) else None,
                )
                bytes_completed += path.stat().st_size
    finally:
        if progress:
            progress.stop()

    return summary.result() if summary else None
