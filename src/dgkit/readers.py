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
