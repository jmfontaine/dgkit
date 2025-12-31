import gzip
from pathlib import Path

import pytest
from typer.testing import CliRunner

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def cli_runner():
    """Typer CLI test runner."""
    return CliRunner()


@pytest.fixture
def fixtures_dir():
    """Path to test fixtures directory."""
    return FIXTURES_DIR


@pytest.fixture
def sample_artists_xml():
    """Sample artists XML content."""
    return (FIXTURES_DIR / "sample_artists.xml").read_text()


@pytest.fixture
def sample_labels_xml():
    """Sample labels XML content."""
    return (FIXTURES_DIR / "sample_labels.xml").read_text()


@pytest.fixture
def tmp_gzip_file(tmp_path):
    """Factory for creating temporary gzipped XML files."""
    def _create(name: str, content: str) -> Path:
        path = tmp_path / name
        with gzip.open(path, "wt") as f:
            f.write(content)
        return path
    return _create
