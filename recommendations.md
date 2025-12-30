# dgkit Recommendations

Based on code review and research. Each section includes options with a preferred recommendation.

---

## UX Issues

### 1. Format as Option vs Positional Argument

**Current:** `dgkit convert jsonl file1.xml file2.xml`

| Option | Example | Pros | Cons |
|--------|---------|------|------|
| **A) Keep positional** | `dgkit convert jsonl files...` | Shorter | Conflicts with `-f` for force |
| **B) Use `--format/-f`** | `dgkit convert files... -f jsonl` | Unix convention, flexible ordering | Slightly longer |
| **C) Separate commands** | `dgkit to-jsonl files...` | Very explicit | More commands to maintain |

**Decision: Option B.** Rename `--force` to `--overwrite/-w` or `--yes/-y`. Matches Miller, jq patterns.

### 2. Separate `convert` from `load` Commands

**Current:** Format enum mixes file formats (jsonl) with databases (sqlite).

**Decision:** Split into two commands:

```
dgkit convert files... --format jsonl --compress gzip
dgkit load files... --database sqlite --path ./discogs.db
```

**Rationale:** Avoids mixing unrelated options (compression vs port/host). Matches sqlite-utils and csvkit patterns.

**Console/Blackhole:** Keep blackhole as a regular format in `convert`. Move console to `inspect --preview`.

---

## CLI Options Improvements

### 3. `--read-chunk-size`

**Default:** 1MB (matches pip, Azure recommendations)

**Format options:**
- Human-readable (`1MB`, `512KB`) - better UX, requires parsing
- Bytes only (`1048576`) - simpler implementation

**Decision:** Support both. Note: Impact may be limited since lxml.iterparse handles its own buffering. Benchmark before/after.

### 4. `--batch-size`

**Current:** SqliteWriter writes one record at a time.

**Impact:** Batch inserts are 28-70x faster than single inserts.

| Default | Trade-off |
|---------|-----------|
| 1,000 | Safe for SQLite variable limits |
| 10,000 | Higher throughput, more memory |

**Decision:** Default 10,000. Pair with PRAGMA optimizations:
```sql
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
PRAGMA cache_size = -64000;
```

### 5. Benchmarking

**Decision:** Add `--benchmark` flag to `convert` and `load` commands instead of a separate command. Avoids duplicating options and works with any specific option/value combination.

**Metrics to display:** Total time, records/sec, memory peak, time breakdown (read/parse/write percentages).

### 6. `inspect` Command

**Decision:** Three modes with format option:

| Mode | Behavior |
|------|----------|
| Default (quick) | File stats + metadata, no parsing (~1 second) |
| `--deep` | Full parse: record count, field coverage |
| `--sample N` | Parse first N records, show examples |

Add `--format/-f` option for sample output: `repr` (default), `json`, `table`.

---

## Database Improvements

### 7. SQL Schemas as Separate Files

**Decision:**
```
src/dgkit/sql/
  sqlite/
    tables/artist.sql, label.sql, ...
    indices/artist_indices.sql, ...
    constraints/foreign_keys.sql
  postgresql/  # future
```

**Benefits:** Diff-friendly for review, database-specific variations coexist, load with `importlib.resources`.

**Foreign keys with partial loads:** For v1, expect all files to be loaded. Document this requirement. FK constraints fail gracefully if referenced table is missing. Revisit if users request partial load support.

### 8. Create Indices After Data Insertion

**Current:** No index creation.

**Research:** Creating indices after bulk inserts is up to 5x faster.

**Decision:**
```python
def __exit__(self, exc_type, exc_val, exc_tb):
    if self._conn and not exc_type:
        self._create_indices()
        self._create_constraints()
        self._conn.execute("ANALYZE")
        self._conn.commit()
```

**What ANALYZE does:** Updates SQLite's query planner statistics. After bulk inserts, the planner has no data distribution info. ANALYZE scans tables/indices and stores stats so queries use optimal execution plans. Run once after loading, not per-query.

### 9. Splitting List Fields (Normalization)

**Current:** Lists serialized as JSON strings.

**Models affected:** `Artist.aliases`, `Artist.name_variations`, `Artist.urls`

| Approach | Query Speed | Complexity |
|----------|-------------|------------|
| JSON columns | Slow for filtering | Low |
| Normalized tables | Fast with indices | Medium |

**Decision:**
- **Normalize aliases** (queryable FK relationship):
  ```sql
  CREATE TABLE artist_alias (
      artist_id INTEGER NOT NULL,
      alias_id INTEGER NOT NULL,
      PRIMARY KEY (artist_id, alias_id)
  );
  ```
- **Keep URLs as JSON array** (rarely queried, display-only)
- **Drop name_variations from Artist model** - reconstruct at query time from releases/tracks where it appears in context

### 10. Schema Review for Query Performance

**Current issues:** No primary keys, no indices, no foreign keys.

**Decision:**
- Use `INTEGER PRIMARY KEY` (alias for ROWID in SQLite)
- Create covering indices for common query patterns
- Run `ANALYZE` after index creation

---

## Testing and Benchmarking

### 11. Test Organization

**Decision:** Start with by-type organization, split by entity when files exceed ~300 lines:

```
tests/
  conftest.py
  unit/test_parsers.py, test_writers.py, ...
  integration/test_cli.py, test_convert_flow.py
  performance/test_benchmarks.py
  fixtures/sample_artists.xml, ...
```

**Stack:** pytest + typer.testing.CliRunner + pytest-benchmark + pytest-cov

### 12. Performance Regression Testing

| Tool | Use |
|------|-----|
| pytest-benchmark | Function-level, baseline comparison |
| hyperfine | CLI-level end-to-end timing |
| Bencher/CodSpeed | CI tracking (add later) |

```bash
pytest tests/performance/ --benchmark-save=baseline
pytest tests/performance/ --benchmark-compare=baseline --benchmark-compare-fail=mean:10%
```

### 13. Benchmarking Against Alternatives

**Methodology:**
1. Same hardware, data, workload for all tools
2. Use actual Discogs dump subsets (small/medium/large)
3. Warm-up runs, minimum 10 runs
4. Document versions, configuration, hardware

**Tool:** hyperfine for fair CLI comparison.

### 14. Memory Leak Detection

| Tool | Platform | Use Case |
|------|----------|----------|
| tracemalloc | All | Development, cross-platform |
| memray | Linux | Deep analysis, flamegraphs |
| pytest-memray | Linux | CI with `@pytest.mark.limit_leaks` |

**Decision:** tracemalloc for development, pytest-memray for Linux CI.

---

## Deployment and Distribution

### 15. PyPI Publishing

**Decision:** uv + GitHub Actions Trusted Publishing (no API tokens needed).

1. Add pending publisher at pypi.org/manage/account/publishing/
2. Use `uv build` + `pypa/gh-action-pypi-publish@release/v1`

### 16. uvx and pipx

**No configuration needed.** Once on PyPI:
```bash
uvx dgkit --help
pipx run dgkit --help
```

uvx is significantly faster (Rust vs Python).

### 17. Homebrew

**Priority:** Medium. Create personal tap `github.com/jmf/homebrew-dgkit` with formula generated by homebrew-pypi-poet.

### 18. Standalone Binaries

**Decision: Skip.** Complexity not worth it:
- lxml requires native compilation per platform
- uvx/pipx provide easy installation
- Would need 6+ builds (Win/Mac/Linux x86_64/ARM64)

### 19. Cross-Platform Compatibility

**Current:** Good. lxml has pre-built wheels for all major platforms.

**Action:** Test via GitHub Actions matrix before each release.

---

## Architecture Questions

### 20. Option Organization (Reader vs Writer)

**Decision:** Use Typer's `rich_help_panel`:

```python
read_chunk_size: Annotated[int, typer.Option(rich_help_panel="Reader Options")]
batch_size: Annotated[int, typer.Option(rich_help_panel="Writer Options")]
```

Help output groups options visually without naming prefixes.

### 21. Hiding Blackhole Writer

**Decision:** Keep as valid format, document only in advanced docs.

### 22. Data Filtering

**Decision:** Filter protocol with composable chain:

```python
class Filter(Protocol):
    def __call__(self, record: NamedTuple) -> NamedTuple | None: ...

class DropByValue:
    def __call__(self, record): ...

class UnsetFields:
    def __call__(self, record):
        return record._replace(**updates)  # NamedTuples work fine
```

CLI: `--drop-if field=value` and `--unset field1,field2`

### 23. Alternative Readers

**Decision:** Reader registry with optional dependencies:

| Backend | Speed | Use Case |
|---------|-------|----------|
| standard | Baseline | Default, no extra deps |
| rapidgzip | 10-20x faster | Large files, multi-core |
| indexed | Fast seeks | Random access |

```toml
[project.optional-dependencies]
fast = ["rapidgzip"]
```

CLI: `--reader rapidgzip`

---

## CI/CD

### 24. Multi-Platform Testing

**Decision:** GitHub Actions matrix:

```yaml
strategy:
  matrix:
    os: [ubuntu-latest, macos-latest, windows-latest]
    python-version: ["3.10", "3.11", "3.12", "3.13"]
```

### 25. Workflow Structure

**Two workflows:**

| Workflow | Trigger | Jobs |
|----------|---------|------|
| `ci.yml` | Push, PRs | lint, type-check, test (matrix) |
| `release.yml` | Tag `v*` | test, build, publish to PyPI |

Use `astral-sh/setup-uv@v5` with `enable-cache: true`.

---

## Action Items

Prioritized list of implementation tasks:

| # | Item | Effort | Notes |
|---|------|--------|-------|
| 1 | Change format to `--format/-f` option | Low | Rename `--force` to `--overwrite/-w` |
| 2 | Separate `convert` and `load` commands | Medium | Keep blackhole as regular format |
| 3 | Add data filtering (`--drop-if`, `--unset`) | Medium | Filter protocol with NamedTuple._replace() |
| 4 | Add `--batch-size` to SqliteWriter | Low | Biggest perf win, unbatched is 28-70x slower |
| 5 | Create indices after data insertion | Low | Add PRAGMA opts + ANALYZE |
| 6 | Store SQL schemas as separate files | Low | `sql/sqlite/tables/`, `indices/`, `constraints/` |
| 7 | Normalize alias relationships | Medium | Keep URLs as JSON, drop name_variations |
| 8 | Add pytest + typer.testing setup | Medium | By-type organization |
| 9 | Set up PyPI + GitHub Actions CI | Low | Enables distribution, blocks nothing |
| 10 | Create Homebrew tap | Medium | After PyPI stable |
| 11 | Add `--benchmark` flag to convert/load | Low | Show perf summary at end |
| 12 | Implement `inspect` command | Medium | Quick mode, `--deep`, `--sample N`, `--format` |
| 13 | Add alternative readers registry | Medium | Optional deps: `dgkit[fast]` for rapidgzip |

**Deferred:**
- Standalone binaries (skip permanently)
- Partial load support for FKs (v1 expects all files loaded)
