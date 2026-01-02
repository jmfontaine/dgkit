# Automated Tests

Run tests with `just test`.

## Unit Tests

Located in `tests/unit/`.

| File | Coverage |
|------|----------|
| `test_parsers.py` | XML to model conversion for Artist, Label, MasterRelease, Release |
| `test_filters.py` | Expression parsing, UnsetFields, FilterChain |
| `test_writers.py` | SQLite DSN parsing |
| `test_validation.py` | TrackingElement for strict mode detection |

## Integration Tests

Located in `tests/integration/`.

| File | Coverage |
|------|----------|
| `test_cli.py` | Convert and load commands with SQLite |
| `test_postgresql.py` | PostgreSQL writer using testcontainers |

## Fixtures

Shared fixtures in `tests/conftest.py`:

- `cli_runner`: Typer CLI test runner
- `sample_artists_xml`, `sample_labels_xml`: Sample XML content
- `tmp_gzip_file`: Factory for temporary gzipped XML files

Sample data in `tests/fixtures/`.
