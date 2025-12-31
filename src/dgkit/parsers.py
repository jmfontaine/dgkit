import re

from lxml import etree
from pathlib import Path
from typing import Iterator

from dgkit.models import Artist, ArtistRef, Label, MasterRelease, Release
from dgkit.types import Parser


def _parse_artist_refs(parent: etree._Element | None) -> list[ArtistRef]:
    """Parse a list of artist references from a parent element."""
    if parent is None:
        return []
    refs = []
    for name_elem in parent.findall("name"):
        ref_id = name_elem.get("id")
        if ref_id and name_elem.text:
            refs.append(ArtistRef(id=int(ref_id), name=name_elem.text))
    return refs


class ArtistParser:
    tag = "artist"

    def parse(self, elem: etree._Element) -> Iterator[Artist]:
        """Parse artist XML element into Artist record."""
        urls_elem = elem.find("urls")
        urls = (
            [url.text for url in urls_elem.findall("url") if url.text]
            if urls_elem is not None
            else []
        )

        namevariations_elem = elem.find("namevariations")
        name_variations = (
            [n.text for n in namevariations_elem.findall("name") if n.text]
            if namevariations_elem is not None
            else []
        )

        yield Artist(
            id=int(elem.findtext("id")),
            name=elem.findtext("name"),
            real_name=elem.findtext("realname"),
            profile=elem.findtext("profile"),
            data_quality=elem.findtext("data_quality"),
            urls=urls,
            name_variations=name_variations,
            aliases=_parse_artist_refs(elem.find("aliases")),
            members=_parse_artist_refs(elem.find("members")),
            groups=_parse_artist_refs(elem.find("groups")),
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
