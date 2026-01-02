# Benchmarking

Guidelines for benchmarking dgkit against alternatives.

## Alternatives

| Tool | Language | Database | Source |
|------|----------|----------|--------|
| [discogs-xml2db](https://github.com/philipmat/discogs-xml2db) | Python + C# | PostgreSQL, MySQL | GitHub |
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
