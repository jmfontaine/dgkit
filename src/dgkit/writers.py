import bz2
import gzip
import json
import sqlite3

from pathlib import Path
from typing import IO, Any, NamedTuple, Self

from dgkit.types import Compression, DatabaseType, FileFormat, Writer


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

    # Columns to index after data insertion (by table name)
    INDEX_COLUMNS: dict[str, list[str]] = {
        "artist": ["name"],
        "label": ["name"],
        "masterrelease": ["title"],
        "release": ["title"],
    }

    def __init__(self, path: Path, batch_size: int = 10000, **kwargs: Any):
        self.path = path
        self.batch_size = batch_size
        self._conn: sqlite3.Connection | None = None
        self._tables: set[str] = set()
        self._buffers: dict[str, list[tuple]] = {}

    def __enter__(self) -> Self:
        self._conn = sqlite3.connect(self.path)
        # Performance optimizations for bulk inserts
        self._conn.execute("PRAGMA journal_mode = WAL")
        self._conn.execute("PRAGMA synchronous = NORMAL")
        self._conn.execute("PRAGMA cache_size = -64000")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if self._conn:
            self._flush_all()
            if not exc_type:
                self._create_indices()
                self._conn.execute("ANALYZE")
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
        for i, field in enumerate(fields):
            field_type = annotations.get(field, str)
            # Handle Optional types (e.g., str | None)
            if hasattr(field_type, "__origin__"):
                args = getattr(field_type, "__args__", ())
                field_type = next((t for t in args if t is not type(None)), str)
            sqlite_type = SQLITE_TYPE_MAP.get(field_type, "TEXT")
            # First integer column becomes PRIMARY KEY
            if i == 0 and sqlite_type == "INTEGER":
                columns.append(f"{field} INTEGER PRIMARY KEY")
            else:
                columns.append(f"{field} {sqlite_type}")

        self._conn.execute(f"DROP TABLE IF EXISTS {table_name}")
        self._conn.execute(f"CREATE TABLE {table_name} ({', '.join(columns)})")
        self._tables.add(table_name)
        self._buffers[table_name] = []
        return table_name

    def _create_indices(self) -> None:
        """Create indices on tables after data insertion."""
        if not self._conn:
            return
        for table_name in self._tables:
            for column in self.INDEX_COLUMNS.get(table_name, []):
                index_name = f"idx_{table_name}_{column}"
                self._conn.execute(
                    f"CREATE INDEX IF NOT EXISTS {index_name} ON {table_name}({column})"
                )

    def _flush(self, table_name: str) -> None:
        """Flush buffered records to the database."""
        if not self._conn or table_name not in self._buffers:
            return
        buffer = self._buffers[table_name]
        if not buffer:
            return
        placeholders = ", ".join("?" * len(buffer[0]))
        sql = f"INSERT INTO {table_name} VALUES ({placeholders})"
        self._conn.executemany(sql, buffer)
        buffer.clear()

    def _flush_all(self) -> None:
        """Flush all buffered records."""
        for table_name in self._buffers:
            self._flush(table_name)

    def write(self, record: NamedTuple) -> None:
        if not self._conn:
            return
        table_name = self._ensure_table(record)
        # Serialize lists as JSON strings
        values = tuple(
            json.dumps(v) if isinstance(v, list) else v for v in record
        )
        self._buffers[table_name].append(values)
        if len(self._buffers[table_name]) >= self.batch_size:
            self._flush(table_name)


FILE_WRITERS: dict[FileFormat, type[Writer]] = {
    FileFormat.blackhole: BlackholeWriter,
    FileFormat.console: ConsoleWriter,
    FileFormat.jsonl: JsonlWriter,
}


DATABASE_WRITERS: dict[DatabaseType, type[Writer]] = {
    DatabaseType.sqlite: SqliteWriter,
}


def get_file_writer(format: FileFormat, **kwargs: Any) -> Writer:
    """Create a writer for the given file format."""
    if format not in FILE_WRITERS:
        raise NotImplementedError(f"Writer for {format.value} not implemented")
    return FILE_WRITERS[format](**kwargs)


def get_database_writer(database: DatabaseType, **kwargs: Any) -> Writer:
    """Create a writer for the given database type."""
    if database not in DATABASE_WRITERS:
        raise NotImplementedError(f"Writer for {database.value} not implemented")
    return DATABASE_WRITERS[database](**kwargs)
