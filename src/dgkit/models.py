from typing import NamedTuple


class Artist(NamedTuple):
    id: int
    name: str | None
    profile: str | None
    real_name: str | None
    aliases: list[int] = []
    name_variations: list[str] = []
    urls: list[str] = []


class Label(NamedTuple):
    id: int
    name: str | None


class MasterRelease(NamedTuple):
    id: int
    title: str | None


class Release(NamedTuple):
    id: int
    title: str | None
