import bz2
import gzip
import json
import sqlite3

from pathlib import Path
from typing import IO, Any, NamedTuple, Self

from dgkit.types import Compression, Format, Writer


def open_compressed(path: Path, mode: str, compression: Compression) -> IO:
    """Open a file with optional compression."""
    match compression:
        case Compression.gzip:
            return gzip.open(path, mode)
        case Compression.bz2:
            return bz2.open(path, mode)
        case _:
            return open(path, mode)


class BlackholeWriter:
    """Writer that drops records. This is mostly useful for benchmarking."""

    aggregates_inputs = True

    def __init__(self, **kwargs: Any):
        pass

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        pass

    def write(self, record: NamedTuple) -> None:
        pass


class ConsoleWriter:
    """Writer that prints records to the console."""

    aggregates_inputs = True

    def __init__(self, **kwargs: Any):
        pass

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        pass

    def write(self, record: NamedTuple) -> None:
        from rich import print
        print(record)


class JsonlWriter:
    """Writer that outputs records as JSON Lines."""

    aggregates_inputs = False

    def __init__(self, path: Path, compression: Compression = Compression.none):
        self.path = path
        self.compression = compression
        self._fp: IO | None = None

    def __enter__(self) -> Self:
        self._fp = open_compressed(self.path, "wt", self.compression)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if self._fp:
            self._fp.close()

    def write(self, record: NamedTuple) -> None:
        if self._fp:
            self._fp.write(json.dumps(record._asdict()) + "\n")


SQLITE_TYPE_MAP: dict[type, str] = {
    int: "INTEGER",
    float: "REAL",
    str: "TEXT",
    bool: "INTEGER",
    bytes: "BLOB",
}


class SqliteWriter:
    """Writer that outputs records to a SQLite database."""

    aggregates_inputs = True

    def __init__(self, path: Path, **kwargs: Any):
        self.path = path
        self._conn: sqlite3.Connection | None = None
        self._tables: set[str] = set()

    def __enter__(self) -> Self:
        self._conn = sqlite3.connect(self.path)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if self._conn:
            self._conn.commit()
            self._conn.close()

    def _ensure_table(self, record: NamedTuple) -> str:
        """Create table for record type if it doesn't exist."""
        table_name = type(record).__name__.lower()
        if table_name in self._tables:
            return table_name

        fields = record._fields
        annotations = type(record).__annotations__

        columns = []
        for field in fields:
            field_type = annotations.get(field, str)
            # Handle Optional types (e.g., str | None)
            if hasattr(field_type, "__origin__"):
                args = getattr(field_type, "__args__", ())
                field_type = next((t for t in args if t is not type(None)), str)
            sqlite_type = SQLITE_TYPE_MAP.get(field_type, "TEXT")
            columns.append(f"{field} {sqlite_type}")

        self._conn.execute(f"DROP TABLE IF EXISTS {table_name}")
        self._conn.execute(f"CREATE TABLE {table_name} ({', '.join(columns)})")
        self._tables.add(table_name)
        return table_name

    def write(self, record: NamedTuple) -> None:
        if not self._conn:
            return
        table_name = self._ensure_table(record)
        # Serialize lists as JSON strings
        values = tuple(
            json.dumps(v) if isinstance(v, list) else v for v in record
        )
        placeholders = ", ".join("?" * len(record))
        sql = f"INSERT INTO {table_name} VALUES ({placeholders})"
        self._conn.execute(sql, values)


WRITERS: dict[Format, type[Writer]] = {
    Format.blackhole: BlackholeWriter,
    Format.console: ConsoleWriter,
    Format.jsonl: JsonlWriter,
    Format.sqlite: SqliteWriter,
}


def get_writer(format: Format, **kwargs: Any) -> Writer:
    """Create a writer for the given format."""
    if format not in WRITERS:
        raise NotImplementedError(f"Writer for {format.value} not implemented")
    return WRITERS[format](**kwargs)
