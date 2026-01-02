import gzip

from contextlib import contextmanager
from pathlib import Path
from typing import IO, Iterator


class GzipReader:
    """Gzip reader with progress tracking support."""

    def __init__(self) -> None:
        self._fileobj: IO[bytes] | None = None
        self._total_size: int = 0

    @contextmanager
    def open(self, path: Path) -> Iterator[IO[bytes]]:
        self._total_size = path.stat().st_size
        with open(path, "rb") as compressed:
            self._fileobj = compressed
            with gzip.GzipFile(fileobj=compressed) as decompressed:
                yield decompressed
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
