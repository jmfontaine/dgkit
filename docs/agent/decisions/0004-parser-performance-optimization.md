---
date: 2026-01-04
status: In Progress
---

# Parser Performance Optimization

## Context and Problem Statement

Processing 18.8M releases took 75 minutes (~4,178 records/sec). Profiling revealed that
~63% of time is spent in Python model creation, not XML parsing. The goal is to identify
and implement optimizations to improve throughput.

**Input file:** `samples/discogs_20260101_releases_sample_1000000.xml.gz` (681MB, 1M releases)

### Benchmark Methodology

```bash
uv run dgkit convert --format blackhole --no-progress samples/discogs_20260101_releases_sample_1000000.xml.gz
```

Run 3 times, record time and throughput from the summary output.

### Baseline Performance

| Run | Time | Throughput |
|-----|------|------------|
| 1 | 88s | 11,337/s |
| 2 | 84s | 11,869/s |
| 3 | 83s | 11,909/s |
| **Average** | **85s** | **11,700/s** |

Peak memory: 30 MB

### Profiling Results (cProfile)

| Component | Time | % | Calls |
|-----------|------|---|-------|
| `find_elements` (lxml iterparse) | 36.5s | 37% | 1M |
| `_parse_tracks` | 22.6s | 23% | 1M |
| `_parse_extra_artists` | 15.1s | 15% | 3.1M |
| `_parse_companies` | 5.8s | 6% | 583K |
| `_parse_credit_artists` | 4.7s | 5% | 2.9M |
| `_parse_formats` | 4.4s | 4% | 1M |
| `_parse_identifiers` | 3.7s | 4% | 649K |
| `_parse_videos` | 3.4s | 3% | 515K |
| gzip decompression | 3.3s | 3% | - |
| `list.append` | 2.1s | 2% | 30M |

### Profiling Results (scalene, line-level)

**pipeline.py (lxml operations):**

| Line | % | Code |
|------|---|------|
| 65 | **29.2%** | `parent = elem.getparent()` |
| 70 | 9.0% | `elem.clear()` |
| 62 | 2.7% | `for _, elem in context:` |

**parsers.py (model creation):**

| Line | % | Code |
|------|---|------|
| 178 | 5.7% | `int(child.text) if child.text else None` |
| 295 | 3.4% | `position = child.text` |
| 189 | 3.1% | `ExtraArtist(...)` constructor |
| 307 | 2.8% | `Track(...)` constructor |

### Key Finding

**`elem.getparent()` accounts for 29% of total runtime.** This call exists to filter
nested elements (e.g., `<label>` inside `<sublabels>`). For releases, which have no
nested releases, this check runs on every element but never filters anything.

## Considered Options

### 1. Skip getparent() for entity types without nesting

**Target:** 29% hotspot
**Expected gain:** ~25% faster
**Effort:** Low

The releases file has no nested `<release>` elements. Only labels have nesting
(`<sublabels>` contains `<label>` elements). Skip the parent check for releases,
artists, and masters.

```python
# Current (all entities)
container = _DISCOGS_CONTAINERS.get(tag)
for _, elem in context:
    if container is not None:
        parent = elem.getparent()  # 29% of runtime!
        if parent is None or parent.tag != container:
            continue

# Proposed (only for labels)
needs_parent_check = tag == "label"
for _, elem in context:
    if needs_parent_check:
        parent = elem.getparent()
        if parent is None or parent.tag != "labels":
            continue
```

### 2. Replace dataclasses with msgspec.Struct

**Target:** 10-15% in constructors
**Expected gain:** ~10% faster
**Effort:** Medium

msgspec.Struct is significantly faster than dataclasses for object creation.

```python
# Current
@dataclass(slots=True)
class ExtraArtist:
    id: int | None
    artist_name_variation: str | None
    name: str | None
    role: str | None
    tracks: str | None

# Proposed
import msgspec

class ExtraArtist(msgspec.Struct, frozen=True):
    id: int | None
    artist_name_variation: str | None
    name: str | None
    role: str | None
    tracks: str | None
```

Trade-offs:

- Adds msgspec dependency
- May affect downstream serialization (asdict behavior)

### 3. Use match statement instead of if/elif chains

**Target:** String comparisons in parser loops
**Expected gain:** 2-5% faster
**Effort:** Low

Python 3.10+ match statements may optimize string dispatch.

```python
# Current
for child in artist_elem:
    tag = child.tag
    if tag == "id":
        artist_id = int(child.text) if child.text else None
    elif tag == "name":
        name = child.text
    elif tag == "anv":
        anv = child.text
    # ...

# Proposed
for child in artist_elem:
    match child.tag:
        case "id":
            artist_id = int(child.text) if child.text else None
        case "name":
            name = child.text
        case "anv":
            anv = child.text
        # ...
```

### 4. Pre-allocate lists with known sizes

**Target:** 30M list.append calls (2.1s)
**Expected gain:** 5-10% faster
**Effort:** Low

When the number of elements is known, pre-allocate the list.

```python
# Current
tracks = []
for track_elem in tracklist_elem:
    tracks.append(_parse_track(track_elem))

# Proposed
track_elems = list(tracklist_elem)
tracks = [_parse_track(t) for t in track_elems]
```

### 5. Cache frequently accessed attributes

**Target:** Repeated `.text` and `.get()` calls
**Expected gain:** 1-2% faster
**Effort:** Low

Avoid repeated attribute lookups in tight loops.

### 6. Use NamedTuple instead of dataclass

**Target:** Constructor overhead
**Expected gain:** 15-25% faster
**Effort:** Medium

NamedTuple has less overhead than dataclass for simple structs.

Trade-offs:

- Less flexibility (no default_factory)
- Different serialization behavior

### 7. Cython compilation of hot parser functions

**Target:** `_parse_extra_artists`, `_parse_tracks`
**Expected gain:** 40-60% on those functions
**Effort:** High

Compile the hottest parser functions with Cython.

Trade-offs:

- Build complexity
- Platform-specific wheels

### 8. PyPy instead of CPython

**Target:** Overall Python overhead
**Expected gain:** 2-5x overall
**Effort:** Zero code changes

Run under PyPy instead of CPython.

Trade-offs:

- Compatibility issues with some C extensions
- Different memory characteristics

## Experiment Results

### Experiment 1: Skip getparent() for non-label entities

**Status:** Complete

**Hypothesis:** Removing the getparent() call for releases/artists/masters will
reduce runtime by ~25%.

**Implementation:**

```python
_ENTITIES_WITH_NESTING = {"label"}

def find_elements(
    stream: IO[bytes], tag: str, limit: int | None = None
) -> Iterator[etree._Element]:
    check_parent = tag in _ENTITIES_WITH_NESTING
    context = etree.iterparse(stream, events=("end",), tag=tag)
    count = 0
    for _, elem in context:
        if check_parent:
            parent = elem.getparent()
            if parent is None or parent.tag != "labels":
                continue
        yield elem
        # ... rest unchanged
```

**Results:**

| Metric | Baseline | Optimized | Change |
|--------|----------|-----------|--------|
| Time | 85s | 84s | -1% |
| Throughput | 11,700/s | 11,810/s | +1% |

**Conclusion:** Minimal improvement. Scalene's profiler overhead inflated the
apparent cost of getparent(). The actual lxml C-level call is very fast.
Keeping the change since it's cleaner and slightly faster.

### Experiment 2: msgspec.Struct

**Status:** Complete

**Hypothesis:** Replacing dataclasses with msgspec.Struct will reduce runtime by ~10%.

**Implementation:**

- Added `msgspec>=0.19` dependency
- Converted all 16 model classes in `models.py` from `@dataclass(slots=True)` to `msgspec.Struct`
- Updated `writers.py` to use `msgspec.to_builtins()` for JSON serialization
- Updated `filters.py` to use `msgspec.structs.replace()`

**Results:**

| Run | Time | Throughput |
|-----|------|------------|
| 1 | 77s | 12,949/s |
| 2 | 78s | 12,812/s |
| 3 | 78s | 12,781/s |
| **Average** | **78s** | **12,847/s** |

| Metric | Baseline | Optimized | Change |
|--------|----------|-----------|--------|
| Time | 85s | 78s | -8% |
| Throughput | 11,700/s | 12,847/s | +10% |

**Conclusion:** Significant improvement. msgspec.Struct has lower object creation
overhead than dataclasses. The 10% throughput gain matches the expected improvement.
Keeping the change.

### Experiment 3: Match statement

**Status:** Complete

**Hypothesis:** Using match statements instead of if/elif chains will reduce runtime by 2-5%.

**Implementation:**

Converted 7 if/elif chains to match statements in `parsers.py`:

- `_parse_credit_artists` (4 cases, called 2.9M times)
- `_parse_extra_artists` (5 cases, called 3.1M times)
- `_parse_sub_tracks` (5 cases)
- `_parse_tracks` (6 cases, called 1M times)
- `_parse_companies` (5 cases)
- `_parse_videos` (2 cases)
- `ReleaseParser.parse` (17 cases, called 1M times)

**Results:**

| Run | Time | Throughput |
|-----|------|------------|
| 1 | 76s | 13,038/s |
| 2 | 77s | 12,869/s |
| 3 | 77s | 12,979/s |
| **Average** | **77s** | **12,962/s** |

| Metric | Before (Exp 2) | After | Incremental |
|--------|----------------|-------|-------------|
| Time | 78s | 77s | -1% |
| Throughput | 12,847/s | 12,962/s | +1% |

| Metric | Baseline | Cumulative | Change |
|--------|----------|------------|--------|
| Time | 85s | 77s | -9% |
| Throughput | 11,700/s | 12,962/s | +11% |

**Conclusion:** Minimal incremental improvement (~1%), but cleaner code. Python's match
statement doesn't provide significant performance gains over if/elif for string dispatch.
Keeping the change for readability.

### Experiment 4: List comprehensions

**Status:** Not started

## Decision Outcome

TBD - experiments in progress.

## References

- [msgspec documentation](https://jcristharif.com/msgspec/)
- [Python match statement PEP 634](https://peps.python.org/pep-0634/)
- [lxml performance tips](https://lxml.de/performance.html)
