import psycopg
import pytest
from testcontainers.postgres import PostgresContainer

from dgkit.cli import app
from dgkit.models import Artist
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


class TestPostgresWriter:
    def test_write_single_record(self, postgres_dsn):
        artist = Artist(
            id=1,
            name="Test Artist",
            profile="Test profile",
            real_name="Real Name",
            urls=["https://example.com"],
            aliases=[100, 200],
        )

        with PostgresWriter(dsn=postgres_dsn) as writer:
            writer.write(artist)

        with psycopg.connect(postgres_dsn) as conn:
            cursor = conn.execute("SELECT id, name, profile, real_name FROM artist")
            row = cursor.fetchone()
            assert row == (1, "Test Artist", "Test profile", "Real Name")

            cursor = conn.execute(
                "SELECT artist_id, alias_id FROM artist_alias ORDER BY alias_id"
            )
            aliases = cursor.fetchall()
            assert aliases == [(1, 100), (1, 200)]

    def test_write_multiple_records(self, postgres_dsn):
        artists = [
            Artist(id=1, name="Artist One", profile=None, real_name=None),
            Artist(id=2, name="Artist Two", profile="Profile", real_name="Name"),
            Artist(id=3, name="Artist Three", profile=None, real_name=None),
        ]

        with PostgresWriter(dsn=postgres_dsn) as writer:
            for artist in artists:
                writer.write(artist)

        with psycopg.connect(postgres_dsn) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM artist")
            assert cursor.fetchone()[0] == 3

    def test_batch_flush(self, postgres_dsn):
        """Test that records are flushed in batches."""
        with PostgresWriter(dsn=postgres_dsn, batch_size=10) as writer:
            for i in range(25):
                writer.write(
                    Artist(id=i, name=f"Artist {i}", profile=None, real_name=None)
                )

        with psycopg.connect(postgres_dsn) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM artist")
            assert cursor.fetchone()[0] == 25


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
            assert cursor.fetchone()[0] == 2

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
            assert cursor.fetchone()[0] == 1
