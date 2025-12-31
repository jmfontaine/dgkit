from typing import NamedTuple


class ArtistRef(NamedTuple):
    """Reference to another artist (used for aliases, members, groups)."""

    id: int
    name: str


class Artist(NamedTuple):
    id: int
    name: str | None
    real_name: str | None
    profile: str | None
    data_quality: str | None
    urls: list[str] = []
    name_variations: list[str] = []
    aliases: list[ArtistRef] = []
    members: list[ArtistRef] = []
    groups: list[ArtistRef] = []


class LabelRef(NamedTuple):
    """Reference to another label (used for sub_labels, parent_label)."""

    id: int
    name: str


class Label(NamedTuple):
    id: int
    name: str | None
    contact_info: str | None
    profile: str | None
    data_quality: str | None
    urls: list[str] = []
    sub_labels: list[LabelRef] = []
    parent_label: LabelRef | None = None


class CreditArtist(NamedTuple):
    """Artist credit on a release or master."""

    id: int
    name: str
    artist_name_variation: str | None
    join: str | None


class ExtraArtist(NamedTuple):
    """Extra artist credit with role (producer, engineer, etc.)."""

    id: int | None
    name: str
    artist_name_variation: str | None
    role: str | None
    tracks: str | None


class ReleaseLabel(NamedTuple):
    """Label credit on a release."""

    id: int
    name: str
    catalog_number: str | None


class Format(NamedTuple):
    """Physical format of a release."""

    name: str
    quantity: int
    text: str | None
    descriptions: list[str] = []


class SubTrack(NamedTuple):
    """Sub-track within a track (movements, sections)."""

    position: str | None
    title: str | None
    duration: str | None
    artists: list[CreditArtist] = []
    extra_artists: list[ExtraArtist] = []


class Track(NamedTuple):
    """Track on a release."""

    position: str | None
    title: str | None
    duration: str | None
    artists: list[CreditArtist] = []
    extra_artists: list[ExtraArtist] = []
    sub_tracks: list[SubTrack] = []


class Identifier(NamedTuple):
    """Identifier like barcode, matrix, etc."""

    type: str
    description: str | None
    value: str


class Company(NamedTuple):
    """Company credit on a release."""

    id: int
    name: str
    catalog_number: str | None
    entity_type: int | None
    entity_type_name: str | None


class Series(NamedTuple):
    """Series a release belongs to."""

    id: int
    name: str
    catalog_number: str | None


class Video(NamedTuple):
    """Video associated with a master release."""

    src: str
    duration: int
    embed: bool
    title: str | None
    description: str | None


class MasterRelease(NamedTuple):
    id: int
    title: str | None
    main_release: int | None
    year: int | None
    notes: str | None
    data_quality: str | None
    artists: list[CreditArtist] = []
    genres: list[str] = []
    styles: list[str] = []
    videos: list[Video] = []


class Release(NamedTuple):
    id: int
    status: str | None
    title: str | None
    country: str | None
    released: str | None
    notes: str | None
    data_quality: str | None
    master_id: int | None
    is_main_release: bool | None
    artists: list[CreditArtist] = []
    labels: list[ReleaseLabel] = []
    extra_artists: list[ExtraArtist] = []
    formats: list[Format] = []
    genres: list[str] = []
    styles: list[str] = []
    tracklist: list[Track] = []
    identifiers: list[Identifier] = []
    videos: list[Video] = []
    companies: list[Company] = []
    series: list[Series] = []
