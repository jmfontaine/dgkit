import bz2
import gzip
import json
import sqlite3
from importlib.resources import files
from urllib.parse import urlparse

from pathlib import Path
from typing import IO, Any, NamedTuple, Self, get_args, get_origin

from dgkit.types import Compression, DatabaseType, FileFormat, Writer


def _get_list_element_type(field_type: type) -> type | None:
    """Get the element type of a list type annotation, or None if not a list."""
    origin = get_origin(field_type)
    if origin is list:
        args = get_args(field_type)
        return args[0] if args else None
    return None


def _singularize(name: str) -> str:
    """Simple singularization: remove trailing 's' or 'es'."""
    if name.endswith("ies"):
        return name[:-3] + "y"
    if name.endswith("es"):
        return name[:-2]
    if name.endswith("s"):
        return name[:-1]
    return name


def parse_sqlite_dsn(dsn: str) -> str:
    """Parse SQLite DSN and return the database path.

    Supports:
    - sqlite:///./relative.db (relative path)
    - sqlite:////absolute/path.db (absolute path)
    - sqlite://:memory: (in-memory)
    - Plain path (passed through as-is)
    """
    parsed = urlparse(dsn)

    # Plain path (no scheme)
    if not parsed.scheme:
        return dsn

    if parsed.scheme != "sqlite":
        raise ValueError(f"Unsupported scheme: {parsed.scheme}")

    # Handle :memory: special case
    if parsed.path == "/:memory:":
        return ":memory:"

    # urlparse keeps leading slash, remove one level for relative paths
    # sqlite:///./foo.db -> path="/./foo.db" -> "./foo.db"
    # sqlite:////absolute/path.db -> path="//absolute/path.db" -> "/absolute/path.db"
    if parsed.path.startswith("/"):
        return parsed.path[1:]

    return parsed.path


def _load_sql(database: str, category: str, name: str) -> str | None:
    """Load SQL from package resources."""
    try:
        resource = files("dgkit.sql") / database / category / f"{name}.sql"
        return resource.read_text()
    except FileNotFoundError:
        return None


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

    def __init__(self, dsn: str, batch_size: int = 10000, **kwargs: Any):
        self.dsn = dsn
        self.path = parse_sqlite_dsn(dsn)
        self.batch_size = batch_size
        self._conn: sqlite3.Connection | None = None
        self._tables: set[str] = set()
        self._buffers: dict[str, list[tuple]] = {}
        # Cache of junction table info: {(table, field): junction_table_name}
        self._junction_tables: dict[tuple[str, str], str] = {}
        # Cache of fields to exclude from main table (junction table fields)
        self._junction_fields: dict[str, set[str]] = {}

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

        annotations = type(record).__annotations__
        junction_fields: set[str] = set()

        # Identify junction table fields (list[int])
        for field, field_type in annotations.items():
            elem_type = _get_list_element_type(field_type)
            if elem_type is int:
                junction_fields.add(field)
                junction_table = f"{table_name}{_singularize(field)}"
                self._junction_tables[(table_name, field)] = junction_table

        self._junction_fields[table_name] = junction_fields

        # Drop and recreate main table
        self._conn.execute(f"DROP TABLE IF EXISTS {table_name}")

        # Try to load schema from SQL file
        sql = _load_sql("sqlite", "tables", table_name)
        if sql:
            self._conn.execute(sql)
        else:
            # Fall back to dynamic schema generation (excluding junction fields)
            fields = record._fields
            columns = []
            for i, field in enumerate(fields):
                if field in junction_fields:
                    continue
                field_type = annotations.get(field, str)
                if hasattr(field_type, "__origin__"):
                    args = getattr(field_type, "__args__", ())
                    field_type = next((t for t in args if t is not type(None)), str)
                sqlite_type = SQLITE_TYPE_MAP.get(field_type, "TEXT")
                if i == 0 and sqlite_type == "INTEGER":
                    columns.append(f"{field} INTEGER PRIMARY KEY")
                else:
                    columns.append(f"{field} {sqlite_type}")
            self._conn.execute(f"CREATE TABLE {table_name} ({', '.join(columns)})")

        self._tables.add(table_name)
        self._buffers[table_name] = []

        # Create junction tables
        for field in junction_fields:
            junction_table = self._junction_tables[(table_name, field)]
            self._conn.execute(f"DROP TABLE IF EXISTS {junction_table}")

            sql = _load_sql("sqlite", "tables", junction_table)
            if sql:
                self._conn.execute(sql)
            else:
                # Dynamic junction table: {table}_id, {field_singular}_id
                fk_col = f"{table_name}_id"
                ref_col = f"{_singularize(field)}_id"
                self._conn.execute(
                    f"CREATE TABLE {junction_table} ("
                    f"{fk_col} INTEGER NOT NULL, "
                    f"{ref_col} INTEGER NOT NULL, "
                    f"PRIMARY KEY ({fk_col}, {ref_col}))"
                )

            self._tables.add(junction_table)
            self._buffers[junction_table] = []

        return table_name

    def _create_indices(self) -> None:
        """Create indices on tables after data insertion."""
        if not self._conn:
            return
        for table_name in self._tables:
            sql = _load_sql("sqlite", "indices", table_name)
            if sql:
                self._conn.execute(sql)

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
        junction_fields = self._junction_fields.get(table_name, set())
        record_id = record[0]  # Assume first field is the ID

        # Build main table values (excluding junction fields, serialize other lists as JSON)
        main_values: list[Any] = []
        for field, value in zip(record._fields, record):
            if field in junction_fields:
                continue
            if isinstance(value, list):
                main_values.append(json.dumps(value))
            else:
                main_values.append(value)

        self._buffers[table_name].append(tuple(main_values))
        if len(self._buffers[table_name]) >= self.batch_size:
            self._flush(table_name)

        # Insert junction table entries
        for field in junction_fields:
            junction_table = self._junction_tables[(table_name, field)]
            field_idx = record._fields.index(field)
            values = record[field_idx]
            if values:
                for ref_id in values:
                    self._buffers[junction_table].append((record_id, ref_id))
                if len(self._buffers[junction_table]) >= self.batch_size:
                    self._flush(junction_table)


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
