import typer
from pathlib import Path
from typing import Annotated

from dgkit.pipeline import (
    build_database_path,
    build_output_path,
    convert,
    inspect,
)
from dgkit.types import Compression, Format
from dgkit.writers import WRITERS

app = typer.Typer(help="Discogs Toolkit")


@app.command(name="convert", help="Convert data dumps to another format.")
def convert_cmd(
    format: Annotated[
        Format, typer.Argument(case_sensitive=False, help="Output file format.")
    ],
    files: Annotated[list[Path], typer.Argument(help="Input files.")],
    limit: Annotated[
        int | None, typer.Option(help="Max records per file.")
    ] = None,
    output_dir: Annotated[
        Path, typer.Option("--output-dir", "-o", help="Output directory.")
    ] = Path("."),
    compress: Annotated[
        Compression, typer.Option("--compress", "-c", case_sensitive=False, help="Compression algorithm.")
    ] = Compression.none,
    force: Annotated[
        bool, typer.Option("--force", "-f", help="Overwrite existing files.")
    ] = False,
):
    # Check for existing output files (only for file-based formats)
    if format not in (Format.console, Format.blackhole) and not force:
        valid_files = [f for f in files if f.is_file()]
        writer_cls = WRITERS[format]
        if writer_cls.aggregates_inputs:
            db_path = build_database_path(valid_files, output_dir)
            existing = [db_path] if db_path.exists() else []
        else:
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

    convert(format, files, limit=limit, output_dir=output_dir, compression=compress)


@app.command(name="inspect")
def inspect_cmd():
    inspect()
