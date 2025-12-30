from typing import NamedTuple


class Artist(NamedTuple):
    id: int
    name: str | None
    profile: str | None
    real_name: str | None
    urls: list[str] = []


class ArtistAlias(NamedTuple):
    artist_id: int
    alias_id: int


class Label(NamedTuple):
    id: int
    name: str | None


class MasterRelease(NamedTuple):
    id: int
    title: str | None


class Release(NamedTuple):
    id: int
    title: str | None
