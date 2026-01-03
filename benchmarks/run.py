#!/usr/bin/env python3
"""Benchmark dgkit against alternatives."""

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Annotated, Any

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


def _get_time_cmd() -> list[str]:
    """Get the GNU time command for the current platform."""
    if sys.platform == "darwin":
        return ["gtime", "-v"]
    return ["/usr/bin/time", "-v"]


def _parse_wall_clock(wall_clock: str) -> float:
    """Parse wall clock time string to seconds.

    Formats: "0:01.23" (m:ss.xx), "1:23:45" (h:mm:ss), "1:23.45" (m:ss.xx)
    """
    parts = wall_clock.split(":")
    if len(parts) == 2:
        minutes, seconds = parts
        return int(minutes) * 60 + float(seconds)
    elif len(parts) == 3:
        hours, minutes, seconds = parts
        return int(hours) * 3600 + int(minutes) * 60 + float(seconds)
    return 0.0


SCRIPT_DIR = Path(__file__).parent
REPO_DIR = SCRIPT_DIR.parent
RESULTS_DIR = SCRIPT_DIR / "results"
ALTERNATIVES_DIR = SCRIPT_DIR / "alternatives"


def _dgkit_cmd(sample: Path, out: Path) -> list[str]:
    return [
        "uv",
        "run",
        "--directory",
        str(REPO_DIR),
        "dgkit",
        "convert",
        str(sample),
        "-f",
        "jsonl",
        "-o",
        str(out),
        "--no-progress",
        "--no-summary",
    ]


def _dgkit_cython_setup() -> None:
    """Compile parsers.py with Cython."""
    subprocess.run(
        [
            "uv",
            "run",
            "--directory",
            str(REPO_DIR),
            "cythonize",
            "-i",
            "src/dgkit/parsers.py",
        ],
        capture_output=True,
        check=True,
    )


def _dgkit_cython_teardown() -> None:
    """Remove Cython-compiled files."""
    for pattern in ["src/dgkit/parsers*.so", "src/dgkit/parsers.c"]:
        for f in REPO_DIR.glob(pattern.replace("src/dgkit/", "src/dgkit/")):
            f.unlink(missing_ok=True)


def _xml2db_python_cmd(sample: Path, out: Path) -> list[str]:
    return [
        str(ALTERNATIVES_DIR / "xml2db-python/.venv/bin/python"),
        str(ALTERNATIVES_DIR / "xml2db-python/run.py"),
        "--output",
        str(out),
        str(sample),
    ]


TOOLS: dict[str, Any] = {
    "dgkit": {"cmd": _dgkit_cmd, "needs_output": True},
    "dgkit-cython": {
        "cmd": _dgkit_cmd,
        "needs_output": True,
        "setup": _dgkit_cython_setup,
        "teardown": _dgkit_cython_teardown,
    },
    "xml2db-python": {"cmd": _xml2db_python_cmd, "needs_output": True},
}


def run_benchmark(sample: Path, tool: str) -> dict[str, Any] | None:
    """Run a single benchmark with gtime to capture timing and memory."""
    config = TOOLS[tool]

    # Run setup if defined
    if setup := config.get("setup"):
        with console.status(f"[bold blue]Setting up {tool}..."):
            try:
                setup()
            except subprocess.CalledProcessError:
                console.print(f"[red]Error:[/red] {tool} setup failed")
                return None

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            out_dir = tmpdir / "output"
            out_dir.mkdir()

            # Handle sample copying for C#
            if config.get("copy_sample"):
                tool_sample = out_dir / sample.name
                shutil.copy(sample, tool_sample)
            else:
                tool_sample = sample

            tool_cmd = config["cmd"](tool_sample, out_dir)

            try:
                with console.status(f"[bold green]Running {tool}..."):
                    result = subprocess.run(
                        _get_time_cmd() + tool_cmd,
                        capture_output=True,
                        text=True,
                    )
            except FileNotFoundError:
                if sys.platform == "darwin":
                    console.print(
                        "[red]Error:[/red] gtime not found. "
                        "Install with: [cyan]brew install gnu-time[/cyan]"
                    )
                else:
                    console.print(
                        "[red]Error:[/red] /usr/bin/time not found. "
                        "Install with: [cyan]apt install time[/cyan]"
                    )
                return None

            # Check for command failure
            if result.returncode != 0:
                console.print(
                    f"[red]Error:[/red] {tool} failed (exit {result.returncode})"
                )
                if result.stderr:
                    # Show first line of error (skip gtime stats)
                    for line in result.stderr.split("\n"):
                        if not line.strip().startswith(
                            (
                                "Command",
                                "User",
                                "System",
                                "Percent",
                                "Elapsed",
                                "Maximum",
                                "Average",
                                "Major",
                                "Minor",
                                "Voluntary",
                                "Involuntary",
                                "Swaps",
                                "File",
                                "Socket",
                                "Signals",
                                "Page",
                                "Exit",
                            )
                        ):
                            if line.strip():
                                console.print(f"  {line.strip()}")
                                break
                return None

            # Parse gtime output
            stderr = result.stderr
            stats: dict[str, Any] = {"exit_code": result.returncode}
            for line in stderr.split("\n"):
                if "wall clock" in line:
                    stats["wall_clock"] = line.split(": ")[1].strip()
                elif "Maximum resident" in line:
                    kb = int(line.split(": ")[1].strip())
                    stats["max_rss_mb"] = kb / 1024
                elif "User time" in line:
                    stats["user_time"] = float(line.split(": ")[1].strip())
                elif "System time" in line:
                    stats["system_time"] = float(line.split(": ")[1].strip())
            return stats
    finally:
        # Run teardown if defined
        if teardown := config.get("teardown"):
            teardown()


app = typer.Typer(help="Benchmark dgkit against alternatives.")


@app.command()
def main(
    input_file: Annotated[
        Path,
        typer.Option("--input", "-i", help="Path to Discogs dump file.", exists=True),
    ],
    tools: Annotated[
        list[str] | None,
        typer.Argument(help=f"Tools to benchmark. Choices: {', '.join(TOOLS.keys())}"),
    ] = None,
) -> None:
    """Run benchmarks against alternative tools."""
    # Validate tools
    tool_list = tools or list(TOOLS.keys())
    for tool in tool_list:
        if tool not in TOOLS:
            raise typer.BadParameter(
                f"Unknown tool: {tool}. Available: {', '.join(TOOLS.keys())}"
            )

    console.print(
        Panel(f"[bold]{input_file.name}[/bold]\nTools: {', '.join(tool_list)}")
    )

    # Run benchmarks and collect results
    results: dict[str, dict[str, Any]] = {}
    for tool in tool_list:
        stats = run_benchmark(input_file, tool)
        if stats:
            results[tool] = stats

    # Skip table if no results
    if not results:
        return

    # Get baseline time if dgkit was run
    baseline_seconds: float | None = None
    if "dgkit" in results and results["dgkit"].get("wall_clock"):
        baseline_seconds = _parse_wall_clock(results["dgkit"]["wall_clock"])

    # Build results table
    table = Table(show_header=True, header_style="bold")
    table.add_column("Tool")
    table.add_column("Wall Clock", justify="right")
    if baseline_seconds:
        table.add_column("Comparison", justify="right")
    table.add_column("User", justify="right")
    table.add_column("System", justify="right")
    table.add_column("Max RSS (MB)", justify="right")

    for tool in tool_list:
        if tool not in results:
            continue
        stats = results[tool]
        row = [
            tool,
            stats.get("wall_clock", "N/A"),
        ]
        if baseline_seconds:
            if tool == "dgkit":
                row.append("baseline")
            else:
                tool_seconds = _parse_wall_clock(stats.get("wall_clock", "0:00"))
                ratio = tool_seconds / baseline_seconds if baseline_seconds > 0 else 0
                row.append(f"{ratio:.2f}x")
        row.extend(
            [
                f"{stats.get('user_time', 0):.2f}s",
                f"{stats.get('system_time', 0):.2f}s",
                f"{stats.get('max_rss_mb', 0):.1f}",
            ]
        )
        table.add_row(*row)

    console.print(table)


if __name__ == "__main__":
    app()
