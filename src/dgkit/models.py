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


class MasterRelease(NamedTuple):
    id: int
    title: str | None


class Release(NamedTuple):
    id: int
    title: str | None
