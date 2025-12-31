import sqlite3

from dgkit.cli import app


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

    def test_convert_to_jsonl(self, cli_runner, tmp_gzip_file, sample_artists_xml, tmp_path):
        gzip_path = tmp_gzip_file("discogs_20251201_artists.xml.gz", sample_artists_xml)
        result = cli_runner.invoke(app, [
            "convert", str(gzip_path), "-f", "jsonl", "-o", str(tmp_path)
        ])
        assert result.exit_code == 0
        output_file = tmp_path / "discogs_20251201_artists.jsonl"
        assert output_file.exists()
        content = output_file.read_text()
        assert "Test Artist" in content


class TestLoadCommand:
    def test_load_help(self, cli_runner):
        result = cli_runner.invoke(app, ["load", "--help"])
        assert result.exit_code == 0
        assert "Load data dumps" in result.output

    def test_load_to_sqlite(self, cli_runner, tmp_gzip_file, sample_artists_xml, tmp_path):
        gzip_path = tmp_gzip_file("discogs_20251201_artists.xml.gz", sample_artists_xml)
        db_path = tmp_path / "test.db"
        result = cli_runner.invoke(app, [
            "load", str(gzip_path), "-d", "sqlite", "--dsn", str(db_path)
        ])
        assert result.exit_code == 0
        assert db_path.exists()

        # Verify data
        conn = sqlite3.connect(db_path)
        cursor = conn.execute("SELECT COUNT(*) FROM artist")
        assert cursor.fetchone()[0] == 2
        conn.close()

    def test_load_with_filter(self, cli_runner, tmp_gzip_file, sample_artists_xml, tmp_path):
        gzip_path = tmp_gzip_file("discogs_20251201_artists.xml.gz", sample_artists_xml)
        db_path = tmp_path / "test.db"
        result = cli_runner.invoke(app, [
            "load", str(gzip_path), "-d", "sqlite", "--dsn", str(db_path),
            "--drop-if", "id == 1"
        ])
        assert result.exit_code == 0

        conn = sqlite3.connect(db_path)
        cursor = conn.execute("SELECT COUNT(*) FROM artist")
        assert cursor.fetchone()[0] == 1  # Only artist id=2 remains
        conn.close()
