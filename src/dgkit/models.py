from msgspec import Struct, field


class ArtistRef(Struct):
    """Reference to another artist (used for aliases, members, groups)."""

    id: int | None
    name: str | None


class Artist(Struct):
    id: int
    data_quality: str | None
    name: str | None
    profile: str | None
    real_name: str | None
    aliases: list[ArtistRef] = field(default_factory=list)
    groups: list[ArtistRef] = field(default_factory=list)
    members: list[ArtistRef] = field(default_factory=list)
    name_variations: list[str] = field(default_factory=list)
    urls: list[str] = field(default_factory=list)


class LabelRef(Struct):
    """Reference to another label (used for sub_labels, parent_label)."""

    id: int | None
    name: str | None


class Label(Struct):
    id: int
    contact_info: str | None
    data_quality: str | None
    name: str | None
    profile: str | None
    parent_label: LabelRef | None = None
    sub_labels: list[LabelRef] = field(default_factory=list)
    urls: list[str] = field(default_factory=list)


class CreditArtist(Struct):
    """Artist credit on a release or master."""

    id: int | None
    artist_name_variation: str | None
    join: str | None
    name: str | None


class ExtraArtist(Struct):
    """Extra artist credit with role (producer, engineer, etc.)."""

    id: int | None
    artist_name_variation: str | None
    name: str | None
    role: str | None
    tracks: str | None


class ReleaseLabel(Struct):
    """Label credit on a release."""

    id: int | None
    catalog_number: str | None
    name: str | None


class Format(Struct):
    """Physical format of a release."""

    name: str | None
    # KLUDGE: Should be int, but some Discogs releases have values exceeding BIGINT.
    # Example: "1000000000000000000000000000000000000000000000000000000000000001"
    # See: https://www.discogs.com/release/8262262
    quantity: str | None
    text: str | None
    descriptions: list[str] = field(default_factory=list)


class SubTrack(Struct):
    """Sub-track within a track (movements, sections)."""

    duration: str | None
    position: str | None
    title: str | None
    artists: list[CreditArtist] = field(default_factory=list)
    extra_artists: list[ExtraArtist] = field(default_factory=list)


class Track(Struct):
    """Track on a release."""

    duration: str | None
    position: str | None
    title: str | None
    artists: list[CreditArtist] = field(default_factory=list)
    extra_artists: list[ExtraArtist] = field(default_factory=list)
    sub_tracks: list[SubTrack] = field(default_factory=list)


class Identifier(Struct):
    """Identifier like barcode, matrix, etc."""

    type: str | None
    description: str | None
    value: str | None


class Company(Struct):
    """Company credit on a release."""

    id: int | None
    catalog_number: str | None
    entity_type: int | None
    entity_type_name: str | None
    name: str | None


class Series(Struct):
    """Series a release belongs to."""

    id: int | None
    catalog_number: str | None
    name: str | None


class Video(Struct):
    """Video associated with a master release."""

    description: str | None
    duration: int | None
    embed: bool | None
    src: str | None
    title: str | None


class MasterRelease(Struct):
    id: int
    data_quality: str | None
    main_release: int | None
    notes: str | None
    title: str | None
    year: int | None
    artists: list[CreditArtist] = field(default_factory=list)
    genres: list[str] = field(default_factory=list)
    styles: list[str] = field(default_factory=list)
    videos: list[Video] = field(default_factory=list)


class Release(Struct):
    id: int
    country: str | None
    data_quality: str | None
    is_main_release: bool | None
    master_id: int | None
    notes: str | None
    released: str | None
    status: str | None
    title: str | None
    artists: list[CreditArtist] = field(default_factory=list)
    companies: list[Company] = field(default_factory=list)
    extra_artists: list[ExtraArtist] = field(default_factory=list)
    formats: list[Format] = field(default_factory=list)
    genres: list[str] = field(default_factory=list)
    identifiers: list[Identifier] = field(default_factory=list)
    labels: list[ReleaseLabel] = field(default_factory=list)
    series: list[Series] = field(default_factory=list)
    styles: list[str] = field(default_factory=list)
    tracklist: list[Track] = field(default_factory=list)
    videos: list[Video] = field(default_factory=list)
