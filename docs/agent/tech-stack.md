# Tech Stack

## Python

Targets all [supported Python versions](https://devguide.python.org/versions/). Older versions may be supported if they don't complicate maintenance.

## Dependencies

- lxml: Streaming XML parsing of large Discogs dump files
- psycopg: PostgreSQL database output
- pyparsing: Filter expression parsing with boolean logic
- typer: Command-line interface

## Formatting and Linting

- markdownlint-cli2: Markdown linting
- pyproject-fmt: pyproject.toml formatting
- ruff: Python linting and formatting
- sqlfluff: SQL linting
