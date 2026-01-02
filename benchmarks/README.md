# Benchmarks

Compare dgkit performance against alternative Discogs data processing tools.

## Prerequisites

- [hyperfine](https://github.com/sharkdp/hyperfine) - CLI benchmarking tool
- [gtime](https://formulae.brew.sh/formula/gnu-time) - GNU time for memory measurement (macOS: `brew install gnu-time`)
- Sample data in `../samples/` (see main README for creating samples)

## Setup

Install alternative tools:

```shell
cd benchmarks
./setup.sh
```

This clones and builds:

| Tool | Language | Repository |
|------|----------|------------|
| discogs-xml2db | Python | [philipmat/discogs-xml2db](https://github.com/philipmat/discogs-xml2db) |
| dgtools | Go | [marcw/dgtools](https://github.com/marcw/dgtools) |
| discogs-load | Rust | [DylanBartels/discogs-load](https://github.com/DylanBartels/discogs-load) |
| discogs-batch | Java | [echovisionlab/discogs-batch](https://github.com/echovisionlab/discogs-batch) |

## Running Benchmarks

```shell
# Default: 1M releases sample
./run.sh

# Specific sample file
./run.sh ../samples/discogs_20260101_artists_sample_1000000.xml.gz
```

The script measures:

1. **Timing** - Mean execution time via hyperfine (3 runs + warmup)
2. **Memory** - Peak RSS via GNU time
3. **Output size** - Resulting file sizes

Results are saved to `results/<sample_name>_timing.json`.

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
