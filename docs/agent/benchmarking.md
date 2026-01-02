# Benchmarking

Guidelines for benchmarking dgkit against alternatives.

## Quick Start

```shell
# One-time setup of alternative tools
just bench-setup

# Run benchmark comparison (default: 1M releases sample)
just bench

# Benchmark specific sample
just bench samples/discogs_20260101_artists_sample_1000000.xml.gz
```

See `benchmarks/README.md` for detailed setup and requirements.

## Profiling

Profile dgkit to identify bottlenecks:

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

Key functions to watch:

- `ReleaseParser.parse()` - main parsing entry point
- `_parse_tracks()` - tracklist parsing (high call volume)
- `_parse_credit_artists()` / `_parse_extra_artists()` - called millions of times

## Performance Principles

1. **Single iteration** - Iterate over XML children once, dispatch by tag. Avoid multiple `findtext()`/`find()` calls on the same element.
2. **Memory efficiency** - Clear parsed elements after processing to avoid memory buildup during streaming.
3. **Minimize allocations** - Reuse data structures where possible. NamedTuples are efficient.
4. **Profile before optimizing** - Use cProfile to identify actual bottlenecks.

## Alternatives

| Tool | Language | Database | Source |
|------|----------|----------|--------|
| [discogs-xml2db](https://github.com/philipmat/discogs-xml2db) | Python, C# | PostgreSQL, MySQL | GitHub |
| [dgtools](https://github.com/marcw/dgtools) | Go | PostgreSQL | GitHub |
| [discogs-load](https://github.com/DylanBartels/discogs-load) | Rust | PostgreSQL | GitHub |
| [discogs-batch](https://github.com/echovisionlab/discogs-batch) | Java | PostgreSQL | GitHub |

## Methodology

### Sample Benchmarks

For repeatable benchmarks with statistical validity, use sample files (e.g., 1M elements):

```bash
hyperfine --warmup 1 --runs 5 \
  'dgkit convert releases_sample.xml.gz -f sqlite' \
  'discogs-load releases_sample.xml.gz'
```

Create samples with:

```bash
dgkit sample discogs_20260101_releases.xml.gz -n 1000000
```

### Full Dump Benchmarks

For full dumps (1min to 1h+), single runs are acceptable. Capture:

- Wall clock time
- Peak RSS memory
- CPU user/system time
- Records processed per second
- Final database/file size

Use `/usr/bin/time -v` (Linux) or `gtime -v` (macOS via Homebrew).

## Discogs Dump Compression

### Finding: Discogs Uses Python gzip

Investigation of gzip headers revealed that Discogs uses Python's `gzip` module:

| Tool | XFL | OS byte |
|------|-----|---------|
| gzip/pigz/zopfli | 2 | 3 (Unix) |
| 7zip | 4 | 3 (Unix) |
| **Python gzip** | **2** | **255 (unknown)** |
| **Discogs dumps** | **2** | **255 (unknown)** |

The `OS=255` byte is distinctive to Python's gzip implementation.

### Compression Ratio Varies by Position

The compression ratio varies significantly across the file:

| Position | Ratio |
|----------|-------|
| Start (0-10MB) | ~29% |
| Middle (~1GB) | ~22% |
| End (~1.5GB) | ~20% |

The beginning contains more unique data (varied artist names). Later sections have more repetitive patterns. The overall ~22% ratio is an average.

### Verification

Recompressing `discogs_20260101_labels.xml.gz` with Python gzip level 9:

| File | Size |
|------|------|
| Original (Discogs) | 86,153,596 bytes |
| Python gzip level 9 | 86,153,592 bytes |
| Difference | -4 bytes (0.00%) |

The 4-byte difference is the mtime timestamp in the gzip header.

### Implications for dgkit

- The `sample` command uses Python gzip level 9, matching Discogs' approach
- Samples from the beginning of dumps will be less compressible than the full file
- No special compression tools (zopfli, pigz) are needed to match Discogs' output
