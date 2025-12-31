import psycopg
import pytest
from testcontainers.postgres import PostgresContainer

from dgkit.cli import app
from dgkit.models import Artist, ArtistRef
from dgkit.writers import PostgresWriter


@pytest.fixture(scope="module")
def postgres_container():
    """Start a PostgreSQL container for the test module."""
    with PostgresContainer("postgres:16-alpine") as postgres:
        yield postgres


@pytest.fixture
def postgres_dsn(postgres_container):
    """Get connection string for the PostgreSQL container."""
    return postgres_container.get_connection_url().replace("+psycopg2", "")


@pytest.fixture
def make_artist():
    """Factory for creating Artist instances with defaults."""

    def _make(
        id: int = 1,
        name: str | None = "Test",
        real_name: str | None = None,
        profile: str | None = None,
        data_quality=None,
        **kwargs,
    ) -> Artist:
        return Artist(
            id=id,
            data_quality=data_quality,
            name=name,
            profile=profile,
            real_name=real_name,
            **kwargs,
        )

    return _make


class TestPostgresWriter:
    def test_write_single_record(self, postgres_dsn, make_artist):
        artist = make_artist(
            id=1,
            name="Test Artist",
            profile="Test profile",
            real_name="Real Name",
            urls=["https://example.com"],
            aliases=[ArtistRef(100, "Alias One"), ArtistRef(200, "Alias Two")],
        )

        with PostgresWriter(dsn=postgres_dsn) as writer:
            writer.write(artist)

        with psycopg.connect(postgres_dsn) as conn:
            cursor = conn.execute("SELECT id, name, profile, real_name FROM artist")
            row = cursor.fetchone()
            assert row == (1, "Test Artist", "Test profile", "Real Name")

            cursor = conn.execute(
                "SELECT artist_id, id, name FROM artist_alias ORDER BY id"
            )
            aliases = cursor.fetchall()
            assert aliases == [(1, 100, "Alias One"), (1, 200, "Alias Two")]

    def test_write_multiple_records(self, postgres_dsn, make_artist):
        artists = [
            make_artist(id=1, name="Artist One"),
            make_artist(id=2, name="Artist Two", profile="Profile", real_name="Name"),
            make_artist(id=3, name="Artist Three"),
        ]

        with PostgresWriter(dsn=postgres_dsn) as writer:
            for artist in artists:
                writer.write(artist)

        with psycopg.connect(postgres_dsn) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM artist")
            row = cursor.fetchone()
            assert row is not None and row[0] == 3

    def test_batch_flush(self, postgres_dsn, make_artist):
        """Test that records are flushed in batches."""
        with PostgresWriter(dsn=postgres_dsn, batch_size=10) as writer:
            for i in range(25):
                writer.write(make_artist(id=i, name=f"Artist {i}"))

        with psycopg.connect(postgres_dsn) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM artist")
            row = cursor.fetchone()
            assert row is not None and row[0] == 25


class TestLoadCommandPostgres:
    def test_load_to_postgresql(
        self, cli_runner, tmp_gzip_file, sample_artists_xml, postgres_dsn
    ):
        gzip_path = tmp_gzip_file("discogs_20251201_artists.xml.gz", sample_artists_xml)
        result = cli_runner.invoke(
            app, ["load", str(gzip_path), "-d", "postgresql", "--dsn", postgres_dsn]
        )
        assert result.exit_code == 0

        with psycopg.connect(postgres_dsn) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM artist")
            row = cursor.fetchone()
            assert row is not None and row[0] == 2

    def test_load_with_filter(
        self, cli_runner, tmp_gzip_file, sample_artists_xml, postgres_dsn
    ):
        gzip_path = tmp_gzip_file("discogs_20251201_artists.xml.gz", sample_artists_xml)
        result = cli_runner.invoke(
            app,
            [
                "load",
                str(gzip_path),
                "-d",
                "postgresql",
                "--dsn",
                postgres_dsn,
                "--drop-if",
                "id == 1",
            ],
        )
        assert result.exit_code == 0

        with psycopg.connect(postgres_dsn) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM artist")
            row = cursor.fetchone()
            assert row is not None and row[0] == 1
