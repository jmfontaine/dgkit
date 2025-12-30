import re

from lxml import etree
from pathlib import Path
from rich import print
from typing import IO, Iterator

from dgkit.parsers import get_parser
from dgkit.readers import GzipReader
from dgkit.types import Compression, Format, Parser, Reader, Writer
from dgkit.writers import WRITERS, get_writer


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
