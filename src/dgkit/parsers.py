import re

from lxml import etree
from pathlib import Path
from typing import Iterator

from dgkit.models import (
    Artist,
    ArtistRef,
    Label,
    LabelRef,
    MasterArtist,
    MasterRelease,
    Release,
    Video,
)
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


def _parse_label_refs(parent: etree._Element | None) -> list[LabelRef]:
    """Parse a list of label references from a parent element."""
    if parent is None:
        return []
    refs = []
    for label_elem in parent.findall("label"):
        ref_id = label_elem.get("id")
        if ref_id and label_elem.text:
            refs.append(LabelRef(id=int(ref_id), name=label_elem.text))
    return refs


class LabelParser:
    tag = "label"

    def parse(self, elem: etree._Element) -> Iterator[Label]:
        """Parse label XML element into Label record."""
        urls_elem = elem.find("urls")
        urls = (
            [url.text for url in urls_elem.findall("url") if url.text]
            if urls_elem is not None
            else []
        )

        parent_label_elem = elem.find("parentLabel")
        parent_label = None
        if parent_label_elem is not None:
            parent_id = parent_label_elem.get("id")
            if parent_id and parent_label_elem.text:
                parent_label = LabelRef(id=int(parent_id), name=parent_label_elem.text)

        yield Label(
            id=int(elem.get("id") or elem.findtext("id")),
            name=elem.findtext("name") or elem.text,
            contact_info=elem.findtext("contactinfo"),
            profile=elem.findtext("profile"),
            data_quality=elem.findtext("data_quality"),
            urls=urls,
            sublabels=_parse_label_refs(elem.find("sublabels")),
            parent_label=parent_label,
        )


def _parse_master_artists(parent: etree._Element | None) -> list[MasterArtist]:
    """Parse artist credits from a master release."""
    if parent is None:
        return []
    artists = []
    for artist_elem in parent.findall("artist"):
        artist_id = artist_elem.findtext("id")
        name = artist_elem.findtext("name")
        anv = artist_elem.findtext("anv")
        join = artist_elem.findtext("join")
        if artist_id and name:
            artists.append(MasterArtist(int(artist_id), name, anv, join))
    return artists


def _parse_videos(parent: etree._Element | None) -> list[Video]:
    """Parse videos from a master release."""
    if parent is None:
        return []
    videos = []
    for video_elem in parent.findall("video"):
        src = video_elem.get("src")
        duration = video_elem.get("duration")
        embed = video_elem.get("embed")
        if src and duration:
            videos.append(
                Video(
                    src=src,
                    duration=int(duration),
                    embed=embed == "true",
                    title=video_elem.findtext("title"),
                    description=video_elem.findtext("description"),
                )
            )
    return videos


class MasterReleaseParser:
    tag = "master"

    def parse(self, elem: etree._Element) -> Iterator[MasterRelease]:
        """Parse master XML element into MasterRelease record."""
        genres_elem = elem.find("genres")
        genres = (
            [g.text for g in genres_elem.findall("genre") if g.text]
            if genres_elem is not None
            else []
        )

        styles_elem = elem.find("styles")
        styles = (
            [s.text for s in styles_elem.findall("style") if s.text]
            if styles_elem is not None
            else []
        )

        year_text = elem.findtext("year")
        year = int(year_text) if year_text else None

        main_release_text = elem.findtext("main_release")
        main_release = int(main_release_text) if main_release_text else None

        yield MasterRelease(
            id=int(elem.get("id")),
            title=elem.findtext("title"),
            main_release=main_release,
            year=year,
            notes=elem.findtext("notes"),
            data_quality=elem.findtext("data_quality"),
            artists=_parse_master_artists(elem.find("artists")),
            genres=genres,
            styles=styles,
            videos=_parse_videos(elem.find("videos")),
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
