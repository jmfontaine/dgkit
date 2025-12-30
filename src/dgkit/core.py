import bz2
import gzip
import json
import re
import sqlite3

from contextlib import contextmanager
from enum import Enum
from lxml import etree
from pathlib import Path
from rich import print
from typing import IO, Any, Iterator, NamedTuple, Protocol, Self


class Format(str, Enum):
    blackhole = "blackhole"
    console = "console"
    jsonl = "jsonl"
    sqlite = "sqlite"


class Compression(str, Enum):
    none = "none"
    gzip = "gzip"
    bz2 = "bz2"


def open_compressed(path: Path, mode: str, compression: Compression) -> IO:
    """Open a file with optional compression."""
    match compression:
        case Compression.gzip:
            return gzip.open(path, mode)
        case Compression.bz2:
            return bz2.open(path, mode)
        case _:
            return open(path, mode)


class Parser(Protocol):
    """Protocol for XML element parsers."""

    tag: str

    def parse(self, elem: etree._Element) -> Iterator[NamedTuple]: ...


class Reader(Protocol):
    """Protocol for input readers."""

    @contextmanager
    def open(self, path: Path) -> Iterator[IO[bytes]]: ...


class Writer(Protocol):
    """Protocol for output writers."""

    def __enter__(self) -> Self: ...
    def __exit__(self, exc_type, exc_val, exc_tb) -> None: ...
    def write(self, record: NamedTuple) -> None: ...


class GzipReader:
    """Reader using standard gzip module."""

    @contextmanager
    def open(self, path: Path) -> Iterator[IO[bytes]]:
        with gzip.open(path, "rb") as fp:
            yield fp


class BlackholeWriter:
    """Writer that drops records. This is mostly useful for benchmarking."""

    aggregates_inputs = True

    def __init__(self, **kwargs: Any):
        pass

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        pass

    def write(self, record: NamedTuple) -> None:
        pass


class ConsoleWriter:
    """Writer that prints records to the console."""

    aggregates_inputs = True

    def __init__(self, **kwargs: Any):
        pass

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        pass

    def write(self, record: NamedTuple) -> None:
        print(record)


class JsonlWriter:
    """Writer that outputs records as JSON Lines."""

    aggregates_inputs = False

    def __init__(self, path: Path, compression: Compression = Compression.none):
        self.path = path
        self.compression = compression
        self._fp: IO | None = None

    def __enter__(self) -> Self:
        self._fp = open_compressed(self.path, "wt", self.compression)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if self._fp:
            self._fp.close()

    def write(self, record: NamedTuple) -> None:
        if self._fp:
            self._fp.write(json.dumps(record._asdict()) + "\n")


SQLITE_TYPE_MAP: dict[type, str] = {
    int: "INTEGER",
    float: "REAL",
    str: "TEXT",
    bool: "INTEGER",
    bytes: "BLOB",
}


class SqliteWriter:
    """Writer that outputs records to a SQLite database."""

    aggregates_inputs = True

    def __init__(self, path: Path, **kwargs: Any):
        self.path = path
        self._conn: sqlite3.Connection | None = None
        self._tables: set[str] = set()

    def __enter__(self) -> Self:
        self._conn = sqlite3.connect(self.path)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if self._conn:
            self._conn.commit()
            self._conn.close()

    def _ensure_table(self, record: NamedTuple) -> str:
        """Create table for record type if it doesn't exist."""
        table_name = type(record).__name__.lower()
        if table_name in self._tables:
            return table_name

        fields = record._fields
        annotations = type(record).__annotations__

        columns = []
        for field in fields:
            field_type = annotations.get(field, str)
            # Handle Optional types (e.g., str | None)
            if hasattr(field_type, "__origin__"):
                args = getattr(field_type, "__args__", ())
                field_type = next((t for t in args if t is not type(None)), str)
            sqlite_type = SQLITE_TYPE_MAP.get(field_type, "TEXT")
            columns.append(f"{field} {sqlite_type}")

        self._conn.execute(f"DROP TABLE IF EXISTS {table_name}")
        self._conn.execute(f"CREATE TABLE {table_name} ({', '.join(columns)})")
        self._tables.add(table_name)
        return table_name

    def write(self, record: NamedTuple) -> None:
        if not self._conn:
            return
        table_name = self._ensure_table(record)
        # Serialize lists as JSON strings
        values = tuple(
            json.dumps(v) if isinstance(v, list) else v for v in record
        )
        placeholders = ", ".join("?" * len(record))
        sql = f"INSERT INTO {table_name} VALUES ({placeholders})"
        self._conn.execute(sql, values)


WRITERS: dict[Format, type[Writer]] = {
    Format.blackhole: BlackholeWriter,
    Format.console: ConsoleWriter,
    Format.jsonl: JsonlWriter,
    Format.sqlite: SqliteWriter,
}


def get_writer(format: Format, **kwargs: Any) -> Writer:
    """Create a writer for the given format."""
    if format not in WRITERS:
        raise NotImplementedError(f"Writer for {format.value} not implemented")
    return WRITERS[format](**kwargs)


class Artist(NamedTuple):
    id: int
    name: str | None
    profile: str | None
    real_name: str | None
    aliases: list[int] = []
    name_variations: list[str] = []
    urls: list[str] = []


class Label(NamedTuple):
    id: int
    name: str | None


class MasterRelease(NamedTuple):
    id: int
    title: str | None


class Release(NamedTuple):
    id: int
    title: str | None


class ArtistParser:
    tag = "artist"

    def parse(self, elem: etree._Element) -> Iterator[Artist]:
        """Parse artist XML element into Artist record."""
        aliases_elem = elem.find("aliases")
        aliases = (
            [int(name.get("id")) for name in aliases_elem.findall("name")]
            if aliases_elem is not None
            else []
        )

        namevariations_elem = elem.find("namevariations")
        name_variations = (
            [name.text for name in namevariations_elem.findall("name") if name.text]
            if namevariations_elem is not None
            else []
        )

        urls_elem = elem.find("urls")
        urls = (
            [url.text for url in urls_elem.findall("url") if url.text]
            if urls_elem is not None
            else []
        )

        yield Artist(
            id=int(elem.findtext("id")),
            name=elem.findtext("name"),
            profile=elem.findtext("profile"),
            real_name=elem.findtext("realname"),
            aliases=aliases,
            name_variations=name_variations,
            urls=urls,
        )


class LabelParser:
    tag = "label"

    def parse(self, elem: etree._Element) -> Iterator[Label]:
        """Parse label XML element into Label record."""
        yield Label(
            id=int(elem.get("id") or elem.findtext("id")),
            name=elem.findtext("name") or elem.text,
        )


class MasterReleaseParser:
    tag = "master"

    def parse(self, elem: etree._Element) -> Iterator[MasterRelease]:
        """Parse master XML element into MasterRelease record."""
        yield MasterRelease(
            id=int(elem.get("id")),
            title=elem.findtext("title"),
        )


class ReleaseParser:
    tag = "release"

    def parse(self, elem: etree._Element) -> Iterator[Release]:
        """Parse release XML element into Release record."""
        yield Release(
            id=int(elem.get("id")),
            title=elem.findtext("title"),
        )


PARSERS: dict[str, type[Parser]] = {
    "artists": ArtistParser,
    "labels": LabelParser,
    "masters": MasterReleaseParser,
    "releases": ReleaseParser,
}

FILENAME_PATTERN = re.compile(r"discogs_\d{8}_(\w+)\.xml\.gz")


def get_parser(path: Path) -> Parser:
    """Create a parser based on filename pattern."""
    match = FILENAME_PATTERN.match(path.name)
    if not match:
        raise ValueError(f"Unrecognized filename pattern: {path.name}")
    entity = match.group(1)
    if entity not in PARSERS:
        raise NotImplementedError(f"Parser for {entity} not implemented")
    return PARSERS[entity]()


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


def execute(
    *, path: Path, parser: Parser, reader: Reader, writer: Writer, limit: int | None
):
    """Execute the pipeline."""
    with reader.open(path) as stream:
        for elem in find_elements(stream, parser.tag, limit):
            for record in parser.parse(elem):
                writer.write(record)


COMPRESSION_EXTENSIONS: dict[Compression, str] = {
    Compression.none: "",
    Compression.bz2: ".bz2",
    Compression.gzip: ".gz",
}


def build_output_path(
    input_path: Path,
    format: Format,
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
    format: Format,
    paths: list[Path],
    limit: int | None = None,
    output_dir: Path = Path("."),
    compression: Compression = Compression.none,
):
    reader = GzipReader()
    valid_paths = [p for p in paths if p.is_file()]
    writer_cls = WRITERS[format]

    if writer_cls.aggregates_inputs:
        # Aggregating writers: single destination for all input files
        if format in (Format.console, Format.blackhole):
            output_path = None
        else:
            output_path = build_database_path(valid_paths, output_dir)
        with get_writer(format, path=output_path) as writer:
            for path in valid_paths:
                parser = get_parser(path)
                execute(
                    limit=limit,
                    path=path,
                    parser=parser,
                    reader=reader,
                    writer=writer,
                )
    else:
        # File writers: one output per input
        for path in valid_paths:
            output_path = build_output_path(path, format, output_dir, compression)
            parser = get_parser(path)
            with get_writer(
                format, path=output_path, compression=compression
            ) as writer:
                execute(
                    limit=limit,
                    path=path,
                    parser=parser,
                    reader=reader,
                    writer=writer,
                )


def inspect():
    print("Inspect")
