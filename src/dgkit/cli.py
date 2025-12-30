import typer
from pathlib import Path
from typing import Annotated

from dgkit.filters import Filter, parse_drop_if, parse_unset
from dgkit.pipeline import (
    build_database_path,
    build_output_path,
    convert,
    inspect,
    load,
)
from dgkit.types import Compression, DatabaseType, FileFormat


def build_filters(drop_if: list[str], unset: list[str]) -> list[Filter]:
    """Build filter list from CLI options."""
    filters: list[Filter] = []
    filters.extend(parse_drop_if(drop_if))
    unset_filter = parse_unset(unset)
    if unset_filter:
        filters.append(unset_filter)
    return filters

app = typer.Typer(help="Discogs Toolkit")


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
):
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
    convert(format, files, limit=limit, output_dir=output_dir, compression=compress, filters=filters)


@app.command(name="load", help="Load data dumps into a database.")
def load_cmd(
    files: Annotated[list[Path], typer.Argument(help="Input files.")],
    database: Annotated[
        DatabaseType,
        typer.Option("--database", "-d", case_sensitive=False, help="Database type."),
    ],
    path: Annotated[
        Path | None, typer.Option("--path", "-p", help="Database file path.")
    ] = None,
    limit: Annotated[
        int | None, typer.Option(help="Max records per file.")
    ] = None,
    overwrite: Annotated[
        bool, typer.Option("--overwrite", "-w", help="Overwrite existing database.")
    ] = False,
    drop_if: Annotated[
        list[str], typer.Option("--drop-if", help="Drop records matching field=value.")
    ] = [],
    unset: Annotated[
        list[str], typer.Option("--unset", help="Fields to set to null (comma-separated).")
    ] = [],
):
    valid_files = [f for f in files if f.is_file()]

    # Derive database path if not provided
    if path is None:
        path = build_database_path(valid_files, Path("."))

    # Check for existing database
    if path.exists() and not overwrite:
        typer.echo(f"Database already exists: {path}")
        if not typer.confirm("Overwrite?"):
            raise typer.Abort()

    filters = build_filters(drop_if, unset)
    load(database, files, db_path=path, limit=limit, filters=filters)


@app.command(name="inspect")
def inspect_cmd():
    inspect()
