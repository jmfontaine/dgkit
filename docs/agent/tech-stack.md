# Tech Stack

## Python

- dgkit aims at being compatible with all [supported Python versions](https://devguide.python.org/versions/).
- When possible, dgkit supports older unsupported versions as long as it does not negatively impact the maintainability of the project or hurt the performance and user experience for supported versions.

## Dependencies

- lxml: Streaming XML parsing of large Discogs dump files
- psycopg: PostgreSQL database output
- pyparsing: Filter expression parsing with boolean logic
- typer: Command-line interface

## Formatting and Linting

- pyproject-fmt: pyproject.toml formatting
- ruff: Python linting and formatting
- sqlfluff: SQL linting
