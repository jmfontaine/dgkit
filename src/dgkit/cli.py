import typer
from pathlib import Path
from typing import Annotated

from dgkit.core import Format, convert, inspect

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
):
    convert(format, files, limit=limit)


@app.command(name="inspect")
def inspect_cmd():
    inspect()
