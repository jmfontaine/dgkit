import bz2
import gzip
import json
import re
import sqlite3
from importlib.resources import files
from pathlib import Path
from typing import IO, TYPE_CHECKING, Any, NamedTuple, Self, get_args, get_origin
from urllib.parse import urlparse

from dgkit.types import Compression, DatabaseType, FileFormat, Writer

if TYPE_CHECKING:
    import psycopg


def _get_list_element_type(field_type: type) -> type | None:
    """Get the element type of a list type annotation, or None if not a list."""
    origin = get_origin(field_type)
    if origin is list:
        args = get_args(field_type)
        return args[0] if args else None
    return None


def _is_namedtuple(cls: type) -> bool:
    """Check if a class is a NamedTuple."""
    return (
        isinstance(cls, type)
        and issubclass(cls, tuple)
        and hasattr(cls, "_fields")
        and hasattr(cls, "_asdict")
    )


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


# Map table prefixes to their merged SQL file
_TABLE_FILE_MAP = {
    "artist": "artist",
    "label": "label",
    "masterrelease": "masterrelease",
    "release": "release",
}


def _get_sql_file_for_table(table_name: str) -> str:
    """Get the SQL file name that contains a table's definition."""
    # Check for exact match first (main tables)
    if table_name in _TABLE_FILE_MAP:
        return table_name
    # For junction tables, extract prefix (e.g., artist_alias -> artist)
    if "_" in table_name:
        prefix = table_name.split("_")[0]
        if prefix in _TABLE_FILE_MAP:
            return prefix
    return table_name


def _load_sql(database: str, category: str, name: str) -> str | None:
    """Load SQL from package resources.

    For tables, extracts the specific CREATE TABLE statement from merged files.
    """
    sql_file = _get_sql_file_for_table(name)
    try:
        resource = files("dgkit.sql") / database / category / f"{sql_file}.sql"
        content = resource.read_text()
    except FileNotFoundError:
        return None

    # For non-table categories (like indices), return the whole file
    if category != "tables":
        return content

    # Extract the specific CREATE TABLE statement (handles quoted table names)
    pattern = rf'CREATE TABLE "?{re.escape(name)}"?\s*\([^;]+\);'
    match = re.search(pattern, content, re.IGNORECASE | re.DOTALL)
    if match:
        return match.group(0)
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


class JsonWriter:
    """Writer that outputs records as a JSON array."""

    aggregates_inputs = False

    def __init__(self, path: Path, compression: Compression = Compression.none):
        self.path = path
        self.compression = compression
        self._fp: IO | None = None
        self._first = True

    def __enter__(self) -> Self:
        self._fp = open_compressed(self.path, "wt", self.compression)
        self._fp.write("[\n")
        self._first = True
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if self._fp:
            self._fp.write("\n]\n")
            self._fp.close()

    def write(self, record: NamedTuple) -> None:
        if self._fp:
            if not self._first:
                self._fp.write(",\n")
            self._first = False
            self._fp.write(json.dumps(record._asdict()))


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
    bool: "INTEGER",
    bytes: "BLOB",
    float: "REAL",
    int: "INTEGER",
    str: "TEXT",
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
        # Cache of junction table info: {(table, field): (junction_table_name, elem_type)}
        self._junction_tables: dict[tuple[str, str], tuple[str, type]] = {}
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

        # Identify junction table fields (list[int] or list[NamedTuple])
        for field, field_type in annotations.items():
            elem_type = _get_list_element_type(field_type)
            if elem_type is int or _is_namedtuple(elem_type):
                junction_fields.add(field)
                junction_table = f"{table_name}_{_singularize(field)}"
                self._junction_tables[(table_name, field)] = (junction_table, elem_type)

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
            junction_table, elem_type = self._junction_tables[(table_name, field)]
            self._conn.execute(f"DROP TABLE IF EXISTS {junction_table}")

            sql = _load_sql("sqlite", "tables", junction_table)
            if sql:
                self._conn.execute(sql)
            elif elem_type is int:
                # Simple junction table: {table}_id, {field_singular}_id
                fk_col = f"{table_name}_id"
                ref_col = f"{_singularize(field)}_id"
                self._conn.execute(
                    f"CREATE TABLE {junction_table} ("
                    f"{fk_col} INTEGER NOT NULL, "
                    f"{ref_col} INTEGER NOT NULL, "
                    f"PRIMARY KEY ({fk_col}, {ref_col}))"
                )
            elif _is_namedtuple(elem_type):
                # NamedTuple junction table: {table}_id + elem fields
                fk_col = f"{table_name}_id"
                elem_annotations = elem_type.__annotations__
                columns = [f"{fk_col} INTEGER NOT NULL"]
                for elem_field, elem_field_type in elem_annotations.items():
                    sqlite_type = SQLITE_TYPE_MAP.get(elem_field_type, "TEXT")
                    columns.append(f"{elem_field} {sqlite_type}")
                self._conn.execute(
                    f"CREATE TABLE {junction_table} ({', '.join(columns)})"
                )

            self._tables.add(junction_table)
            self._buffers[junction_table] = []

        return table_name

    def _create_indices(self) -> None:
        """Create indices on tables after data insertion."""
        if not self._conn:
            return
        executed_files: set[str] = set()
        for table_name in self._tables:
            sql_file = _get_sql_file_for_table(table_name)
            if sql_file in executed_files:
                continue
            sql = _load_sql("sqlite", "indices", table_name)
            if sql:
                self._conn.execute(sql)
                executed_files.add(sql_file)

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

        # Build main table values (excluding junction fields, serialize lists/tuples as JSON)
        main_values: list[Any] = []
        for field, value in zip(record._fields, record):
            if field in junction_fields:
                continue
            if isinstance(value, (list, tuple)):
                main_values.append(json.dumps(value))
            else:
                main_values.append(value)

        self._buffers[table_name].append(tuple(main_values))
        if len(self._buffers[table_name]) >= self.batch_size:
            self._flush(table_name)

        # Insert junction table entries
        for field in junction_fields:
            junction_table, elem_type = self._junction_tables[(table_name, field)]
            field_idx = record._fields.index(field)
            values = record[field_idx]
            if values:
                for item in values:
                    if elem_type is int:
                        self._buffers[junction_table].append((record_id, item))
                    elif _is_namedtuple(elem_type):
                        self._buffers[junction_table].append((record_id, *item))
                if len(self._buffers[junction_table]) >= self.batch_size:
                    self._flush(junction_table)


POSTGRES_TYPE_MAP: dict[type, str] = {
    bool: "BOOLEAN",
    bytes: "BYTEA",
    float: "DOUBLE PRECISION",
    int: "BIGINT",
    str: "TEXT",
}


class PostgresWriter:
    """Writer that outputs records to a PostgreSQL database."""

    aggregates_inputs = True

    def __init__(self, dsn: str, batch_size: int = 10000, **kwargs: Any):
        self.dsn = dsn
        self.batch_size = batch_size
        self._conn: "psycopg.Connection | None" = None
        self._tables: set[str] = set()
        self._buffers: dict[str, list[tuple]] = {}
        self._junction_tables: dict[tuple[str, str], tuple[str, type]] = {}
        self._junction_fields: dict[str, set[str]] = {}
        self._table_columns: dict[str, list[str]] = {}

    def __enter__(self) -> Self:
        import psycopg

        self._conn = psycopg.connect(self.dsn)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if self._conn:
            self._flush_all()
            if not exc_type:
                self._create_indices()
            self._conn.commit()
            self._conn.close()

    def _ensure_table(self, record: NamedTuple) -> str:
        """Create table for record type if it doesn't exist."""
        table_name = type(record).__name__.lower()
        if table_name in self._tables:
            return table_name

        annotations = type(record).__annotations__
        junction_fields: set[str] = set()

        for field, field_type in annotations.items():
            elem_type = _get_list_element_type(field_type)
            if elem_type is int or _is_namedtuple(elem_type):
                junction_fields.add(field)
                junction_table = f"{table_name}_{_singularize(field)}"
                self._junction_tables[(table_name, field)] = (junction_table, elem_type)

        self._junction_fields[table_name] = junction_fields

        self._conn.execute(f"DROP TABLE IF EXISTS {table_name} CASCADE")

        # Track column names for COPY (excluding junction fields)
        column_names = [f for f in record._fields if f not in junction_fields]
        self._table_columns[table_name] = column_names

        sql = _load_sql("postgresql", "tables", table_name)
        if sql:
            self._conn.execute(sql)
        else:
            columns = []
            for i, field in enumerate(record._fields):
                if field in junction_fields:
                    continue
                field_type = annotations.get(field, str)
                if hasattr(field_type, "__origin__"):
                    args = getattr(field_type, "__args__", ())
                    field_type = next((t for t in args if t is not type(None)), str)
                pg_type = POSTGRES_TYPE_MAP.get(field_type, "TEXT")
                if i == 0 and pg_type == "BIGINT":
                    columns.append(f"{field} BIGINT PRIMARY KEY")
                else:
                    columns.append(f"{field} {pg_type}")
            self._conn.execute(f"CREATE TABLE {table_name} ({', '.join(columns)})")

        self._tables.add(table_name)
        self._buffers[table_name] = []

        for field in junction_fields:
            junction_table, elem_type = self._junction_tables[(table_name, field)]
            self._conn.execute(f"DROP TABLE IF EXISTS {junction_table} CASCADE")

            fk_col = f"{table_name}_id"
            if elem_type is int:
                ref_col = f"{_singularize(field)}_id"
                junction_columns = [fk_col, ref_col]
            elif _is_namedtuple(elem_type):
                junction_columns = [fk_col] + list(elem_type._fields)
            else:
                junction_columns = [fk_col]
            self._table_columns[junction_table] = junction_columns

            sql = _load_sql("postgresql", "tables", junction_table)
            if sql:
                self._conn.execute(sql)
            elif elem_type is int:
                ref_col = f"{_singularize(field)}_id"
                self._conn.execute(
                    f"CREATE TABLE {junction_table} ("
                    f"{fk_col} BIGINT NOT NULL, "
                    f"{ref_col} BIGINT NOT NULL, "
                    f"PRIMARY KEY ({fk_col}, {ref_col}))"
                )
            elif _is_namedtuple(elem_type):
                elem_annotations = elem_type.__annotations__
                columns = [f"{fk_col} BIGINT NOT NULL"]
                for elem_field, elem_field_type in elem_annotations.items():
                    pg_type = POSTGRES_TYPE_MAP.get(elem_field_type, "TEXT")
                    columns.append(f"{elem_field} {pg_type}")
                self._conn.execute(
                    f"CREATE TABLE {junction_table} ({', '.join(columns)})"
                )

            self._tables.add(junction_table)
            self._buffers[junction_table] = []

        return table_name

    def _create_indices(self) -> None:
        """Create indices on tables after data insertion."""
        if not self._conn:
            return
        executed_files: set[str] = set()
        for table_name in self._tables:
            sql_file = _get_sql_file_for_table(table_name)
            if sql_file in executed_files:
                continue
            sql = _load_sql("postgresql", "indices", table_name)
            if sql:
                self._conn.execute(sql)
                executed_files.add(sql_file)

    def _flush(self, table_name: str) -> None:
        """Flush buffered records to the database using COPY."""
        if not self._conn or table_name not in self._buffers:
            return
        buffer = self._buffers[table_name]
        if not buffer:
            return

        columns = self._table_columns.get(table_name)
        if columns:
            col_list = ", ".join(columns)
            with self._conn.cursor().copy(
                f"COPY {table_name} ({col_list}) FROM STDIN"
            ) as copy:
                for row in buffer:
                    copy.write_row(row)
        else:
            with self._conn.cursor().copy(f"COPY {table_name} FROM STDIN") as copy:
                for row in buffer:
                    copy.write_row(row)
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
        record_id = record[0]

        main_values: list[Any] = []
        for field, value in zip(record._fields, record):
            if field in junction_fields:
                continue
            if isinstance(value, (list, tuple)):
                main_values.append(json.dumps(value))
            else:
                main_values.append(value)

        self._buffers[table_name].append(tuple(main_values))
        if len(self._buffers[table_name]) >= self.batch_size:
            self._flush(table_name)

        for field in junction_fields:
            junction_table, elem_type = self._junction_tables[(table_name, field)]
            field_idx = record._fields.index(field)
            values = record[field_idx]
            if values:
                for item in values:
                    if elem_type is int:
                        self._buffers[junction_table].append((record_id, item))
                    elif _is_namedtuple(elem_type):
                        self._buffers[junction_table].append((record_id, *item))
                if len(self._buffers[junction_table]) >= self.batch_size:
                    self._flush(junction_table)


FILE_WRITERS: dict[FileFormat, type[Writer]] = {
    FileFormat.blackhole: BlackholeWriter,
    FileFormat.console: ConsoleWriter,
    FileFormat.json: JsonWriter,
    FileFormat.jsonl: JsonlWriter,
}


DATABASE_WRITERS: dict[DatabaseType, type[Writer]] = {
    DatabaseType.postgresql: PostgresWriter,
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
