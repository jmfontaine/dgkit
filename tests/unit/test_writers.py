import pytest

from dgkit.writers import parse_sqlite_dsn


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
