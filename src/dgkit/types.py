from contextlib import contextmanager
from enum import Enum
from pathlib import Path
from typing import IO, Iterator, NamedTuple, Protocol, Self

from lxml import etree


class FileFormat(str, Enum):
    blackhole = "blackhole"
    console = "console"
    json = "json"
    jsonl = "jsonl"


class DatabaseType(str, Enum):
    postgresql = "postgresql"
    sqlite = "sqlite"


class Compression(str, Enum):
    bz2 = "bz2"
    gzip = "gzip"
    none = "none"


class Parser(Protocol):
    """Protocol for XML element parsers."""

    tag: str

    def parse(self, elem: etree._Element) -> Iterator[NamedTuple]: ...


class Reader(Protocol):
    """Protocol for input readers.

    Readers may optionally implement progress tracking by providing
    `total_size` and `bytes_read` properties. Use `is_trackable()` from
    pipeline module to check if a reader supports tracking.
    """

    @contextmanager
    def open(self, path: Path) -> Iterator[IO[bytes]]: ...


class Writer(Protocol):
    """Protocol for output writers."""

    aggregates_inputs: bool

    def __enter__(self) -> Self: ...
    def __exit__(self, exc_type, exc_val, exc_tb) -> None: ...
    def write(self, record: NamedTuple) -> None: ...
