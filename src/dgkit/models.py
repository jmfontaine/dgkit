from typing import NamedTuple


class ArtistRef(NamedTuple):
    """Reference to another artist (used for aliases, members, groups)."""

    id: int
    name: str


class Artist(NamedTuple):
    id: int
    data_quality: str | None
    name: str | None
    profile: str | None
    real_name: str | None
    aliases: list[ArtistRef] = []
    groups: list[ArtistRef] = []
    members: list[ArtistRef] = []
    name_variations: list[str] = []
    urls: list[str] = []


class LabelRef(NamedTuple):
    """Reference to another label (used for sub_labels, parent_label)."""

    id: int
    name: str


class Label(NamedTuple):
    id: int
    contact_info: str | None
    data_quality: str | None
    name: str | None
    profile: str | None
    parent_label: LabelRef | None = None
    sub_labels: list[LabelRef] = []
    urls: list[str] = []


class CreditArtist(NamedTuple):
    """Artist credit on a release or master."""

    id: int
    artist_name_variation: str | None
    join: str | None
    name: str


class ExtraArtist(NamedTuple):
    """Extra artist credit with role (producer, engineer, etc.)."""

    id: int | None
    artist_name_variation: str | None
    name: str
    role: str | None
    tracks: str | None


class ReleaseLabel(NamedTuple):
    """Label credit on a release."""

    id: int
    catalog_number: str | None
    name: str


class Format(NamedTuple):
    """Physical format of a release."""

    name: str
    quantity: int
    text: str | None
    descriptions: list[str] = []


class SubTrack(NamedTuple):
    """Sub-track within a track (movements, sections)."""

    duration: str | None
    position: str | None
    title: str | None
    artists: list[CreditArtist] = []
    extra_artists: list[ExtraArtist] = []


class Track(NamedTuple):
    """Track on a release."""

    duration: str | None
    position: str | None
    title: str | None
    artists: list[CreditArtist] = []
    extra_artists: list[ExtraArtist] = []
    sub_tracks: list[SubTrack] = []


class Identifier(NamedTuple):
    """Identifier like barcode, matrix, etc."""

    description: str | None
    type: str
    value: str


class Company(NamedTuple):
    """Company credit on a release."""

    id: int
    catalog_number: str | None
    entity_type: int | None
    entity_type_name: str | None
    name: str


class Series(NamedTuple):
    """Series a release belongs to."""

    id: int
    catalog_number: str | None
    name: str


class Video(NamedTuple):
    """Video associated with a master release."""

    description: str | None
    duration: int
    embed: bool
    src: str
    title: str | None


class MasterRelease(NamedTuple):
    id: int
    data_quality: str | None
    main_release: int | None
    notes: str | None
    title: str | None
    year: int | None
    artists: list[CreditArtist] = []
    genres: list[str] = []
    styles: list[str] = []
    videos: list[Video] = []


class Release(NamedTuple):
    id: int
    country: str | None
    data_quality: str | None
    is_main_release: bool | None
    master_id: int | None
    notes: str | None
    released: str | None
    status: str | None
    title: str | None
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
