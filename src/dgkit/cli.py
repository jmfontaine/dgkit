import sys
import time
import types
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.panel import Panel

from dgkit.filters import Filter, parse_filter, parse_unset
from dgkit.pipeline import (
    build_database_path,
    build_output_path,
    convert,
    create_progress_elements,
    load,
)
from dgkit.sampler import build_sample_path, sample
from dgkit.summary import Summary, _format_duration
from dgkit.types import Compression, DatabaseType, EntityType, FileFormat


def _infer_database_type(dsn: str) -> DatabaseType:
    """Infer database type from DSN string."""
    dsn_lower = dsn.lower()
    if dsn_lower.startswith("postgresql://") or dsn_lower.startswith("postgres://"):
        return DatabaseType.postgresql
    return DatabaseType.sqlite


# Global debug flag
_debug = False
_console = Console()


def display_result(result: Summary) -> None:
    """Display processing result with Rich formatting."""
    if result.warnings:
        warnings_text = "\n".join(result.warnings)
        _console.print(
            Panel(warnings_text, title="Unhandled Data", border_style="yellow")
        )
    _console.print(Panel(result.display(), title="Summary", border_style="green"))


def build_filters(drop_if: list[str], unset: list[str]) -> list[Filter]:
    """Build filter list from CLI options."""
    filters: list[Filter] = []
    for expr in drop_if:
        filters.append(parse_filter(expr))
    unset_filter = parse_unset(unset)
    if unset_filter:
        filters.append(unset_filter)
    return filters


def _exception_handler(
    exc_type: type[BaseException] | None,
    exc_value: BaseException | None,
    exc_traceback: types.TracebackType | None,
) -> None:
    """Handle exceptions with clean output unless debug mode is enabled."""
    if _debug:
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
    else:
        typer.echo(f"Error: {exc_value}", err=True)
        raise SystemExit(1)


app = typer.Typer(
    help="Process Discogs data dumps.",
    no_args_is_help=True,
    rich_markup_mode="rich",
)


@app.callback()
def main(
    debug: Annotated[
        bool, typer.Option("--debug", help="Show full error tracebacks.")
    ] = False,
) -> None:
    """Configure global options."""
    global _debug
    _debug = debug
    sys.excepthook = _exception_handler


@app.command(name="convert", help="Convert data dumps to another format.")
def convert_cmd(
    files: Annotated[list[Path], typer.Argument(help="Discogs dump files.")],
    format: Annotated[
        FileFormat,
        typer.Option(
            "--format", "-f", case_sensitive=False, help="Output file format."
        ),
    ],
    limit: Annotated[int | None, typer.Option(help="Max records per file.")] = None,
    output_dir: Annotated[
        Path, typer.Option("--output-dir", "-o", help="Output directory.")
    ] = Path("."),
    compress: Annotated[
        Compression,
        typer.Option(
            "--compress", "-c", case_sensitive=False, help="Compression algorithm."
        ),
    ] = Compression.none,
    overwrite: Annotated[
        bool, typer.Option("--overwrite", "-w", help="Overwrite existing files.")
    ] = False,
    entity_type: Annotated[
        EntityType | None,
        typer.Option(
            "--type",
            "-t",
            case_sensitive=False,
            help="Entity type (if not auto-detected).",
        ),
    ] = None,
    drop_if: Annotated[
        list[str], typer.Option("--drop-if", help="Drop records matching field=value.")
    ] = [],
    unset: Annotated[
        list[str],
        typer.Option("--unset", help="Fields to set to null (comma-separated)."),
    ] = [],
    summary: Annotated[
        bool, typer.Option("--summary/--no-summary", help="Show summary.")
    ] = True,
    progress: Annotated[
        bool, typer.Option("--progress/--no-progress", help="Show progress bar.")
    ] = True,
    strict: Annotated[
        bool, typer.Option("--strict", help="Warn about unhandled XML elements.")
    ] = False,
    strict_fail: Annotated[
        bool,
        typer.Option(
            "--strict-fail", help="Fail on unhandled XML data (implies --strict)."
        ),
    ] = False,
) -> None:
    # --strict-fail implies --strict
    if strict_fail:
        strict = True

    # Check for existing output files (only for file-based formats)
    if format not in (FileFormat.console, FileFormat.blackhole) and not overwrite:
        valid_files = [f for f in files if f.is_file()]
        output_paths = [
            build_output_path(f, format, output_dir, compress) for f in valid_files
        ]
        existing = [p for p in output_paths if p.exists()]
        if existing:
            typer.echo("The following files already exist:")
            for path in existing:
                typer.echo(f"  {path}")
            if not typer.confirm("Overwrite?"):
                raise typer.Abort()

    filters = build_filters(drop_if, unset)
    result = convert(
        compression=compress,
        entity_type=entity_type.value if entity_type else None,
        fail_on_unhandled=strict_fail,
        filters=filters,
        format=format,
        limit=limit,
        output_dir=output_dir,
        paths=files,
        show_progress=progress,
        show_summary=summary,
        strict=strict,
    )
    if result:
        display_result(result)


@app.command(name="load", help="Load data dumps into a database.")
def load_cmd(
    files: Annotated[list[Path], typer.Argument(help="Discogs dump files.")],
    dsn: Annotated[
        str | None,
        typer.Option(
            "--dsn",
            help="Database connection string (PostgreSQL: postgresql://..., SQLite: path or sqlite:///...).",
        ),
    ] = None,
    limit: Annotated[int | None, typer.Option(help="Max records per file.")] = None,
    batch: Annotated[
        int, typer.Option("--batch", "-b", help="Batch size for database inserts.")
    ] = 10000,
    overwrite: Annotated[
        bool, typer.Option("--overwrite", "-w", help="Overwrite existing database.")
    ] = False,
    entity_type: Annotated[
        EntityType | None,
        typer.Option(
            "--type",
            "-t",
            case_sensitive=False,
            help="Entity type (if not auto-detected).",
        ),
    ] = None,
    drop_if: Annotated[
        list[str], typer.Option("--drop-if", help="Drop records matching field=value.")
    ] = [],
    unset: Annotated[
        list[str],
        typer.Option("--unset", help="Fields to set to null (comma-separated)."),
    ] = [],
    summary: Annotated[
        bool, typer.Option("--summary/--no-summary", help="Show summary.")
    ] = True,
    progress: Annotated[
        bool, typer.Option("--progress/--no-progress", help="Show progress bar.")
    ] = True,
    strict: Annotated[
        bool, typer.Option("--strict", help="Warn about unhandled XML elements.")
    ] = False,
    strict_fail: Annotated[
        bool,
        typer.Option(
            "--strict-fail", help="Fail on unhandled XML data (implies --strict)."
        ),
    ] = False,
) -> None:
    # --strict-fail implies --strict
    if strict_fail:
        strict = True

    valid_files = [f for f in files if f.is_file()]

    # Derive DSN from input filenames if not provided (defaults to SQLite)
    if dsn is None:
        path = build_database_path(valid_files, Path("."))
        dsn = str(path)

    # Infer database type from DSN
    database = _infer_database_type(dsn)

    # Check for existing database (only for SQLite file-based DSNs)
    if database == DatabaseType.sqlite and ":memory:" not in dsn:
        db_path = Path(dsn.replace("sqlite:///", "").replace("sqlite://", ""))
        if db_path.exists() and not overwrite:
            typer.echo(f"Database already exists: {db_path}")
            if not typer.confirm("Overwrite?"):
                raise typer.Abort()

    filters = build_filters(drop_if, unset)
    result = load(
        database,
        files,
        batch_size=batch,
        dsn=dsn,
        entity_type=entity_type.value if entity_type else None,
        fail_on_unhandled=strict_fail,
        filters=filters,
        limit=limit,
        show_progress=progress,
        show_summary=summary,
        strict=strict,
    )
    if result:
        display_result(result)


@app.command(name="sample", help="Extract a sample from a Discogs data dump.")
def sample_cmd(
    file: Annotated[Path, typer.Argument(help="Discogs dump file.")],
    count: Annotated[
        int, typer.Option("--count", "-n", help="Number of elements to extract.")
    ] = 1_000_000,
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Output file path.")
    ] = None,
    overwrite: Annotated[
        bool, typer.Option("--overwrite", "-w", help="Overwrite existing file.")
    ] = False,
    progress: Annotated[
        bool, typer.Option("--progress/--no-progress", help="Show progress bar.")
    ] = True,
) -> None:
    if not file.is_file():
        raise typer.BadParameter(f"File not found: {file}")

    # Build output path
    if output is None:
        output_path = build_sample_path(file, count)
    elif output.is_dir() or str(output).endswith("/"):
        # Treat as directory - create if needed
        output.mkdir(parents=True, exist_ok=True)
        output_path = output / build_sample_path(file, count)
    else:
        output_path = output

    # Check for existing output file
    if output_path.exists() and not overwrite:
        typer.echo(f"File already exists: {output_path}")
        if not typer.confirm("Overwrite?"):
            raise typer.Abort()

    start_time = time.perf_counter()

    # Set up progress bar
    if progress:
        with create_progress_elements() as progress_bar:
            task_id = progress_bar.add_task("Sampling", total=count)

            def on_progress() -> None:
                progress_bar.advance(task_id)

            written = sample(file, output_path, count, on_progress=on_progress)
    else:
        written = sample(file, output_path, count)

    elapsed = time.perf_counter() - start_time
    rate = written / elapsed if elapsed > 0 else 0

    summary_text = "\n".join(
        [
            f"Time:    {_format_duration(elapsed)} ({rate:,.0f} elements/sec)",
            f"Written: {written:,}",
            f"Output:  {output_path}",
        ]
    )
    _console.print(Panel(summary_text, title="Summary", border_style="green"))
