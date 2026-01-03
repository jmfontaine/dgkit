import json
from dataclasses import dataclass

import pytest

from dgkit.types import Compression, FileFormat
from dgkit.writers import (
    BlackholeWriter,
    ConsoleWriter,
    JsonWriter,
    JsonlWriter,
    get_database_writer,
    get_file_writer,
    open_compressed,
    parse_sqlite_dsn,
)


@dataclass
class SimpleRecord:
    id: int
    name: str


class TestParseSqliteDsn:
    def test_plain_path(self):
        assert parse_sqlite_dsn("test.db") == "test.db"
        assert parse_sqlite_dsn("/absolute/path.db") == "/absolute/path.db"
        assert parse_sqlite_dsn("./relative/path.db") == "./relative/path.db"

    def test_sqlite_relative_path(self):
        assert parse_sqlite_dsn("sqlite:///./test.db") == "./test.db"
        assert parse_sqlite_dsn("sqlite:///./data/test.db") == "./data/test.db"

    def test_sqlite_absolute_path(self):
        assert parse_sqlite_dsn("sqlite:////tmp/test.db") == "/tmp/test.db"
        assert (
            parse_sqlite_dsn("sqlite:////absolute/path/test.db")
            == "/absolute/path/test.db"
        )

    def test_sqlite_memory(self):
        assert parse_sqlite_dsn("sqlite:///:memory:") == ":memory:"

    def test_unsupported_scheme(self):
        with pytest.raises(ValueError, match="Unsupported scheme"):
            parse_sqlite_dsn("postgresql://localhost/db")


class TestBlackholeWriter:
    def test_writes_nothing(self):
        """BlackholeWriter accepts writes without storing."""
        with BlackholeWriter() as writer:
            writer.write(SimpleRecord(1, "Test"))
            writer.write(SimpleRecord(2, "Another"))
        # No assertion needed - just verifying no error

    def test_aggregates_inputs(self):
        assert BlackholeWriter.aggregates_inputs is True


class TestConsoleWriter:
    def test_writes_to_console(self, capsys):
        """ConsoleWriter prints records."""
        with ConsoleWriter() as writer:
            writer.write(SimpleRecord(1, "Test"))
        captured = capsys.readouterr()
        assert "SimpleRecord" in captured.out
        assert "id=1" in captured.out

    def test_aggregates_inputs(self):
        assert ConsoleWriter.aggregates_inputs is True


class TestJsonWriter:
    def test_writes_json_array(self, tmp_path):
        """JsonWriter creates valid JSON array."""
        output = tmp_path / "test.json"
        with JsonWriter(output) as writer:
            writer.write(SimpleRecord(1, "First"))
            writer.write(SimpleRecord(2, "Second"))

        content = output.read_text()
        data = json.loads(content)
        assert data == [
            {"id": 1, "name": "First"},
            {"id": 2, "name": "Second"},
        ]

    def test_writes_single_record(self, tmp_path):
        """JsonWriter handles single record."""
        output = tmp_path / "test.json"
        with JsonWriter(output) as writer:
            writer.write(SimpleRecord(1, "Only"))

        data = json.loads(output.read_text())
        assert data == [{"id": 1, "name": "Only"}]

    def test_writes_gzip_compressed(self, tmp_path):
        """JsonWriter with gzip compression."""
        import gzip

        output = tmp_path / "test.json.gz"
        with JsonWriter(output, compression=Compression.gzip) as writer:
            writer.write(SimpleRecord(1, "Compressed"))

        with gzip.open(output, "rt") as f:
            data = json.load(f)
        assert data == [{"id": 1, "name": "Compressed"}]

    def test_writes_bz2_compressed(self, tmp_path):
        """JsonWriter with bz2 compression."""
        import bz2

        output = tmp_path / "test.json.bz2"
        with JsonWriter(output, compression=Compression.bz2) as writer:
            writer.write(SimpleRecord(1, "Bz2Compressed"))

        with bz2.open(output, "rt") as f:
            data = json.load(f)
        assert data == [{"id": 1, "name": "Bz2Compressed"}]

    def test_aggregates_inputs_false(self):
        assert JsonWriter.aggregates_inputs is False


class TestJsonlWriter:
    def test_writes_jsonl(self, tmp_path):
        """JsonlWriter creates valid JSONL."""
        output = tmp_path / "test.jsonl"
        with JsonlWriter(output) as writer:
            writer.write(SimpleRecord(1, "First"))
            writer.write(SimpleRecord(2, "Second"))

        lines = output.read_text().strip().split("\n")
        assert len(lines) == 2
        assert json.loads(lines[0]) == {"id": 1, "name": "First"}
        assert json.loads(lines[1]) == {"id": 2, "name": "Second"}

    def test_writes_gzip_compressed(self, tmp_path):
        """JsonlWriter with gzip compression."""
        import gzip

        output = tmp_path / "test.jsonl.gz"
        with JsonlWriter(output, compression=Compression.gzip) as writer:
            writer.write(SimpleRecord(1, "Compressed"))

        with gzip.open(output, "rt") as f:
            lines = f.read().strip().split("\n")
        assert len(lines) == 1
        assert json.loads(lines[0]) == {"id": 1, "name": "Compressed"}

    def test_aggregates_inputs_false(self):
        assert JsonlWriter.aggregates_inputs is False


class TestOpenCompressed:
    def test_gzip(self, tmp_path):
        """open_compressed with gzip."""
        import gzip

        path = tmp_path / "test.gz"
        with open_compressed(path, "wt", Compression.gzip) as f:
            f.write("test content")

        with gzip.open(path, "rt") as f:
            assert f.read() == "test content"

    def test_bz2(self, tmp_path):
        """open_compressed with bz2."""
        import bz2

        path = tmp_path / "test.bz2"
        with open_compressed(path, "wt", Compression.bz2) as f:
            f.write("test content")

        with bz2.open(path, "rt") as f:
            assert f.read() == "test content"

    def test_none(self, tmp_path):
        """open_compressed with no compression."""
        path = tmp_path / "test.txt"
        with open_compressed(path, "w", Compression.none) as f:
            f.write("test content")

        assert path.read_text() == "test content"


class TestGetFileWriter:
    def test_get_blackhole_writer(self):
        writer = get_file_writer(FileFormat.blackhole)
        assert isinstance(writer, BlackholeWriter)

    def test_get_console_writer(self):
        writer = get_file_writer(FileFormat.console)
        assert isinstance(writer, ConsoleWriter)

    def test_get_json_writer(self, tmp_path):
        path = tmp_path / "test.json"
        writer = get_file_writer(FileFormat.json, path=path)
        assert isinstance(writer, JsonWriter)

    def test_get_jsonl_writer(self, tmp_path):
        path = tmp_path / "test.jsonl"
        writer = get_file_writer(FileFormat.jsonl, path=path)
        assert isinstance(writer, JsonlWriter)


class TestGetDatabaseWriter:
    def test_unsupported_database_raises(self):
        """Unsupported database type raises NotImplementedError."""
        from typing import cast

        from dgkit.types import DatabaseType

        # Create a mock unsupported database type and cast to bypass type check
        class FakeDbType:
            value = "fake"

        with pytest.raises(
            NotImplementedError, match="Writer for fake not implemented"
        ):
            get_database_writer(
                cast(DatabaseType, FakeDbType()), dsn="fake://localhost"
            )
