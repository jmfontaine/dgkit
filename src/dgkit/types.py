from contextlib import contextmanager
from enum import Enum
from typing import IO, Iterator, NamedTuple, Protocol, Self

from lxml import etree
from pathlib import Path


class Format(str, Enum):
    blackhole = "blackhole"
    console = "console"
    jsonl = "jsonl"
    sqlite = "sqlite"


class Compression(str, Enum):
    none = "none"
    gzip = "gzip"
    bz2 = "bz2"


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

    aggregates_inputs: bool

    def __enter__(self) -> Self: ...
    def __exit__(self, exc_type, exc_val, exc_tb) -> None: ...
    def write(self, record: NamedTuple) -> None: ...
