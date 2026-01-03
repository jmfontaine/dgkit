import types

from contextlib import contextmanager
from enum import Enum
from pathlib import Path
from typing import IO, Any, Iterator, Protocol, Self, runtime_checkable


@runtime_checkable
class Element(Protocol):
    """Protocol for XML element access (satisfied by lxml._Element and TrackingElement)."""

    @property
    def tag(self) -> str: ...
    @property
    def text(self) -> str | None: ...
    def __iter__(self) -> Iterator["Element"]: ...
    def get(self, attr: str, default: str | None = None) -> str | None: ...
    def findtext(self, tag: str, default: str | None = None) -> str | None: ...
    def find(self, tag: str) -> "Element | None": ...
    def findall(self, tag: str) -> list["Element"]: ...


class EntityType(str, Enum):
    artists = "artists"
    labels = "labels"
    masters = "masters"
    releases = "releases"


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

    def parse(self, elem: Element) -> Iterator[Any]: ...


class Reader(Protocol):
    """Protocol for input readers."""

    @property
    def bytes_read(self) -> int: ...

    @property
    def total_size(self) -> int: ...

    @contextmanager
    def open(self, path: Path) -> Iterator[IO[bytes]]: ...


class Writer(Protocol):
    """Protocol for output writers."""

    aggregates_inputs: bool

    def __enter__(self) -> Self: ...
    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: types.TracebackType | None,
    ) -> None: ...
    def write(self, record: Any) -> None: ...
