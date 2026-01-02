"""Sample elements from Discogs XML dumps."""

import gzip
import re
from pathlib import Path
from typing import Callable

from lxml import etree

from dgkit.readers import GzipReader


# Matches: discogs_YYYYMMDD_<entity>.xml.gz or discogs_YYYYMMDD_<entity>_sample_N.xml.gz
FILENAME_PATTERN = re.compile(
    r"discogs_\d{8}_(artists|labels|masters|releases)(?:_sample_\d+)?\.xml\.gz"
)

# Maps entity name (from filename) to XML element tag
ENTITY_TAGS: dict[str, str] = {
    "artists": "artist",
    "labels": "label",
    "masters": "master",
    "releases": "release",
}


def get_entity_tag(path: Path) -> tuple[str, str]:
    """Get entity name and XML tag from filename.

    Returns:
        Tuple of (entity_name, xml_tag), e.g., ("artists", "artist")

    Raises:
        ValueError: If filename doesn't match expected pattern or entity unknown.
    """
    match = FILENAME_PATTERN.match(path.name)
    if not match:
        raise ValueError(f"Unrecognized filename pattern: {path.name}")
    entity = match.group(1)
    if entity not in ENTITY_TAGS:
        raise ValueError(f"Unknown entity type: {entity}")
    return entity, ENTITY_TAGS[entity]


def build_sample_path(input_path: Path, count: int) -> Path:
    """Build default output path for sample file.

    Example: discogs_20251201_releases.xml.gz -> discogs_20251201_releases_sample_1000000.xml.gz
    """
    stem = input_path.name.removesuffix(".xml.gz")
    return Path(f"{stem}_sample_{count}.xml.gz")


def sample(
    input_path: Path,
    output_path: Path,
    count: int,
    *,
    on_progress: Callable[[], None] | None = None,
) -> int:
    """Extract first `count` elements from a Discogs XML dump.

    Args:
        input_path: Path to input gzipped XML file.
        output_path: Path to output gzipped XML file.
        count: Maximum number of elements to extract.
        on_progress: Optional callback called after each element is written.

    Returns:
        Actual number of elements written (may be less than count if input has fewer).
    """
    entity, tag = get_entity_tag(input_path)
    written = 0

    with GzipReader().open(input_path) as stream:
        context = etree.iterparse(stream, events=("end",), tag=tag)

        with gzip.open(output_path, "wb", compresslevel=6) as out:
            # Write XML declaration and opening root tag
            out.write(b'<?xml version="1.0" encoding="UTF-8"?>\n')
            out.write(f"<{entity}>\n".encode("utf-8"))

            for _, elem in context:
                # Serialize element to bytes
                xml_bytes = etree.tostring(elem, encoding="unicode")
                out.write(xml_bytes.encode("utf-8"))
                out.write(b"\n")
                written += 1

                # Memory optimization: clear element after processing
                elem.clear()
                while elem.getprevious() is not None:
                    del elem.getparent()[0]

                if on_progress is not None:
                    on_progress()

                if written >= count:
                    break

            # Write closing root tag
            out.write(f"</{entity}>\n".encode("utf-8"))

    return written
