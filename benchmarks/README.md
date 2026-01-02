# Benchmarks

Compare dgkit performance against alternative Discogs data processing tools.

## Prerequisites

- GNU time for timing and memory measurement
  - macOS: `brew install gnu-time`
  - Linux: `apt install time` (uses `/usr/bin/time`)
- Sample data in `../samples/` (see main README for creating samples)

## Setup

Install alternative tools:

```shell
just bench-setup
# or: python benchmarks/setup.py
```

This clones and builds:

| Tool | Language | Repository |
|------|----------|------------|
| discogs-xml2db-python | Python | [philipmat/discogs-xml2db](https://github.com/philipmat/discogs-xml2db) |
| discogs-xml2db-csharp | C# | [philipmat/discogs-xml2db](https://github.com/philipmat/discogs-xml2db) |
| dgtools | Go | [marcw/dgtools](https://github.com/marcw/dgtools) |
| discogs-load | Rust | [DylanBartels/discogs-load](https://github.com/DylanBartels/discogs-load) |
| discogs-batch | Java | [echovisionlab/discogs-batch](https://github.com/echovisionlab/discogs-batch) |

## Running Benchmarks

```shell
# All tools
just bench -i samples/discogs_20260101_releases_sample_1000000.xml.gz

# Single tool
just bench -i samples/discogs_20260101_releases_sample_1000000.xml.gz dgkit

# Multiple tools
just bench -i samples/discogs_20260101_releases_sample_1000000.xml.gz dgkit xml2db-csharp
```

Available tools: `dgkit`, `xml2db-python`, `xml2db-csharp`

The script measures (single run per tool via gtime):

- **Wall clock time**
- **User/system CPU time**
- **Peak memory (RSS)**

## Profiling dgkit

Profile parsing performance:

```python
import cProfile
import pstats
from pathlib import Path
from dgkit.pipeline import convert
from dgkit.types import FileFormat

with cProfile.Profile() as pr:
    convert(
        paths=[Path("samples/discogs_20260101_releases_sample_1000000.xml.gz")],
        format=FileFormat.blackhole,
        show_progress=False,
        show_summary=False,
    )

stats = pstats.Stats(pr)
stats.sort_stats("cumulative")
stats.print_stats(20)
```

## Notes

- Results are machine-dependent; use relative comparisons (ratios) for cross-machine analysis
- The `alternatives/` and `results/` directories are gitignored
- Run benchmarks on a quiet system for consistent results
