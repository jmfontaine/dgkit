# Repository Structure

```shell
.
├── .gitignore                            # Git ignore rules
├── .markdownlint-cli2.jsonc              # Markdown linting configuration
├── .pre-commit-config.yaml               # Pre-commit hooks configuration
├── .python-version                       # Python version for uv
├── benchmarks
│   ├── README.md                         # Benchmark documentation
│   ├── setup.py                          # Install alternative tools
│   ├── run.py                            # Run benchmark comparison
│   ├── alternatives                      # Cloned repos (gitignored)
│   └── results                           # Benchmark results (gitignored)
├── CLAUDE.md                             # AI assistant guidelines
├── docs/agent                            # AI assistant documentation (see CLAUDE.md)
├── justfile                              # Task runner commands (just)
├── LICENSE.txt                           # Apache 2.0 license
├── pyproject.toml                        # Package metadata and dependencies
├── README.md                             # User documentation
├── src
│   └── dgkit
│       ├── cli.py                        # CLI app and commands (Typer)
│       ├── filters.py                    # Expression-based record filtering
│       ├── models.py                     # NamedTuple models for Discogs entities
│       ├── parsers.py                    # XML element to model conversion
│       ├── pipeline.py                   # Orchestrates read -> parse -> filter -> write
│       ├── readers.py                    # Gzip file readers with progress tracking
│       ├── sampler.py                    # Extract samples from XML dumps
│       ├── sql                           # SQL schemas for database writers
│       │   ├── postgresql
│       │   │   ├── indices               # PostgreSQL index definitions
│       │   │   └── tables                # PostgreSQL table definitions
│       │   └── sqlite
│       │       ├── indices               # SQLite index definitions
│       │       └── tables                # SQLite table definitions
│       ├── summary.py                    # Processing statistics display
│       ├── types.py                      # Protocols and CLI-related enums
│       ├── validation.py                 # Strict mode validation helpers
│       └── writers.py                    # Output serialization (JSON, SQLite, etc.)
├── tests
│   ├── conftest.py                       # Pytest fixtures and configuration
│   ├── fixtures
│   │   ├── sample_artists.xml            # Test data for artist parsing
│   │   └── sample_labels.xml             # Test data for label parsing
│   ├── integration
│   │   ├── test_cli.py                   # End-to-end CLI tests
│   │   └── test_postgresql.py            # PostgreSQL writer tests
│   └── unit
│       ├── test_filters.py               # Filter logic tests
│       ├── test_parsers.py               # Parser tests
│       ├── test_validation.py            # Validation tests
│       └── test_writers.py               # Writer tests
└── uv.lock                               # Locked dependencies (uv)
```
