import gzip
import json
import re

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


class Parser(Protocol):
    """Protocol for XML element parsers."""

    tag: str

    def parse(self, elem: etree._Element) -> NamedTuple: ...


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

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        pass

    def write(self, record: NamedTuple) -> None:
        pass


class ConsoleWriter:
    """Writer that prints records to the console."""

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        pass

    def write(self, record: NamedTuple) -> None:
        print(record)


class JsonlWriter:
    """Writer that outputs records as JSON Lines."""

    def __init__(self, path: Path):
        self.path = path
        self._fp: IO[str] | None = None

    def __enter__(self) -> Self:
        self._fp = open(self.path, "w")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if self._fp:
            self._fp.close()

    def write(self, record: NamedTuple) -> None:
        if self._fp:
            self._fp.write(json.dumps(record._asdict()) + "\n")


WRITERS: dict[Format, type[Writer]] = {
    Format.blackhole: BlackholeWriter,
    Format.console: ConsoleWriter,
    Format.jsonl: JsonlWriter,
}


def get_writer(format: Format, **kwargs: Any) -> Writer:
    """Create a writer for the given format."""
    if format not in WRITERS:
        raise NotImplementedError(f"Writer for {format.value} not implemented")
    return WRITERS[format](**kwargs)


class Artist(NamedTuple):
    id: int
    name: str | None


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

    def parse(self, elem: etree._Element) -> Artist:
        """Parse artist XML element into Artist record."""
        return Artist(
            id=int(elem.findtext("id")),
            name=elem.findtext("name"),
        )


class LabelParser:
    tag = "label"

    def parse(self, elem: etree._Element) -> Label:
        """Parse label XML element into Label record."""
        return Label(
            id=int(elem.get("id") or elem.findtext("id")),
            name=elem.findtext("name") or elem.text,
        )


class MasterReleaseParser:
    tag = "master"

    def parse(self, elem: etree._Element) -> MasterRelease:
        """Parse artist XML element into MasterRelease record."""
        return MasterRelease(
            id=int(elem.get("id")),
            title=elem.findtext("title"),
        )


class ReleaseParser:
    tag = "release"

    def parse(self, elem: etree._Element) -> Release:
        """Parse artist XML element into Release record."""
        return Release(
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
            record = parser.parse(elem)
            writer.write(record)


def convert(format: Format, paths: list[Path], limit: int | None = None):
    reader = GzipReader()

    with get_writer(format) as writer:
        for path in paths:
            if path.is_file():
                parser = get_parser(path)
                execute(
                    path=path,
                    parser=parser,
                    reader=reader,
                    writer=writer,
                    limit=limit,
                )


def inspect():
    print("Inspect")
