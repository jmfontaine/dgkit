---
date: 2026-01-03
status: Accepted
---

# Pipeline Concurrency Architecture

## Context and Problem Statement

Processing Discogs XML data (1M releases, 681MB gzipped) is CPU-bound. The pipeline
stages are: gzip decompression, XML iterparse, model creation, and writing. We explored
whether concurrency could improve throughput beyond the baseline.

**Input file:** `samples/discogs_20260101_releases_sample_1000000.xml.gz` (681MB, 1M releases)

**User requirements:**

- Users convert/load to a SINGLE destination at a time
- Optimize a single pipeline path, not parallel outputs

### Baseline Performance (Experiment 1)

| Output | Wall Time | Throughput | Peak Memory | Notes |
|--------|-----------|------------|-------------|-------|
| Blackhole | 279s | **3,580 rec/s** | 2.2 MB | Pure parsing speed |
| JSONL | 697s | 1,435 rec/s | 4.9 MB | asdict + json.dumps overhead |
| SQLite | 770s | 1,298 rec/s | 55.9 MB | Batched executemany |
| PostgreSQL | 923s | 1,083 rec/s | 56.0 MB | psycopg3 COPY protocol |

**Key baseline findings:**

- All stages are CPU-bound (user time ≈ wall time)
- Writing adds 2.5-3.3x overhead vs parse-only
- Serialization (asdict + json.dumps) is the bottleneck, not I/O

## Considered Options

1. **Producer-consumer queue**: Decouple parsing from writing with bounded queue
2. **Thread pool writers**: Dispatch batches to thread pool for parallel writing
3. **Threaded model creation**: Serialize XML elements, parse in thread pool
4. **Multiprocessing with dataclasses**: Process pool for parsing, IPC via pickle
5. **Multiprocessing with dicts**: Same, but dicts instead of dataclasses

## Decision Outcome

Chosen option: **Multiprocessing with dicts** (Experiment 10).

### Architecture

```text
[Main Process]                      [Worker Process]
gzip -> iterparse -> tostring ----> fromstring -> dict
                                          |
                                          v
                              [Main] <-- dict --> write
```

### Results

| Output | Baseline | MP+Dicts | Change |
|--------|----------|----------|--------|
| Blackhole | 279s (3,580/s) | 225s (4,443/s) | **+24%** |
| SQLite | 770s (1,298/s) | 495s (2,022/s) | **+56%** |
| PostgreSQL | 923s (1,083/s) | 653s (1,532/s) | **+41%** |

### Parameter Sweep

| Workers | Batch | Throughput | vs Baseline |
|---------|-------|------------|-------------|
| 1 | 50 | 3,722/s | +4% |
| **1** | **100** | **4,443/s** | **+24%** |
| 1 | 500 | 3,700/s | +3% |
| 4 | 100 | 4,322/s | +21% |
| 8 | 100 | 3,837/s | +7% |

**Optimal configuration:** 1 worker, batch_size=100

**Why 1 worker is optimal:** Main thread (iterparse + tostring) is the bottleneck.
More workers just wait for work. Adding workers increases IPC overhead without benefit.

### Core Implementation

**Worker process:**

```python
def worker_process(
    input_queue: mp.Queue,
    output_queue: mp.Queue,
    worker_id: int,
) -> None:
    """Worker: receives XML bytes, parses to dicts, sends back."""
    while True:
        batch = input_queue.get()
        if batch is STOP_SENTINEL:
            break

        results = []
        for xml_bytes in batch:
            release_dict = parse_release_from_bytes(xml_bytes)
            results.append(release_dict)

        output_queue.put(results)
```

**Main pipeline:**

```python
def run_pipeline(
    input_path: Path,
    writer: Writer,
    num_workers: int = 4,
    batch_size: int = 100,
    limit: int | None = None,
) -> int:
    """Main streams XML, workers parse to dicts, main writes."""
    ctx = mp.get_context("spawn")

    input_queue: mp.Queue = ctx.Queue(maxsize=num_workers * 2)
    output_queue: mp.Queue = ctx.Queue()

    workers = []
    for i in range(num_workers):
        p = ctx.Process(target=worker_process, args=(input_queue, output_queue, i))
        p.start()
        workers.append(p)

    batches_sent = 0
    batches_received = 0
    count = 0
    batch: list[bytes] = []

    for xml_bytes in stream_xml_bytes(input_path, limit):
        batch.append(xml_bytes)
        count += 1

        if len(batch) >= batch_size:
            input_queue.put(batch)
            batches_sent += 1
            batch = []

            # Drain output queue while streaming
            while not output_queue.empty():
                dicts = output_queue.get_nowait()
                batches_received += 1
                for d in dicts:
                    writer.write(d)

    # Send remaining batch
    if batch:
        input_queue.put(batch)
        batches_sent += 1

    # Signal workers to stop
    for _ in workers:
        input_queue.put(STOP_SENTINEL)

    # Collect remaining results
    while batches_received < batches_sent:
        dicts = output_queue.get()
        batches_received += 1
        for d in dicts:
            writer.write(d)

    for p in workers:
        p.join()

    writer.close()
    return count
```

**Streaming XML bytes (main thread):**

```python
def stream_xml_bytes(path: Path, limit: int | None = None) -> Iterator[bytes]:
    """Stream serialized XML elements from gzipped file."""
    with gzip.open(path, "rb") as f:
        context = etree.iterparse(f, events=("end",), tag="release")
        count = 0
        for _, elem in context:
            xml_bytes = etree.tostring(elem)
            yield xml_bytes
            elem.clear()
            while elem.getprevious() is not None:
                del elem.getparent()[0]
            count += 1
            if limit is not None and count >= limit:
                break
```

**Dict parsing (worker process):**

```python
def parse_release_from_bytes(xml_bytes: bytes) -> dict:
    """Parse release from XML bytes to dict. Runs in worker process."""
    elem = etree.fromstring(xml_bytes)

    master = elem.find("master_id")
    master_id = None
    is_main = None
    if master is not None and master.text:
        master_id = int(master.text)
        is_main_text = master.get("is_main_release")
        if is_main_text:
            is_main = is_main_text.lower() == "true"

    return {
        "id": int(elem.get("id") or 0),
        "status": elem.get("status"),
        "title": elem.findtext("title") or "",
        "country": elem.findtext("country"),
        "released": elem.findtext("released"),
        "notes": elem.findtext("notes"),
        "data_quality": elem.findtext("data_quality"),
        "master_id": master_id,
        "is_main_release": is_main,
        "artists": [parse_credit_artist(a) for a in elem.findall("artists/artist")],
        "labels": [parse_label(lbl) for lbl in elem.findall("labels/label")],
        "formats": [parse_format(f) for f in elem.findall("formats/format")],
        "genres": [g.text or "" for g in elem.findall("genres/genre")],
        "styles": [s.text or "" for s in elem.findall("styles/style")],
        "tracklist": [parse_track(t) for t in elem.findall("tracklist/track")],
        "identifiers": [parse_identifier(i) for i in elem.findall("identifiers/identifier")],
        "videos": [parse_video(v) for v in elem.findall("videos/video")],
        "companies": [parse_company(c) for c in elem.findall("companies/company")],
        "extra_artists": [parse_extra_artist(e) for e in elem.findall("extraartists/artist")],
        "series": [parse_series(s) for s in elem.findall("series/series")],
    }
```

## Options Rejected

### Threading Approaches (Experiments 2, 3, 9)

| Experiment | Approach | Blackhole | Change |
|------------|----------|-----------|--------|
| 2. Queue | Producer-consumer | 3,163/s | -12% |
| 3. ThreadPool | Batch dispatch | 1,123/s | -69% |
| 9. ThreadedModels | Serialize + thread | ~1,230/s | -66% |

**Why rejected:** Python's GIL prevents true parallelism for CPU-bound work.
Thread synchronization and context switching add overhead with no benefit.

**Experiment 2 (Producer-Consumer Queue):**

```text
[Main Thread]                    [Writer Thread]
gzip -> parse -> model --Queue--> write()
                         ^
                    bounded size
                    (backpressure)
```

Results:

| Output | Baseline | Queue | Change |
|--------|----------|-------|--------|
| Blackhole | 279s (3,580/s) | 316s (3,163/s) | -12% |
| JSONL | 697s (1,435/s) | 809s (1,236/s) | -14% |
| SQLite | 770s (1,298/s) | 1,062s (942/s) | -27% |
| PostgreSQL | 923s (1,083/s) | 1,063s (941/s) | -13% |

Queue sizes stayed consistently low (1-9), confirming parsing is the bottleneck.
Writer keeps up easily; queue buffering provides no benefit.

**Experiment 3 (Thread Pool Writers):**

```text
[Main Thread]           [ThreadPoolExecutor]
gzip -> parse --------> [worker1] -> write batch
              \-------> [worker2] -> write batch
               \------> [worker3] -> write batch
```

Catastrophically slow (3x overhead). Batching + thread dispatch overhead dominates.
Experiment abandoned after blackhole results showed -69%.

### Multiprocessing with Dataclasses (Experiment 4)

| Output | Baseline | MultiProcess | Change |
|--------|----------|--------------|--------|
| Blackhole | 279s (3,580/s) | 367s (2,723/s) | -24% |

**Why rejected:** `@dataclass(slots=True)` instances are slow to pickle.
IPC serialization overhead exceeds parallelism gains.

### Dicts in Single-Threaded (Experiment 11)

| Output | Baseline (dataclass) | Baseline (dicts) | Change |
|--------|---------------------|------------------|--------|
| Blackhole | 279s (3,580/s) | 979s (1,021/s) | **-71%** |

**Why rejected:** Dict creation has 3.5x more overhead than slotted dataclasses
in single-threaded code. Dicts only win when pickle speed matters (multiprocessing).

**Key insight:** Dicts pickle faster but create slower. Trade-off only pays off
when IPC dominates (multiprocessing).

### Experiments Not Run (5-8)

| Experiment | Approach | Why Skipped |
|------------|----------|-------------|
| 5. asyncpg | Async PostgreSQL | DB writes aren't the bottleneck |
| 6. Polars | DataFrame intermediate | Adds overhead, still bound by main thread |
| 7. Arrow+DuckDB | Columnar ingestion | Same - operates downstream of bottleneck |
| 8. Hybrid | Combine best | Experiment 10 is already optimal |

All operate downstream of the proven bottleneck (main thread parsing).

## The Fundamental Bottleneck

```text
Main thread (sequential, cannot be parallelized):
  gzip decompress -> lxml iterparse -> tostring
```

- **Gzip:** Stream-based, no random access. Can't chunk the file.
- **iterparse:** lxml holds element references, not thread-safe. Must be sequential.
- **tostring:** Required to pass elements across process boundary.

No concurrency approach can parallelize this chain. File chunking is not viable
for gzipped XML because:

1. Gzip compression creates inter-byte dependencies
2. XML has no fixed-size records or line boundaries
3. Finding element boundaries requires parsing

### Stage Characteristics

| Stage | Bound | Parallelizable? | Constraint |
|-------|-------|-----------------|------------|
| Gzip decompression | CPU | No | Sequential stream |
| XML iterparse | CPU | Limited | lxml not thread-safe |
| Model creation | CPU | Yes | GIL limits threads |
| JSON/JSONL write | I/O | Limited | Single file handle |
| SQLite insert | I/O | **No** | Single-writer |
| PostgreSQL insert | I/O | **Yes** | Connection pool |

## Consequences

### Positive

- +24% to +56% throughput improvement with multiprocess + dicts
- Clear understanding of what works and what doesn't
- Eliminates need to evaluate remaining experiments

### Negative

- Multiprocessing adds complexity vs simple baseline
- Dict-based approach loses type safety and IDE autocomplete
- Memory footprint slightly higher (worker process overhead)

### Trade-off Decision

**For dgkit: Keep baseline (single-threaded + dataclasses).**

Rationale:

- 24% slower but simpler code
- Maintains type safety with `@dataclass(slots=True)`
- Memory-efficient streaming
- Users process data once, not repeatedly

The multiprocess + dicts architecture is documented here for cases where
maximum throughput justifies the complexity.

## Summary Tables

### All Threading Approaches Failed

| Experiment | Approach | Blackhole | Result |
|------------|----------|-----------|--------|
| 2. Queue | Producer-consumer | 3,163/s | -12% |
| 3. ThreadPool | Batch dispatch | 1,123/s | -69% |
| 9. ThreadedModels | Serialize + thread | ~1,230/s | -66% |

**Why threading fails:** GIL prevents true parallelism for CPU-bound work.

### Multiprocessing Results

| Experiment | Data Format | Blackhole | Result |
|------------|-------------|-----------|--------|
| 4. MultiProcess | dataclasses | 2,723/s | -24% |
| 10. MultiProcess | dicts | 4,443/s | **+24%** |
| 11. Baseline | dicts | 1,021/s | -71% |

**Why dicts + multiprocessing wins:** Dicts pickle faster, offsetting IPC overhead.

### Actual Outcomes vs Expectations

| Experiment | Expected | Actual | Notes |
|------------|----------|--------|-------|
| 2. Queue | +10-20% | **-12% to -27%** | GIL kills threading |
| 3. ThreadPool | +20-50% for PG | **-69%** | Catastrophic overhead |
| 4. MultiProcess | -10% to +30% | **-24%** | Dataclass pickle too slow |
| 10. MP+Dicts | N/A | **+24% to +56%** | Dicts pickle fast |

## Free-Threaded Python (Experiment 12)

Python 3.13+ and 3.14+ can be built with free-threading support (`--disable-gil`),
which allows true parallel execution of threads. We tested whether this could make
threading viable for our CPU-bound XML parsing.

**Result: Not viable.**

When lxml is imported, it forces the GIL back on:

```text
RuntimeWarning: The global interpreter lock (GIL) has been enabled to load
module 'lxml.etree', which has not declared that it can run safely without
the GIL.
```

lxml is a C extension that hasn't been updated to declare thread-safety for
free-threaded Python. Until lxml (or an alternative XML parser) supports
free-threading, this approach is blocked.

Forcing `PYTHON_GIL=0` to override this behavior is unsafe and caused hangs
in testing.

**Conclusion:** Free-threaded Python doesn't help for XML parsing workloads
until the core libraries (lxml, libxml2 bindings) add support.

## Recommendations

1. **For maximum throughput:** Use Experiment 10 architecture (multiprocess + dicts)
2. **For simplicity:** Keep baseline (single-threaded + dataclasses) - only 24% slower
3. **Don't bother with threading:** Always slower due to GIL

## References

- [Real Python: Python Concurrency](https://realpython.com/python-concurrency/)
- [lxml Performance](https://lxml.de/performance.html)
- [Multiprocessing Queue](https://superfastpython.com/multiprocessing-queue-in-python/)
- [IBM: High-performance XML parsing](https://public.dhe.ibm.com/software/dw/xml/x-hiperfparse/x-hiperfparse-pdf.pdf)
