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
    """Reference to another label (used for sublabels, parent_label)."""
    id: int
    name: str


class Label(NamedTuple):
    id: int
    name: str | None
    contact_info: str | None
    profile: str | None
    data_quality: str | None
    urls: list[str] = []
    sublabels: list[LabelRef] = []
    parent_label: LabelRef | None = None


class MasterArtist(NamedTuple):
    """Artist credit on a master release."""
    id: int
    name: str
    anv: str | None
    join: str | None


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
    artists: list[MasterArtist] = []
    genres: list[str] = []
    styles: list[str] = []
    videos: list[Video] = []


class Release(NamedTuple):
    id: int
    title: str | None
