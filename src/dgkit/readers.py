import gzip

from contextlib import contextmanager
from pathlib import Path
from typing import IO, Iterator


class GzipReader:
    """Reader using standard gzip module."""

    @contextmanager
    def open(self, path: Path) -> Iterator[IO[bytes]]:
        with gzip.open(path, "rb") as fp:
            yield fp


class TrackingGzipReader:
    """Gzip reader that tracks compressed bytes read for progress reporting."""

    def __init__(self):
        self._fileobj: IO[bytes] | None = None
        self._total_size: int = 0

    @contextmanager
    def open(self, path: Path) -> Iterator[IO[bytes]]:
        self._total_size = path.stat().st_size
        with open(path, "rb") as raw:
            self._fileobj = raw
            with gzip.GzipFile(fileobj=raw) as gz:
                yield gz
            self._fileobj = None

    @property
    def total_size(self) -> int:
        """Total compressed file size in bytes."""
        return self._total_size

    @property
    def bytes_read(self) -> int:
        """Compressed bytes read so far."""
        if self._fileobj is None:
            return 0
        return self._fileobj.tell()
