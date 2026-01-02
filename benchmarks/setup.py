#!/usr/bin/env python3
"""Setup benchmark alternatives."""

import subprocess
from pathlib import Path

import typer

SCRIPT_DIR = Path(__file__).parent
ALTERNATIVES_DIR = SCRIPT_DIR / "alternatives"

TOOLS = {
    "xml2db-python": {
        "repo": "https://github.com/philipmat/discogs-xml2db.git",
        "setup": ["python3", "-m", "venv", ".venv"],
        "install": [".venv/bin/pip", "install", "-q", "-r", "requirements.txt"],
    },
    "xml2db-csharp": {
        "repo": "https://github.com/philipmat/discogs-xml2db.git",
        "check": "dotnet",
        "build": ["dotnet", "build", "-c", "Release", "--verbosity", "quiet"],
        "build_dir": "alternatives/dotnet",
    },
    "dgtools": {
        "repo": "https://github.com/marcw/dgtools.git",
        "check": "go",
        "build": ["go", "build", "-o", "dgtools", "."],
    },
    "discogs-load": {
        "repo": "https://github.com/DylanBartels/discogs-load.git",
        "check": "cargo",
        "build": ["cargo", "build", "--release", "--quiet"],
    },
    "discogs-batch": {
        "repo": "https://github.com/echovisionlab/discogs-batch.git",
        "check": "java",
        "build": ["./gradlew", "build", "-x", "test", "--quiet"],
    },
}


def run(cmd: list[str], cwd: Path | None = None) -> bool:
    """Run command, return True on success."""
    try:
        subprocess.run(cmd, cwd=cwd, check=True, capture_output=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"  Error: {e.stderr.decode()[:200]}")
        return False
    except FileNotFoundError:
        return False


def command_exists(cmd: str) -> bool:
    """Check if command exists."""
    try:
        subprocess.run(["which", cmd], check=True, capture_output=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def setup_tool(name: str, config: dict) -> bool:
    """Setup a single tool."""
    print(f"=== {name} ===")
    tool_dir = ALTERNATIVES_DIR / name

    # Clone if needed
    if not tool_dir.exists():
        print(f"  Cloning {config['repo']}...")
        if not run(["git", "clone", "--depth", "1", config["repo"], str(tool_dir)]):
            print("  Failed to clone")
            return False

    # Check for required tool
    if "check" in config and not command_exists(config["check"]):
        print(f"  Skipped: {config['check']} not installed")
        return False

    # Determine working directory
    work_dir = tool_dir
    if "build_dir" in config:
        work_dir = tool_dir / config["build_dir"]

    # Run setup commands
    if "setup" in config:
        print("  Setting up...")
        run(config["setup"], cwd=work_dir)

    if "install" in config:
        print("  Installing dependencies...")
        if not run(config["install"], cwd=work_dir):
            print("  Failed to install")
            return False

    if "build" in config:
        print("  Building...")
        if not run(config["build"], cwd=work_dir):
            print("  Failed to build")
            return False

    print("  Done")
    return True


def main() -> None:
    """Setup all benchmark alternatives."""
    ALTERNATIVES_DIR.mkdir(parents=True, exist_ok=True)

    typer.echo("Setting up benchmark alternatives...\n")

    results = {}
    for name, config in TOOLS.items():
        results[name] = setup_tool(name, config)
        typer.echo()

    # Print summary
    typer.echo("Summary:")
    for name, success in results.items():
        status = "OK" if success else "SKIPPED"
        typer.echo(f"  {name}: {status}")


if __name__ == "__main__":
    typer.run(main)
