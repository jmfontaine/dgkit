import gzip
import sqlite3

import pytest

from dgkit.cli import app


@pytest.fixture
def artists_with_unhandled_xml():
    """Sample artists XML with unhandled fields."""
    return """<?xml version="1.0" encoding="UTF-8"?>
<artists>
    <artist>
        <id>1</id>
        <name>Test Artist</name>
        <realname>Real Name</realname>
        <profile>Test profile.</profile>
        <unknown_field>data</unknown_field>
    </artist>
</artists>"""


class TestConvertCommand:
    def test_convert_help(self, cli_runner):
        result = cli_runner.invoke(app, ["convert", "--help"])
        assert result.exit_code == 0
        assert "Convert data dumps" in result.output

    def test_convert_to_console(self, cli_runner, tmp_gzip_file, sample_artists_xml):
        gzip_path = tmp_gzip_file("discogs_20251201_artists.xml.gz", sample_artists_xml)
        result = cli_runner.invoke(app, ["convert", str(gzip_path), "-f", "console"])
        assert result.exit_code == 0
        assert "Test Artist" in result.output

    def test_convert_to_jsonl(
        self, cli_runner, tmp_gzip_file, sample_artists_xml, tmp_path
    ):
        gzip_path = tmp_gzip_file("discogs_20251201_artists.xml.gz", sample_artists_xml)
        result = cli_runner.invoke(
            app, ["convert", str(gzip_path), "-f", "jsonl", "-o", str(tmp_path)]
        )
        assert result.exit_code == 0
        output_file = tmp_path / "discogs_20251201_artists.jsonl"
        assert output_file.exists()
        content = output_file.read_text()
        assert "Test Artist" in content

    def test_convert_strict_mode_panels(
        self, cli_runner, tmp_gzip_file, artists_with_unhandled_xml
    ):
        """Strict mode displays warnings and summary in Rich panels."""
        gzip_path = tmp_gzip_file(
            "discogs_20251201_artists.xml.gz", artists_with_unhandled_xml
        )
        result = cli_runner.invoke(
            app,
            ["convert", str(gzip_path), "-f", "blackhole", "--strict", "--no-progress"],
        )
        assert result.exit_code == 0
        # Check for panel titles
        assert "Unhandled Data" in result.output
        assert "Summary" in result.output
        # Check for actual warning content
        assert "unknown_field" in result.output


class TestLoadCommand:
    def test_load_help(self, cli_runner):
        result = cli_runner.invoke(app, ["load", "--help"])
        assert result.exit_code == 0
        assert "Load data dumps" in result.output

    def test_load_to_sqlite(
        self, cli_runner, tmp_gzip_file, sample_artists_xml, tmp_path
    ):
        gzip_path = tmp_gzip_file("discogs_20251201_artists.xml.gz", sample_artists_xml)
        db_path = tmp_path / "test.db"
        result = cli_runner.invoke(app, ["load", str(gzip_path), "--dsn", str(db_path)])
        assert result.exit_code == 0
        assert db_path.exists()

        # Verify data
        conn = sqlite3.connect(db_path)
        cursor = conn.execute("SELECT COUNT(*) FROM artist")
        assert cursor.fetchone()[0] == 2
        conn.close()

    def test_load_with_filter(
        self, cli_runner, tmp_gzip_file, sample_artists_xml, tmp_path
    ):
        gzip_path = tmp_gzip_file("discogs_20251201_artists.xml.gz", sample_artists_xml)
        db_path = tmp_path / "test.db"
        result = cli_runner.invoke(
            app,
            [
                "load",
                str(gzip_path),
                "--dsn",
                str(db_path),
                "--drop-if",
                "id == 1",
            ],
        )
        assert result.exit_code == 0

        conn = sqlite3.connect(db_path)
        cursor = conn.execute("SELECT COUNT(*) FROM artist")
        assert cursor.fetchone()[0] == 1  # Only artist id=2 remains
        conn.close()


@pytest.fixture
def artists_10_xml():
    """Sample XML with 10 artists for sampling tests."""
    artists = "\n".join(
        f"""    <artist>
        <id>{i}</id>
        <name>Artist {i}</name>
    </artist>"""
        for i in range(1, 11)
    )
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<artists>
{artists}
</artists>"""


class TestSampleCommand:
    def test_sample_help(self, cli_runner):
        result = cli_runner.invoke(app, ["sample", "--help"])
        assert result.exit_code == 0
        assert "Extract a sample" in result.output

    def test_sample_basic(self, cli_runner, tmp_gzip_file, artists_10_xml, tmp_path):
        """Extract 5 elements from file with 10."""
        gzip_path = tmp_gzip_file("discogs_20251201_artists.xml.gz", artists_10_xml)
        output_path = tmp_path / "sample_output.xml.gz"

        result = cli_runner.invoke(
            app,
            [
                "sample",
                str(gzip_path),
                "-n",
                "5",
                "-o",
                str(output_path),
                "--no-progress",
            ],
        )
        assert result.exit_code == 0
        assert "Written: 5" in result.output
        assert output_path.exists()

        # Verify output is valid gzipped XML with 5 artists
        with gzip.open(output_path, "rt") as f:
            content = f.read()
        assert "<artists>" in content
        assert "</artists>" in content
        assert "Artist 1" in content
        assert "Artist 5" in content
        assert "Artist 6" not in content

    def test_sample_count_exceeds_available(
        self, cli_runner, tmp_gzip_file, artists_10_xml, tmp_path
    ):
        """Request more elements than available extracts all."""
        gzip_path = tmp_gzip_file("discogs_20251201_artists.xml.gz", artists_10_xml)
        output_path = tmp_path / "sample_output.xml.gz"

        result = cli_runner.invoke(
            app,
            [
                "sample",
                str(gzip_path),
                "-n",
                "100",
                "-o",
                str(output_path),
                "--no-progress",
            ],
        )
        assert result.exit_code == 0
        assert "Written: 10" in result.output

    def test_sample_default_output_name(
        self, cli_runner, tmp_gzip_file, artists_10_xml, tmp_path, monkeypatch
    ):
        """Without -o, generates default output name."""
        monkeypatch.chdir(tmp_path)
        gzip_path = tmp_gzip_file("discogs_20251201_artists.xml.gz", artists_10_xml)

        result = cli_runner.invoke(
            app, ["sample", str(gzip_path), "-n", "3", "--no-progress"]
        )
        assert result.exit_code == 0
        expected_name = "discogs_20251201_artists_sample_3.xml.gz"
        assert expected_name in result.output

    def test_sample_file_not_found(self, cli_runner, tmp_path):
        """Error when input file doesn't exist."""
        result = cli_runner.invoke(
            app, ["sample", str(tmp_path / "nonexistent.xml.gz"), "--no-progress"]
        )
        assert result.exit_code != 0
        assert "File not found" in result.output

    def test_sample_output_directory(
        self, cli_runner, tmp_gzip_file, artists_10_xml, tmp_path
    ):
        """When output is a directory, generate filename in that directory."""
        gzip_path = tmp_gzip_file("discogs_20251201_artists.xml.gz", artists_10_xml)
        output_dir = tmp_path / "output_dir"
        output_dir.mkdir()

        result = cli_runner.invoke(
            app,
            [
                "sample",
                str(gzip_path),
                "-n",
                "3",
                "-o",
                str(output_dir),
                "--no-progress",
            ],
        )
        assert result.exit_code == 0
        assert "Written: 3" in result.output
        expected_file = output_dir / "discogs_20251201_artists_sample_3.xml.gz"
        assert expected_file.exists()

    def test_sample_overwrite_prompt(
        self, cli_runner, tmp_gzip_file, artists_10_xml, tmp_path
    ):
        """Prompts before overwriting existing file."""
        gzip_path = tmp_gzip_file("discogs_20251201_artists.xml.gz", artists_10_xml)
        output_path = tmp_path / "sample_output.xml.gz"
        output_path.write_bytes(b"existing content")

        # Without confirmation, aborts
        result = cli_runner.invoke(
            app,
            [
                "sample",
                str(gzip_path),
                "-n",
                "5",
                "-o",
                str(output_path),
                "--no-progress",
            ],
            input="n\n",
        )
        assert result.exit_code == 1  # Aborted

        # With -w flag, overwrites without prompt
        result = cli_runner.invoke(
            app,
            [
                "sample",
                str(gzip_path),
                "-n",
                "5",
                "-o",
                str(output_path),
                "-w",
                "--no-progress",
            ],
        )
        assert result.exit_code == 0
        assert "Written: 5" in result.output
