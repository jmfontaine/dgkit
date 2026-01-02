import re
from pathlib import Path
from typing import Iterator

from dgkit.models import (
    Artist,
    ArtistRef,
    Company,
    CreditArtist,
    ExtraArtist,
    Format,
    Identifier,
    Label,
    LabelRef,
    MasterRelease,
    Release,
    ReleaseLabel,
    Series,
    SubTrack,
    Track,
    Video,
)
from dgkit.types import Element, Parser


def _require_int(value: str | None, field: str = "id") -> int:
    """Convert string to int, raising ValueError if None or empty."""
    if not value:
        raise ValueError(f"Required field '{field}' is missing or empty")
    return int(value)


# KLUDGE: _parse_text_list was inlined at call sites to eliminate ~3M function
# calls when processing 1M releases. See decision 0002. The pattern:
#   [e.text for e in p.findall("tag") if e.text] if (p := elem.find("parent")) is not None else []
# replaces what was previously: _parse_text_list(elem.find("parent"), "tag")


def _parse_artist_refs(parent: Element | None) -> list[ArtistRef]:
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

    def parse(self, elem: Element) -> Iterator[Artist]:
        """Parse artist XML element into Artist record."""
        yield Artist(
            id=_require_int(elem.findtext("id")),
            data_quality=elem.findtext("data_quality"),
            name=elem.findtext("name"),
            profile=elem.findtext("profile"),
            real_name=elem.findtext("realname"),
            aliases=_parse_artist_refs(elem.find("aliases")),
            groups=_parse_artist_refs(elem.find("groups")),
            members=_parse_artist_refs(elem.find("members")),
            name_variations=(
                [e.text for e in p.findall("name") if e.text]
                if (p := elem.find("namevariations")) is not None
                else []
            ),
            urls=(
                [e.text for e in p.findall("url") if e.text]
                if (p := elem.find("urls")) is not None
                else []
            ),
        )


def _parse_label_refs(parent: Element | None) -> list[LabelRef]:
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

    def parse(self, elem: Element) -> Iterator[Label]:
        """Parse label XML element into Label record."""
        parent_label_elem = elem.find("parentLabel")
        parent_label = None
        if parent_label_elem is not None:
            parent_id = parent_label_elem.get("id")
            if parent_id and parent_label_elem.text:
                parent_label = LabelRef(id=int(parent_id), name=parent_label_elem.text)

        yield Label(
            id=_require_int(elem.get("id") or elem.findtext("id")),
            contact_info=elem.findtext("contactinfo"),
            data_quality=elem.findtext("data_quality"),
            name=elem.findtext("name") or elem.text,
            profile=elem.findtext("profile"),
            parent_label=parent_label,
            sub_labels=_parse_label_refs(elem.find("sublabels")),
            urls=(
                [e.text for e in p.findall("url") if e.text]
                if (p := elem.find("urls")) is not None
                else []
            ),
        )


def _parse_credit_artists(parent: Element | None) -> list[CreditArtist]:
    """Parse artist credits (id, name, artist_name_variation, join).

    KLUDGE: Uses single-pass iteration over children instead of multiple
    findtext() calls. Called ~3M times for 1M releases, so avoiding repeated
    tree traversals is significant. See decision 0002.
    """
    if parent is None:
        return []
    artists = []
    for artist_elem in parent:
        if artist_elem.tag != "artist":
            continue
        artist_id = None
        name = None
        anv = None
        join = None
        for child in artist_elem:
            tag = child.tag
            if tag == "id":
                artist_id = child.text
            elif tag == "name":
                name = child.text
            elif tag == "anv":
                anv = child.text
            elif tag == "join":
                join = child.text
        if artist_id and name:
            artists.append(
                CreditArtist(
                    id=int(artist_id),
                    artist_name_variation=anv,
                    join=join,
                    name=name,
                )
            )
    return artists


def _parse_extra_artists(parent: Element | None) -> list[ExtraArtist]:
    """Parse extra artist credits (producer, engineer, etc.).

    KLUDGE: Uses single-pass iteration over children instead of multiple
    findtext() calls. Called ~3M times for 1M releases, so avoiding repeated
    tree traversals is significant. See decision 0002.
    """
    if parent is None:
        return []
    artists = []
    for artist_elem in parent:
        if artist_elem.tag != "artist":
            continue
        artist_id = None
        name = None
        anv = None
        role = None
        tracks = None
        for child in artist_elem:
            tag = child.tag
            if tag == "id":
                artist_id = int(child.text) if child.text else None
            elif tag == "name":
                name = child.text
            elif tag == "anv":
                anv = child.text
            elif tag == "role":
                role = child.text
            elif tag == "tracks":
                tracks = child.text
        if name:
            artists.append(
                ExtraArtist(
                    id=artist_id,
                    artist_name_variation=anv,
                    name=name,
                    role=role,
                    tracks=tracks,
                )
            )
    return artists


def _parse_release_labels(parent: Element | None) -> list[ReleaseLabel]:
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


def _parse_formats(parent: Element | None) -> list[Format]:
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
                    name=name,
                    quantity=int(quantity_text),
                    text=text,
                    descriptions=(
                        [e.text for e in p.findall("description") if e.text]
                        if (p := format_elem.find("descriptions")) is not None
                        else []
                    ),
                )
            )
    return formats


def _parse_sub_tracks(parent: Element | None) -> list[SubTrack]:
    """Parse sub_tracks within a track."""
    if parent is None:
        return []
    sub_tracks = []
    for track_elem in parent:
        if track_elem.tag != "track":
            continue
        position = None
        title = None
        duration = None
        artists: list[CreditArtist] = []
        extra_artists: list[ExtraArtist] = []
        for child in track_elem:
            tag = child.tag
            if tag == "position":
                position = child.text
            elif tag == "title":
                title = child.text
            elif tag == "duration":
                duration = child.text
            elif tag == "artists":
                artists = _parse_credit_artists(child)
            elif tag == "extraartists":
                extra_artists = _parse_extra_artists(child)
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


def _parse_tracks(parent: Element | None) -> list[Track]:
    """Parse tracklist."""
    if parent is None:
        return []
    tracks = []
    for track_elem in parent:
        if track_elem.tag != "track":
            continue
        position = None
        title = None
        duration = None
        artists: list[CreditArtist] = []
        extra_artists: list[ExtraArtist] = []
        sub_tracks: list[SubTrack] = []
        for child in track_elem:
            tag = child.tag
            if tag == "position":
                position = child.text
            elif tag == "title":
                title = child.text
            elif tag == "duration":
                duration = child.text
            elif tag == "artists":
                artists = _parse_credit_artists(child)
            elif tag == "extraartists":
                extra_artists = _parse_extra_artists(child)
            elif tag == "sub_tracks":
                sub_tracks = _parse_sub_tracks(child)
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


def _parse_identifiers(parent: Element | None) -> list[Identifier]:
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
                    type=id_type,
                    value=value,
                )
            )
    return identifiers


def _parse_companies(parent: Element | None) -> list[Company]:
    """Parse company credits."""
    if parent is None:
        return []
    companies = []
    for company_elem in parent:
        if company_elem.tag != "company":
            continue
        company_id = None
        name = None
        catalog_number = None
        entity_type = None
        entity_type_name = None
        for child in company_elem:
            tag = child.tag
            if tag == "id":
                company_id = child.text
            elif tag == "name":
                name = child.text
            elif tag == "catno":
                catalog_number = child.text
            elif tag == "entity_type":
                entity_type = int(child.text) if child.text else None
            elif tag == "entity_type_name":
                entity_type_name = child.text
            # resource_url is implicitly handled by iterating
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


def _parse_series(parent: Element | None) -> list[Series]:
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


def _parse_videos(parent: Element | None) -> list[Video]:
    """Parse videos from a master release."""
    if parent is None:
        return []
    videos = []
    for video_elem in parent:
        if video_elem.tag != "video":
            continue
        src = video_elem.get("src")
        duration = video_elem.get("duration")
        embed = video_elem.get("embed")
        if src and duration:
            description = None
            title = None
            for child in video_elem:
                tag = child.tag
                if tag == "description":
                    description = child.text
                elif tag == "title":
                    title = child.text
            videos.append(
                Video(
                    description=description,
                    duration=int(duration),
                    embed=embed == "true",
                    src=src,
                    title=title,
                )
            )
    return videos


def _parse_genres(parent: Element | None) -> list[str]:
    """Parse genres list."""
    if parent is None:
        return []
    return [e.text for e in parent.findall("genre") if e.text]


def _parse_styles(parent: Element | None) -> list[str]:
    """Parse styles list."""
    if parent is None:
        return []
    return [e.text for e in parent.findall("style") if e.text]


class MasterReleaseParser:
    tag = "master"

    def parse(self, elem: Element) -> Iterator[MasterRelease]:
        """Parse master XML element into MasterRelease record."""
        year_text = elem.findtext("year")
        year = int(year_text) if year_text else None

        main_release_text = elem.findtext("main_release")
        main_release = int(main_release_text) if main_release_text else None

        yield MasterRelease(
            id=_require_int(elem.get("id")),
            data_quality=elem.findtext("data_quality"),
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

    def parse(self, elem: Element) -> Iterator[Release]:
        """Parse release XML element into Release record."""
        # Get attributes from element
        release_id = _require_int(elem.get("id"))
        status = elem.get("status")

        # Initialize all fields
        country = None
        data_quality = None
        master_id = None
        is_main_release = None
        notes = None
        released = None
        title = None
        artists: list[CreditArtist] = []
        companies: list[Company] = []
        extra_artists: list[ExtraArtist] = []
        formats: list[Format] = []
        genres: list[str] = []
        identifiers: list[Identifier] = []
        labels: list[ReleaseLabel] = []
        series: list[Series] = []
        styles: list[str] = []
        tracklist: list[Track] = []
        videos: list[Video] = []

        # Single iteration over children
        for child in elem:
            tag = child.tag
            if tag == "country":
                country = child.text
            elif tag == "data_quality":
                data_quality = child.text
            elif tag == "master_id":
                if child.text:
                    master_id = int(child.text)
                    is_main_attr = child.get("is_main_release")
                    is_main_release = is_main_attr == "true" if is_main_attr else None
            elif tag == "notes":
                notes = child.text
            elif tag == "released":
                released = child.text
            elif tag == "title":
                title = child.text
            elif tag == "artists":
                artists = _parse_credit_artists(child)
            elif tag == "companies":
                companies = _parse_companies(child)
            elif tag == "extraartists":
                extra_artists = _parse_extra_artists(child)
            elif tag == "formats":
                formats = _parse_formats(child)
            elif tag == "genres":
                genres = _parse_genres(child)
            elif tag == "identifiers":
                identifiers = _parse_identifiers(child)
            elif tag == "labels":
                labels = _parse_release_labels(child)
            elif tag == "series":
                series = _parse_series(child)
            elif tag == "styles":
                styles = _parse_styles(child)
            elif tag == "tracklist":
                tracklist = _parse_tracks(child)
            elif tag == "videos":
                videos = _parse_videos(child)

        yield Release(
            id=release_id,
            country=country,
            data_quality=data_quality,
            is_main_release=is_main_release,
            master_id=master_id,
            notes=notes,
            released=released,
            status=status,
            title=title,
            artists=artists,
            companies=companies,
            extra_artists=extra_artists,
            formats=formats,
            genres=genres,
            identifiers=identifiers,
            labels=labels,
            series=series,
            styles=styles,
            tracklist=tracklist,
            videos=videos,
        )


PARSERS: dict[str, type[Parser]] = {
    "artists": ArtistParser,
    "labels": LabelParser,
    "masters": MasterReleaseParser,
    "releases": ReleaseParser,
}

# Matches: discogs_YYYYMMDD_<entity>.xml.gz or discogs_YYYYMMDD_<entity>_sample_N.xml.gz
FILENAME_PATTERN = re.compile(
    r"discogs_\d{8}_(artists|labels|masters|releases)(?:_sample_\d+)?\.xml\.gz"
)


def get_parser(path: Path, entity_type: str | None = None) -> Parser:
    """Create a parser based on filename pattern or explicit entity type.

    Args:
        path: Path to the input file.
        entity_type: Optional entity type override (artists, labels, masters, releases).
                     If provided, bypasses filename detection.

    Returns:
        Parser instance for the entity type.

    Raises:
        ValueError: If filename doesn't match pattern and no entity_type provided.
        NotImplementedError: If entity type is not supported.
    """
    if entity_type:
        entity = entity_type
    else:
        match = FILENAME_PATTERN.match(path.name)
        if not match:
            raise ValueError(
                f"Unrecognized filename pattern: {path.name}. "
                f"Use --type to specify entity type."
            )
        entity = match.group(1)
    if entity not in PARSERS:
        raise NotImplementedError(f"Parser for {entity} not implemented")
    return PARSERS[entity]()
