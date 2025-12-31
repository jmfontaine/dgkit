import re
from pathlib import Path
from typing import Iterator

from lxml import etree

from dgkit.models import (
    Artist,
    ArtistRef,
    Company,
    CreditArtist,
    DataQuality,
    ExtraArtist,
    Format,
    FormatName,
    Identifier,
    IdentifierType,
    Label,
    LabelRef,
    MasterRelease,
    Release,
    ReleaseLabel,
    ReleaseStatus,
    Series,
    SubTrack,
    Track,
    Video,
)
from dgkit.types import Parser


def _parse_text_list(parent: etree._Element | None, tag: str) -> list[str]:
    """Parse a list of text elements from a parent."""
    if parent is None:
        return []
    return [elem.text for elem in parent.findall(tag) if elem.text]


def _parse_data_quality(elem: etree._Element) -> DataQuality | None:
    """Parse data_quality field, converting to enum."""
    text = elem.findtext("data_quality")
    return DataQuality(text) if text else None


def _parse_release_status(elem: etree._Element) -> ReleaseStatus | None:
    """Parse release status attribute, converting to enum."""
    text = elem.get("status")
    return ReleaseStatus(text) if text else None


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
        yield Artist(
            id=int(elem.findtext("id")),
            data_quality=_parse_data_quality(elem),
            name=elem.findtext("name"),
            profile=elem.findtext("profile"),
            real_name=elem.findtext("realname"),
            aliases=_parse_artist_refs(elem.find("aliases")),
            groups=_parse_artist_refs(elem.find("groups")),
            members=_parse_artist_refs(elem.find("members")),
            name_variations=_parse_text_list(elem.find("namevariations"), "name"),
            urls=_parse_text_list(elem.find("urls"), "url"),
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
        parent_label_elem = elem.find("parentLabel")
        parent_label = None
        if parent_label_elem is not None:
            parent_id = parent_label_elem.get("id")
            if parent_id and parent_label_elem.text:
                parent_label = LabelRef(id=int(parent_id), name=parent_label_elem.text)

        yield Label(
            id=int(elem.get("id") or elem.findtext("id")),
            contact_info=elem.findtext("contactinfo"),
            data_quality=_parse_data_quality(elem),
            name=elem.findtext("name") or elem.text,
            profile=elem.findtext("profile"),
            parent_label=parent_label,
            sub_labels=_parse_label_refs(elem.find("sublabels")),
            urls=_parse_text_list(elem.find("urls"), "url"),
        )


def _parse_credit_artists(parent: etree._Element | None) -> list[CreditArtist]:
    """Parse artist credits (id, name, artist_name_variation, join)."""
    if parent is None:
        return []
    artists = []
    for artist_elem in parent.findall("artist"):
        artist_id = artist_elem.findtext("id")
        name = artist_elem.findtext("name")
        artist_name_variation = artist_elem.findtext("anv")
        join = artist_elem.findtext("join")
        if artist_id and name:
            artists.append(
                CreditArtist(
                    id=int(artist_id),
                    artist_name_variation=artist_name_variation,
                    join=join,
                    name=name,
                )
            )
    return artists


def _parse_extra_artists(parent: etree._Element | None) -> list[ExtraArtist]:
    """Parse extra artist credits (producer, engineer, etc.)."""
    if parent is None:
        return []
    artists = []
    for artist_elem in parent.findall("artist"):
        artist_id_text = artist_elem.findtext("id")
        artist_id = int(artist_id_text) if artist_id_text else None
        name = artist_elem.findtext("name")
        artist_name_variation = artist_elem.findtext("anv")
        role = artist_elem.findtext("role")
        tracks = artist_elem.findtext("tracks")
        if name:
            artists.append(
                ExtraArtist(
                    id=artist_id,
                    artist_name_variation=artist_name_variation,
                    name=name,
                    role=role,
                    tracks=tracks,
                )
            )
    return artists


def _parse_release_labels(parent: etree._Element | None) -> list[ReleaseLabel]:
    """Parse label credits on a release."""
    if parent is None:
        return []
    labels = []
    for label_elem in parent.findall("label"):
        label_id = label_elem.get("id")
        name = label_elem.get("name")
        catalog_number = label_elem.get("catno")
        if label_id and name:
            labels.append(
                ReleaseLabel(id=int(label_id), catalog_number=catalog_number, name=name)
            )
    return labels


def _parse_formats(parent: etree._Element | None) -> list[Format]:
    """Parse format information."""
    if parent is None:
        return []
    formats = []
    for format_elem in parent.findall("format"):
        name = format_elem.get("name")
        quantity_text = format_elem.get("qty")
        text = format_elem.get("text")
        if name and quantity_text:
            formats.append(
                Format(
                    name=FormatName(name),
                    quantity=int(quantity_text),
                    text=text,
                    descriptions=_parse_text_list(
                        format_elem.find("descriptions"), "description"
                    ),
                )
            )
    return formats


def _parse_sub_tracks(parent: etree._Element | None) -> list[SubTrack]:
    """Parse sub_tracks within a track."""
    if parent is None:
        return []
    sub_tracks = []
    for track_elem in parent.findall("track"):
        position = track_elem.findtext("position")
        title = track_elem.findtext("title")
        duration = track_elem.findtext("duration")
        artists = _parse_credit_artists(track_elem.find("artists"))
        extra_artists = _parse_extra_artists(track_elem.find("extraartists"))
        sub_tracks.append(
            SubTrack(
                duration=duration,
                position=position,
                title=title,
                artists=artists,
                extra_artists=extra_artists,
            )
        )
    return sub_tracks


def _parse_tracks(parent: etree._Element | None) -> list[Track]:
    """Parse tracklist."""
    if parent is None:
        return []
    tracks = []
    for track_elem in parent.findall("track"):
        position = track_elem.findtext("position")
        title = track_elem.findtext("title")
        duration = track_elem.findtext("duration")
        artists = _parse_credit_artists(track_elem.find("artists"))
        extra_artists = _parse_extra_artists(track_elem.find("extraartists"))
        sub_tracks = _parse_sub_tracks(track_elem.find("sub_tracks"))
        tracks.append(
            Track(
                duration=duration,
                position=position,
                title=title,
                artists=artists,
                extra_artists=extra_artists,
                sub_tracks=sub_tracks,
            )
        )
    return tracks


def _parse_identifiers(parent: etree._Element | None) -> list[Identifier]:
    """Parse identifiers (barcode, matrix, etc.)."""
    if parent is None:
        return []
    identifiers = []
    for id_elem in parent.findall("identifier"):
        id_type = id_elem.get("type")
        description = id_elem.get("description")
        value = id_elem.get("value")
        if id_type and value:
            identifiers.append(
                Identifier(
                    description=description,
                    type=IdentifierType(id_type),
                    value=value,
                )
            )
    return identifiers


def _parse_companies(parent: etree._Element | None) -> list[Company]:
    """Parse company credits."""
    if parent is None:
        return []
    companies = []
    for company_elem in parent.findall("company"):
        company_id = company_elem.findtext("id")
        name = company_elem.findtext("name")
        catalog_number = company_elem.findtext("catno")
        entity_type_text = company_elem.findtext("entity_type")
        entity_type = int(entity_type_text) if entity_type_text else None
        entity_type_name = company_elem.findtext("entity_type_name")
        # Access resource_url to mark it as handled
        company_elem.findtext("resource_url")
        if company_id and name:
            companies.append(
                Company(
                    id=int(company_id),
                    catalog_number=catalog_number,
                    entity_type=entity_type,
                    entity_type_name=entity_type_name,
                    name=name,
                )
            )
    return companies


def _parse_series(parent: etree._Element | None) -> list[Series]:
    """Parse series information."""
    if parent is None:
        return []
    series_list = []
    for series_elem in parent.findall("series"):
        series_id = series_elem.get("id")
        name = series_elem.get("name")
        catalog_number = series_elem.get("catno")
        if series_id and name:
            series_list.append(
                Series(id=int(series_id), catalog_number=catalog_number, name=name)
            )
    return series_list


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
                    description=video_elem.findtext("description"),
                    duration=int(duration),
                    embed=embed == "true",
                    src=src,
                    title=video_elem.findtext("title"),
                )
            )
    return videos


def _parse_genres(parent: etree._Element | None) -> list[str]:
    """Parse genres list."""
    return _parse_text_list(parent, "genre")


def _parse_styles(parent: etree._Element | None) -> list[str]:
    """Parse styles list."""
    return _parse_text_list(parent, "style")


class MasterReleaseParser:
    tag = "master"

    def parse(self, elem: etree._Element) -> Iterator[MasterRelease]:
        """Parse master XML element into MasterRelease record."""
        year_text = elem.findtext("year")
        year = int(year_text) if year_text else None

        main_release_text = elem.findtext("main_release")
        main_release = int(main_release_text) if main_release_text else None

        yield MasterRelease(
            id=int(elem.get("id")),
            data_quality=_parse_data_quality(elem),
            main_release=main_release,
            notes=elem.findtext("notes"),
            title=elem.findtext("title"),
            year=year,
            artists=_parse_credit_artists(elem.find("artists")),
            genres=_parse_genres(elem.find("genres")),
            styles=_parse_styles(elem.find("styles")),
            videos=_parse_videos(elem.find("videos")),
        )


class ReleaseParser:
    tag = "release"

    def parse(self, elem: etree._Element) -> Iterator[Release]:
        """Parse release XML element into Release record."""
        master_id_elem = elem.find("master_id")
        master_id = None
        is_main_release = None
        if master_id_elem is not None and master_id_elem.text:
            master_id = int(master_id_elem.text)
            is_main_attr = master_id_elem.get("is_main_release")
            is_main_release = is_main_attr == "true" if is_main_attr else None

        yield Release(
            id=int(elem.get("id")),
            country=elem.findtext("country"),
            data_quality=_parse_data_quality(elem),
            is_main_release=is_main_release,
            master_id=master_id,
            notes=elem.findtext("notes"),
            released=elem.findtext("released"),
            status=_parse_release_status(elem),
            title=elem.findtext("title"),
            artists=_parse_credit_artists(elem.find("artists")),
            companies=_parse_companies(elem.find("companies")),
            extra_artists=_parse_extra_artists(elem.find("extraartists")),
            formats=_parse_formats(elem.find("formats")),
            genres=_parse_genres(elem.find("genres")),
            identifiers=_parse_identifiers(elem.find("identifiers")),
            labels=_parse_release_labels(elem.find("labels")),
            series=_parse_series(elem.find("series")),
            styles=_parse_styles(elem.find("styles")),
            tracklist=_parse_tracks(elem.find("tracklist")),
            videos=_parse_videos(elem.find("videos")),
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
