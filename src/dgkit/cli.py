import typer
from pathlib import Path
from typing import Annotated

from dgkit.core import Format, build_output_path, convert, inspect

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
    force: Annotated[
        bool, typer.Option("--force", "-f", help="Overwrite existing files.")
    ] = False,
):
    # Check for existing output files (only for file-based formats)
    if format not in (Format.console, Format.blackhole) and not force:
        existing = [
            build_output_path(f, format, output_dir)
            for f in files
            if f.is_file() and build_output_path(f, format, output_dir).exists()
        ]
        if existing:
            typer.echo("The following files already exist:")
            for path in existing:
                typer.echo(f"  {path}")
            if not typer.confirm("Overwrite?"):
                raise typer.Abort()

    convert(format, files, limit=limit, output_dir=output_dir)


@app.command(name="inspect")
def inspect_cmd():
    inspect()
