---
date: 2026-01-02
status: Accepted
---

# Parser Performance Optimizations

## Context and Problem Statement

Profiling `dgkit convert --format blackhole` on 1M release records (101.5s baseline)
revealed that parsing consumes ~65% of total time. The bottlenecks were:

| Function | Time | Calls | Issue |
|----------|------|-------|-------|
| `find_elements` | 36.7s (36%) | 1M | lxml iterparse (unavoidable) |
| `_parse_tracks` | 24.7s (24%) | 1M | Nested artist parsing |
| `_parse_extra_artists` | 16.7s (16%) | 3.1M | High call volume |
| `_parse_text_list` | 3.5s (3%) | 3M | Function call overhead |
| Object creation | 3.0s (3%) | 31M | NamedTuple instantiation |

## Considered Options

1. **Quick wins**: Slotted dataclasses, inline hot functions
2. **Medium effort**: mypyc or Cython compilation
3. **High effort**: Rust parser via PyO3, multiprocessing

## Decision Outcome

Chosen option: "Quick wins first", implementing:

### 1. Convert NamedTuples to `@dataclass(slots=True)`

- Reduced function calls by 37% (86.6M → 54.4M)
- Faster attribute access and lower memory usage
- Required updating `writers.py` and `filters.py` to use `dataclasses.asdict()`,
  `dataclasses.replace()`, etc.

### 2. Inline `_parse_text_list`

- Eliminated ~3M function calls
- Pattern: `[e.text for e in p.findall("tag") if e.text] if (p := elem.find("parent")) is not None else []`
- Marked with KLUDGE comment explaining rationale

### 3. Single-pass child iteration in hot parsers

- `_parse_credit_artists` and `_parse_extra_artists` iterate children once
  with tag dispatch instead of multiple `findtext()` calls
- Called ~3M times each, so avoiding repeated tree traversals matters
- Marked with KLUDGE comment explaining rationale

### Results

| Metric | Before | After | Change |
|--------|--------|-------|--------|
| Total time | 101.5s | 99.5s | -2% |
| Function calls | 86.6M | 51.4M | -41% |

### Parked: Rust Bindings

Rust parser via PyO3 (using `quick-xml` crate) was researched but parked:

- Would require moving parsing logic to Rust to see full benefit
- 3-5x speedup potential but 12+ hours effort
- Revisit if mypyc/Cython don't provide sufficient gains

## Consequences

- Code in `parsers.py` uses KLUDGE patterns that deviate from normal style
- KLUDGE comments reference this decision for context
- Future maintainers should profile before reverting optimizations
