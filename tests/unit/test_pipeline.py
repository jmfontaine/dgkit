import io
from pathlib import Path

import pytest

from dgkit.pipeline import (
    build_database_path,
    build_output_path,
    find_elements,
)
from dgkit.types import Compression, FileFormat


class TestFindElements:
    def test_find_all_elements(self):
        """Find all matching elements without limit."""
        xml = b"""<?xml version="1.0"?>
        <root>
            <item><id>1</id></item>
            <item><id>2</id></item>
            <item><id>3</id></item>
        </root>
        """
        stream = io.BytesIO(xml)
        elements = list(find_elements(stream, "item"))
        assert len(elements) == 3

    def test_find_elements_with_limit(self):
        """Limit number of elements returned."""
        xml = b"""<?xml version="1.0"?>
        <root>
            <item><id>1</id></item>
            <item><id>2</id></item>
            <item><id>3</id></item>
            <item><id>4</id></item>
            <item><id>5</id></item>
        </root>
        """
        stream = io.BytesIO(xml)
        elements = list(find_elements(stream, "item", limit=3))
        assert len(elements) == 3

    def test_find_elements_limit_exceeds_available(self):
        """Limit greater than available elements returns all."""
        xml = b"""<?xml version="1.0"?>
        <root>
            <item><id>1</id></item>
            <item><id>2</id></item>
        </root>
        """
        stream = io.BytesIO(xml)
        elements = list(find_elements(stream, "item", limit=10))
        assert len(elements) == 2

    def test_find_no_matching_elements(self):
        """No matching elements returns empty."""
        xml = b"""<?xml version="1.0"?>
        <root>
            <other><id>1</id></other>
        </root>
        """
        stream = io.BytesIO(xml)
        elements = list(find_elements(stream, "item"))
        assert len(elements) == 0


class TestBuildOutputPath:
    def test_basic_output_path(self, tmp_path):
        """Build output path from input path."""
        input_path = Path("discogs_20250101_artists.xml.gz")
        output = build_output_path(input_path, FileFormat.jsonl, tmp_path)
        assert output == tmp_path / "discogs_20250101_artists.jsonl"

    def test_output_path_with_compression(self, tmp_path):
        """Build output path with compression extension."""
        input_path = Path("discogs_20250101_artists.xml.gz")
        output = build_output_path(
            input_path, FileFormat.jsonl, tmp_path, Compression.gzip
        )
        assert output == tmp_path / "discogs_20250101_artists.jsonl.gz"

    def test_output_path_bz2_compression(self, tmp_path):
        """Build output path with bz2 compression."""
        input_path = Path("discogs_20250101_labels.xml.gz")
        output = build_output_path(
            input_path, FileFormat.json, tmp_path, Compression.bz2
        )
        assert output == tmp_path / "discogs_20250101_labels.json.bz2"


class TestBuildDatabasePath:
    def test_uses_stem_from_first_file(self, tmp_path):
        """Use stem from first file for database name."""
        paths = [Path("discogs_20250101_artists.xml.gz")]
        result = build_database_path(paths, tmp_path)
        assert result == tmp_path / "discogs_20250101_artists.db"

    def test_uses_first_file_stem(self, tmp_path):
        """Use first file's stem when multiple provided."""
        paths = [
            Path("releases.xml.gz"),
            Path("discogs_20250201_labels.xml.gz"),
        ]
        result = build_database_path(paths, tmp_path)
        assert result == tmp_path / "releases.db"

    def test_handles_simple_filename(self, tmp_path):
        """Accept simple filenames without date pattern."""
        paths = [Path("my_releases.xml.gz")]
        result = build_database_path(paths, tmp_path)
        assert result == tmp_path / "my_releases.db"

    def test_empty_paths_raises(self, tmp_path):
        """Raise ValueError for empty path list."""
        with pytest.raises(ValueError, match="No input files provided"):
            build_database_path([], tmp_path)
