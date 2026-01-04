import bz2
import gzip
import json
import re
import sqlite3
import types

from dataclasses import asdict, fields, is_dataclass
from importlib.resources import files
from pathlib import Path
from typing import (
    IO,
    TYPE_CHECKING,
    Any,
    LiteralString,
    Protocol,
    Self,
    cast,
    get_args,
    get_origin,
)
from urllib.parse import urlparse

from dgkit.types import Compression, DatabaseType, FileFormat, Writer

if TYPE_CHECKING:
    import psycopg

from psycopg import sql as pgsql


def _get_list_element_type(field_type: type) -> type | None:
    """Get the element type of a list type annotation, or None if not a list."""
    origin = get_origin(field_type)
    if origin is list:
        args = get_args(field_type)
        return args[0] if args else None
    return None


class _DataclassType(Protocol):
    """Protocol for dataclass class types (not instances)."""

    __dataclass_fields__: dict[str, Any]
    __annotations__: dict[str, type]


def _get_field_names(record: Any) -> list[str]:
    """Get field names from a dataclass instance or type."""
    return [f.name for f in fields(record)]


def _get_field_value(record: Any, field_name: str) -> Any:
    """Get field value from a dataclass instance."""
    return getattr(record, field_name)


def _get_type_field_names(cls: type) -> list[str]:
    """Get field names from a dataclass type."""
    return [f.name for f in fields(cls)]


def _singularize(name: str) -> str:
    """Simple singularization: remove trailing 's' or 'es'."""
    if name.endswith("ies"):
        return name[:-3] + "y"
    if name.endswith("es"):
        return name[:-2]
    if name.endswith("s"):
        return name[:-1]
    return name


def _dataclass_to_row(obj: Any, serialize_lists: bool = True) -> tuple:
    """Convert a dataclass to a tuple.

    Args:
        obj: Dataclass instance to convert.
        serialize_lists: If True, serialize lists as JSON strings (for SQLite).
            If False, pass lists directly for PostgreSQL arrays, but still
            serialize lists of dataclasses as JSON.
    """
    values = []
    for f in fields(obj):
        value = getattr(obj, f.name)
        if isinstance(value, (list, tuple)):
            if serialize_lists:
                # SQLite: serialize all lists as JSON
                serializable = [asdict(v) if is_dataclass(v) else v for v in value]
                values.append(json.dumps(serializable))
            elif value and is_dataclass(value[0]) and not isinstance(value[0], type):
                # PostgreSQL: serialize lists of dataclasses as JSONB
                serializable = [asdict(v) for v in value]
                values.append(json.dumps(serializable))
            else:
                # PostgreSQL: pass primitive lists directly for array types
                values.append(list(value))
        else:
            values.append(value)
    return tuple(values)


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


def _extract_columns_from_sql(sql: str) -> set[str]:
    """Extract column names from a CREATE TABLE statement."""
    # Match column definitions between parentheses
    match = re.search(r"\(([^)]+)\)", sql, re.DOTALL)
    if not match:
        return set()
    columns_part = match.group(1)
    columns = set()
    for line in columns_part.split(","):
        line = line.strip()
        if not line:
            continue
        # Extract column name (first word, possibly quoted)
        col_match = re.match(r'"?(\w+)"?', line)
        if col_match:
            columns.add(col_match.group(1))
    return columns


def open_compressed(path: Path, mode: str, compression: Compression) -> IO[Any]:
    """Open a file with optional compression."""
    match compression:
        case Compression.gzip:
            return cast(IO[Any], gzip.open(path, mode))
        case Compression.bz2:
            return cast(IO[Any], bz2.open(path, mode))
        case _:
            return open(path, mode)


class BlackholeWriter:
    """Writer that drops records. This is mostly useful for benchmarking."""

    aggregates_inputs = True

    def __init__(self, **kwargs: Any) -> None:
        pass

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: types.TracebackType | None,
    ) -> None:
        pass

    def write(self, record: Any) -> None:
        pass


class ConsoleWriter:
    """Writer that prints records to the console."""

    aggregates_inputs = True

    def __init__(self, **kwargs: Any) -> None:
        pass

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: types.TracebackType | None,
    ) -> None:
        pass

    def write(self, record: Any) -> None:
        from rich import print

        print(record)


class JsonWriter:
    """Writer that outputs records as a JSON array."""

    aggregates_inputs = False

    def __init__(self, path: Path, compression: Compression = Compression.none) -> None:
        self.path = path
        self.compression = compression
        self._fp: IO | None = None
        self._first = True

    def __enter__(self) -> Self:
        self._fp = open_compressed(self.path, "wt", self.compression)
        self._fp.write("[\n")
        self._first = True
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: types.TracebackType | None,
    ) -> None:
        if self._fp:
            self._fp.write("\n]\n")
            self._fp.close()

    def write(self, record: Any) -> None:
        if self._fp:
            if not self._first:
                self._fp.write(",\n")
            self._first = False
            self._fp.write(json.dumps(asdict(record)))


class JsonlWriter:
    """Writer that outputs records as JSON Lines."""

    aggregates_inputs = False

    def __init__(self, path: Path, compression: Compression = Compression.none) -> None:
        self.path = path
        self.compression = compression
        self._fp: IO | None = None

    def __enter__(self) -> Self:
        self._fp = open_compressed(self.path, "wt", self.compression)
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: types.TracebackType | None,
    ) -> None:
        if self._fp:
            self._fp.close()

    def write(self, record: Any) -> None:
        if self._fp:
            self._fp.write(json.dumps(asdict(record)) + "\n")


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

    def __init__(self, dsn: str, batch_size: int = 10000, **kwargs: Any) -> None:
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

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: types.TracebackType | None,
    ) -> None:
        if self._conn:
            self._flush_all()
            if not exc_type:
                self._create_indices()
                self._conn.execute("ANALYZE")
            self._conn.commit()
            self._conn.close()

    def _ensure_table(self, record: Any) -> str:
        """Create table for record type if it doesn't exist."""
        table_name = type(record).__name__.lower()
        if table_name in self._tables:
            return table_name

        annotations = type(record).__annotations__
        junction_fields: set[str] = set()

        assert self._conn is not None  # Guaranteed after __enter__
        # Drop and recreate main table
        self._conn.execute(f"DROP TABLE IF EXISTS {table_name}")

        # Try to load schema from SQL file
        sql = _load_sql("sqlite", "tables", table_name)
        if sql:
            self._conn.execute(sql)
            # Extract columns from SQL to determine which fields are junction tables
            schema_columns = _extract_columns_from_sql(sql)
        else:
            schema_columns = set()

        # Identify junction table fields (list[int], list[str], or list[dataclass])
        # A field is a junction field if it's a list type AND not in the SQL schema
        for field, field_type in annotations.items():
            elem_type = _get_list_element_type(field_type)
            if elem_type is not None and (
                elem_type is int or elem_type is str or is_dataclass(elem_type)
            ):
                # Only treat as junction if field is not in main table schema
                if not schema_columns or field not in schema_columns:
                    junction_fields.add(field)
                    junction_table = f"{table_name}_{_singularize(field)}"
                    self._junction_tables[(table_name, field)] = (
                        junction_table,
                        elem_type,
                    )

        self._junction_fields[table_name] = junction_fields

        if not sql:
            # Fall back to dynamic schema generation (excluding junction fields)
            field_names = _get_field_names(record)
            columns = []
            for i, field_name in enumerate(field_names):
                if field_name in junction_fields:
                    continue
                field_type = annotations.get(field_name, str)
                if hasattr(field_type, "__origin__"):
                    args = getattr(field_type, "__args__", ())
                    field_type = next((t for t in args if t is not type(None)), str)
                sqlite_type = SQLITE_TYPE_MAP.get(field_type, "TEXT")
                if i == 0 and sqlite_type == "INTEGER":
                    columns.append(f"{field_name} INTEGER PRIMARY KEY")
                else:
                    columns.append(f"{field_name} {sqlite_type}")
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
            elif elem_type is str:
                # String junction table: {table}_id, {field_singular}
                fk_col = f"{table_name}_id"
                val_col = _singularize(field)
                self._conn.execute(
                    f"CREATE TABLE {junction_table} ("
                    f"{fk_col} INTEGER NOT NULL, "
                    f"{val_col} TEXT NOT NULL)"
                )
            elif is_dataclass(elem_type):
                # Dataclass junction table: {table}_id + elem fields
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

    def write(self, record: Any) -> None:
        if not self._conn:
            return
        table_name = self._ensure_table(record)
        junction_fields = self._junction_fields.get(table_name, set())
        field_names = _get_field_names(record)
        record_id = _get_field_value(
            record, field_names[0]
        )  # Assume first field is the ID

        # Build main table values (excluding junction fields, serialize lists/tuples as JSON)
        main_values: list[Any] = []
        for field_name in field_names:
            if field_name in junction_fields:
                continue
            value = _get_field_value(record, field_name)
            if isinstance(value, (list, tuple)):
                main_values.append(json.dumps(value))
            elif is_dataclass(value) and not isinstance(value, type):
                main_values.append(json.dumps(asdict(value)))
            else:
                main_values.append(value)

        self._buffers[table_name].append(tuple(main_values))
        if len(self._buffers[table_name]) >= self.batch_size:
            self._flush(table_name)

        # Insert junction table entries
        for field in junction_fields:
            junction_table, elem_type = self._junction_tables[(table_name, field)]
            values = _get_field_value(record, field)
            if values:
                for item in values:
                    if elem_type is int or elem_type is str:
                        self._buffers[junction_table].append((record_id, item))
                    elif is_dataclass(elem_type):
                        self._buffers[junction_table].append(
                            (record_id, *_dataclass_to_row(item))
                        )
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

    def __init__(
        self,
        dsn: str,
        batch_size: int = 10000,
        commit_interval: int | None = None,
        verbose: bool = False,
        **kwargs: Any,
    ) -> None:
        self.dsn = dsn
        self.batch_size = batch_size
        self.commit_interval = commit_interval
        self.verbose = verbose
        self._conn: "psycopg.Connection | None" = None
        self._tables: set[str] = set()
        self._buffers: dict[str, list[tuple]] = {}
        self._junction_tables: dict[tuple[str, str], tuple[str, type]] = {}
        self._junction_fields: dict[str, set[str]] = {}
        self._table_columns: dict[str, list[str]] = {}
        self._last_error: BaseException | None = None
        self._records_since_commit: int = 0

    def _log(self, message: str) -> None:
        """Log a message if verbose mode is enabled."""
        if self.verbose:
            import sys

            print(f"[PostgresWriter] {message}", file=sys.stderr)

    def __enter__(self) -> Self:
        import psycopg

        self._conn = psycopg.connect(self.dsn)
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: types.TracebackType | None,
    ) -> None:
        if self._conn:
            self._flush_all()
            if not exc_type:
                self._create_indices()
            self._conn.commit()
            self._conn.close()

    def _ensure_table(self, record: Any) -> str:
        """Create table for record type if it doesn't exist."""
        assert self._conn is not None, "Connection must exist in _ensure_table"
        conn = self._conn

        table_name = type(record).__name__.lower()
        if table_name in self._tables:
            return table_name

        annotations = type(record).__annotations__
        junction_fields: set[str] = set()

        try:
            conn.execute(
                pgsql.SQL("DROP TABLE IF EXISTS {} CASCADE").format(
                    pgsql.Identifier(table_name)
                )
            )
        except Exception as e:
            self._last_error = e
            self._log(f"Error dropping table {table_name}: {e}")
            conn.rollback()
            raise

        # Try to load schema from SQL file
        schema_sql = _load_sql("postgresql", "tables", table_name)
        if schema_sql:
            try:
                # SQL loaded from package resources is trusted
                conn.execute(pgsql.SQL(cast(LiteralString, schema_sql)))
            except Exception as e:
                self._last_error = e
                self._log(f"Error creating table {table_name}: {e}")
                self._log(f"  SQL: {schema_sql[:200]}...")
                conn.rollback()
                raise
            # Extract columns from SQL to determine which fields are junction tables
            schema_columns = _extract_columns_from_sql(schema_sql)
        else:
            schema_columns = set()

        # Identify junction table fields (list[int], list[str], or list[dataclass])
        # A field is a junction field if it's a list type AND not in the SQL schema
        for field, field_type in annotations.items():
            elem_type = _get_list_element_type(field_type)
            if elem_type is not None and (
                elem_type is int or elem_type is str or is_dataclass(elem_type)
            ):
                # Only treat as junction if field is not in main table schema
                if not schema_columns or field not in schema_columns:
                    junction_fields.add(field)
                    junction_table = f"{table_name}_{_singularize(field)}"
                    self._junction_tables[(table_name, field)] = (
                        junction_table,
                        elem_type,
                    )

        self._junction_fields[table_name] = junction_fields

        # Track column names for COPY (excluding junction fields)
        all_field_names = _get_field_names(record)
        column_names = [f for f in all_field_names if f not in junction_fields]
        self._table_columns[table_name] = column_names

        if not schema_sql:
            # Fall back to dynamic schema generation (excluding junction fields)
            col_defs: list[pgsql.Composable] = []
            for i, field_name in enumerate(all_field_names):
                if field_name in junction_fields:
                    continue
                field_type = annotations.get(field_name, str)
                if hasattr(field_type, "__origin__"):
                    args = getattr(field_type, "__args__", ())
                    field_type = next((t for t in args if t is not type(None)), str)
                pg_type = POSTGRES_TYPE_MAP.get(field_type, "TEXT")
                if i == 0 and pg_type == "BIGINT":
                    col_defs.append(
                        pgsql.SQL("{} BIGINT PRIMARY KEY").format(
                            pgsql.Identifier(field_name)
                        )
                    )
                else:
                    col_defs.append(
                        pgsql.SQL("{} ").format(pgsql.Identifier(field_name))
                        + pgsql.SQL(cast(LiteralString, pg_type))
                    )
            try:
                conn.execute(
                    pgsql.SQL("CREATE TABLE {} ({})").format(
                        pgsql.Identifier(table_name), pgsql.SQL(", ").join(col_defs)
                    )
                )
            except Exception as e:
                self._last_error = e
                self._log(f"Error creating table {table_name} (dynamic schema): {e}")
                conn.rollback()
                raise

        self._tables.add(table_name)
        self._buffers[table_name] = []

        for field in junction_fields:
            junction_table, elem_type = self._junction_tables[(table_name, field)]
            try:
                conn.execute(
                    pgsql.SQL("DROP TABLE IF EXISTS {} CASCADE").format(
                        pgsql.Identifier(junction_table)
                    )
                )

                fk_col = f"{table_name}_id"
                if elem_type is int:
                    ref_col = f"{_singularize(field)}_id"
                    junction_columns = [fk_col, ref_col]
                elif elem_type is str:
                    val_col = _singularize(field)
                    junction_columns = [fk_col, val_col]
                elif is_dataclass(elem_type):
                    junction_columns = [fk_col] + _get_type_field_names(elem_type)
                else:
                    junction_columns = [fk_col]
                self._table_columns[junction_table] = junction_columns

                schema_sql = _load_sql("postgresql", "tables", junction_table)
                if schema_sql:
                    # SQL loaded from package resources is trusted
                    conn.execute(pgsql.SQL(cast(LiteralString, schema_sql)))
                elif elem_type is int:
                    ref_col = f"{_singularize(field)}_id"
                    conn.execute(
                        pgsql.SQL(
                            "CREATE TABLE {} ("
                            "{} BIGINT NOT NULL, "
                            "{} BIGINT NOT NULL, "
                            "PRIMARY KEY ({}, {}))"
                        ).format(
                            pgsql.Identifier(junction_table),
                            pgsql.Identifier(fk_col),
                            pgsql.Identifier(ref_col),
                            pgsql.Identifier(fk_col),
                            pgsql.Identifier(ref_col),
                        )
                    )
                elif elem_type is str:
                    val_col = _singularize(field)
                    conn.execute(
                        pgsql.SQL(
                            "CREATE TABLE {} ({} BIGINT NOT NULL, {} TEXT NOT NULL)"
                        ).format(
                            pgsql.Identifier(junction_table),
                            pgsql.Identifier(fk_col),
                            pgsql.Identifier(val_col),
                        )
                    )
                elif is_dataclass(elem_type):
                    col_defs: list[pgsql.Composable] = [
                        pgsql.SQL("{} BIGINT NOT NULL").format(pgsql.Identifier(fk_col))
                    ]
                    for (
                        elem_field,
                        elem_field_type,
                    ) in elem_type.__annotations__.items():
                        pg_type = POSTGRES_TYPE_MAP.get(elem_field_type, "TEXT")
                        col_defs.append(
                            pgsql.SQL("{} ").format(pgsql.Identifier(elem_field))
                            + pgsql.SQL(cast(LiteralString, pg_type))
                        )
                    conn.execute(
                        pgsql.SQL("CREATE TABLE {} ({})").format(
                            pgsql.Identifier(junction_table),
                            pgsql.SQL(", ").join(col_defs),
                        )
                    )
            except Exception as e:
                self._last_error = e
                self._log(f"Error creating junction table {junction_table}: {e}")
                conn.rollback()
                raise

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
            index_sql = _load_sql("postgresql", "indices", table_name)
            if index_sql:
                try:
                    # SQL loaded from package resources is trusted
                    self._conn.execute(pgsql.SQL(cast(LiteralString, index_sql)))
                    executed_files.add(sql_file)
                except Exception as e:
                    self._last_error = e
                    self._log(f"Error creating indices for {table_name}: {e}")
                    self._conn.rollback()
                    raise

    def _flush(self, table_name: str) -> None:
        """Flush buffered records to the database using COPY."""
        if not self._conn or table_name not in self._buffers:
            return
        buffer = self._buffers[table_name]
        if not buffer:
            return

        columns = self._table_columns.get(table_name)
        try:
            if columns:
                col_ids = pgsql.SQL(", ").join(pgsql.Identifier(c) for c in columns)
                query = pgsql.SQL("COPY {} ({}) FROM STDIN").format(
                    pgsql.Identifier(table_name), col_ids
                )
                with self._conn.cursor().copy(query) as copy:
                    for row in buffer:
                        copy.write_row(row)
            else:
                query = pgsql.SQL("COPY {} FROM STDIN").format(
                    pgsql.Identifier(table_name)
                )
                with self._conn.cursor().copy(query) as copy:
                    for row in buffer:
                        copy.write_row(row)
            buffer.clear()
        except Exception as e:
            self._last_error = e
            self._log(f"Error flushing {table_name}: {e}")
            self._log(f"  Buffer had {len(buffer)} rows")
            if buffer and columns:
                self._log(f"  Columns: {columns}")
                self._log(f"  Sample row: {buffer[0]}")
            self._conn.rollback()
            raise

    def _flush_all(self) -> None:
        """Flush all buffered records."""
        for table_name in self._buffers:
            self._flush(table_name)

    def write(self, record: Any) -> None:
        if not self._conn:
            return
        table_name = self._ensure_table(record)
        junction_fields = self._junction_fields.get(table_name, set())
        field_names = _get_field_names(record)
        record_id = _get_field_value(record, field_names[0])

        main_values: list[Any] = []
        for field_name in field_names:
            if field_name in junction_fields:
                continue
            value = _get_field_value(record, field_name)
            if isinstance(value, (list, tuple)):
                # Check if list contains dataclasses -> JSONB, else -> array
                if value and is_dataclass(value[0]) and not isinstance(value[0], type):
                    serializable = [asdict(v) for v in value]
                    main_values.append(json.dumps(serializable))
                else:
                    # Pass list directly for PostgreSQL array types
                    main_values.append(list(value))
            elif is_dataclass(value) and not isinstance(value, type):
                main_values.append(json.dumps(asdict(value)))
            else:
                main_values.append(value)

        self._buffers[table_name].append(tuple(main_values))
        if len(self._buffers[table_name]) >= self.batch_size:
            self._flush(table_name)

        for field in junction_fields:
            junction_table, elem_type = self._junction_tables[(table_name, field)]
            values = _get_field_value(record, field)
            if values:
                for item in values:
                    if elem_type is int or elem_type is str:
                        self._buffers[junction_table].append((record_id, item))
                    elif is_dataclass(elem_type):
                        self._buffers[junction_table].append(
                            (record_id, *_dataclass_to_row(item, serialize_lists=False))
                        )
                if len(self._buffers[junction_table]) >= self.batch_size:
                    self._flush(junction_table)

        # Periodic commits for resilience during long loads
        if self.commit_interval is not None:
            self._records_since_commit += 1
            if self._records_since_commit >= self.commit_interval:
                self._flush_all()
                self._conn.commit()
                self._records_since_commit = 0


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
