import re

from lxml import etree
from pathlib import Path
from typing import Iterator

from dgkit.models import Artist, Label, MasterRelease, Release
from dgkit.types import Parser


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

        aliases: list[int] = []
        aliases_elem = elem.find("aliases")
        if aliases_elem is not None:
            for name in aliases_elem.findall("name"):
                alias_id = name.get("id")
                if alias_id:
                    aliases.append(int(alias_id))

        yield Artist(
            id=int(elem.findtext("id")),
            name=elem.findtext("name"),
            profile=elem.findtext("profile"),
            real_name=elem.findtext("realname"),
            urls=urls,
            aliases=aliases,
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
