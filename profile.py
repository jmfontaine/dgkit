from pathlib import Path

from dgkit.pipeline import convert
from dgkit.types import FileFormat

convert(
    format=FileFormat.blackhole,
    paths=[Path("samples/discogs_20260101_releases_sample_1000000.xml.gz")],
    show_progress=False,
    show_summary=False,
)
