import sys

import typer
from pathlib import Path
from typing import Annotated

from rich.console import Console
from rich.panel import Panel

from dgkit.summary import Summary
from dgkit.filters import Filter, parse_filter, parse_unset
from dgkit.pipeline import (
    build_database_path,
    build_output_path,
    convert,
    load,
)
from dgkit.types import Compression, DatabaseType, FileFormat

# Global debug flag
_debug = False
console = Console()


def display_result(result: Summary) -> None:
    """Display processing result with Rich formatting."""
    if result.warnings:
        warnings_text = "\n".join(result.warnings)
        console.print(Panel(warnings_text, title="Unhandled Data", border_style="yellow"))
    console.print(Panel(result.display(), title="Summary", border_style="green"))


def build_filters(drop_if: list[str], unset: list[str]) -> list[Filter]:
    """Build filter list from CLI options."""
    filters: list[Filter] = []
    for expr in drop_if:
        filters.append(parse_filter(expr))
    unset_filter = parse_unset(unset)
    if unset_filter:
        filters.append(unset_filter)
    return filters


def _exception_handler(exc_type, exc_value, exc_traceback):
    """Handle exceptions with clean output unless debug mode is enabled."""
    if _debug:
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
    else:
        typer.echo(f"Error: {exc_value}", err=True)
        raise SystemExit(1)


app = typer.Typer(help="Discogs Toolkit")


@app.callback()
def main(
    debug: Annotated[
        bool, typer.Option("--debug", help="Show full error tracebacks.")
    ] = False,
):
    """Discogs Toolkit - Process Discogs data dumps."""
    global _debug
    _debug = debug
    sys.excepthook = _exception_handler


@app.command(name="convert", help="Convert data dumps to another format.")
def convert_cmd(
    files: Annotated[list[Path], typer.Argument(help="Input files.")],
    format: Annotated[
        FileFormat,
        typer.Option("--format", "-f", case_sensitive=False, help="Output file format."),
    ],
    limit: Annotated[
        int | None, typer.Option(help="Max records per file.")
    ] = None,
    output_dir: Annotated[
        Path, typer.Option("--output-dir", "-o", help="Output directory.")
    ] = Path("."),
    compress: Annotated[
        Compression, typer.Option("--compress", "-c", case_sensitive=False, help="Compression algorithm.")
    ] = Compression.none,
    overwrite: Annotated[
        bool, typer.Option("--overwrite", "-w", help="Overwrite existing files.")
    ] = False,
    drop_if: Annotated[
        list[str], typer.Option("--drop-if", help="Drop records matching field=value.")
    ] = [],
    unset: Annotated[
        list[str], typer.Option("--unset", help="Fields to set to null (comma-separated).")
    ] = [],
    summary: Annotated[
        bool, typer.Option("--summary/--no-summary", help="Show summary.")
    ] = True,
    progress: Annotated[
        bool, typer.Option("--progress/--no-progress", help="Show progress bar.")
    ] = True,
    strict: Annotated[
        bool, typer.Option("--strict", help="Validate XML elements for unhandled data.")
    ] = False,
    fail_on_unhandled: Annotated[
        bool, typer.Option("--fail-on-unhandled", help="Fail on unhandled XML data (implies --strict).")
    ] = False,
):
    # --fail-on-unhandled implies --strict
    if fail_on_unhandled:
        strict = True

    # Check for existing output files (only for file-based formats)
    if format not in (FileFormat.console, FileFormat.blackhole) and not overwrite:
        valid_files = [f for f in files if f.is_file()]
        existing = [
            build_output_path(f, format, output_dir, compress)
            for f in valid_files
            if build_output_path(f, format, output_dir, compress).exists()
        ]
        if existing:
            typer.echo("The following files already exist:")
            for path in existing:
                typer.echo(f"  {path}")
            if not typer.confirm("Overwrite?"):
                raise typer.Abort()

    filters = build_filters(drop_if, unset)
    result = convert(
        format, files, limit=limit, output_dir=output_dir,
        compression=compress, filters=filters,
        show_summary=summary, show_progress=progress,
        strict=strict, fail_on_unhandled=fail_on_unhandled,
    )
    if result:
        display_result(result)


@app.command(name="load", help="Load data dumps into a database.")
def load_cmd(
    files: Annotated[list[Path], typer.Argument(help="Input files.")],
    database: Annotated[
        DatabaseType,
        typer.Option("--database", "-d", case_sensitive=False, help="Database type."),
    ],
    dsn: Annotated[
        str | None, typer.Option("--dsn", help="Database connection string.")
    ] = None,
    limit: Annotated[
        int | None, typer.Option(help="Max records per file.")
    ] = None,
    batch: Annotated[
        int, typer.Option("--batch", "-b", help="Batch size for database inserts.")
    ] = 10000,
    overwrite: Annotated[
        bool, typer.Option("--overwrite", "-w", help="Overwrite existing database.")
    ] = False,
    drop_if: Annotated[
        list[str], typer.Option("--drop-if", help="Drop records matching field=value.")
    ] = [],
    unset: Annotated[
        list[str], typer.Option("--unset", help="Fields to set to null (comma-separated).")
    ] = [],
    summary: Annotated[
        bool, typer.Option("--summary/--no-summary", help="Show summary.")
    ] = True,
    progress: Annotated[
        bool, typer.Option("--progress/--no-progress", help="Show progress bar.")
    ] = True,
    strict: Annotated[
        bool, typer.Option("--strict", help="Validate XML elements for unhandled data.")
    ] = False,
    fail_on_unhandled: Annotated[
        bool, typer.Option("--fail-on-unhandled", help="Fail on unhandled XML data (implies --strict).")
    ] = False,
):
    # --fail-on-unhandled implies --strict
    if fail_on_unhandled:
        strict = True

    valid_files = [f for f in files if f.is_file()]

    # Derive DSN from input filenames if not provided
    if dsn is None:
        path = build_database_path(valid_files, Path("."))
        dsn = str(path)

    # Check for existing database (only for file-based DSNs)
    if not dsn.startswith("sqlite://") or "/:memory:" not in dsn:
        db_path = Path(dsn.replace("sqlite:///", "").replace("sqlite://", ""))
        if db_path.exists() and not overwrite:
            typer.echo(f"Database already exists: {db_path}")
            if not typer.confirm("Overwrite?"):
                raise typer.Abort()

    filters = build_filters(drop_if, unset)
    result = load(
        database, files, dsn=dsn, limit=limit,
        filters=filters, batch_size=batch,
        show_summary=summary, show_progress=progress,
        strict=strict, fail_on_unhandled=fail_on_unhandled,
    )
    if result:
        display_result(result)
