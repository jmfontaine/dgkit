set quiet := true

default := "_list"

# List available recipes
_list:
    just --list

# Run benchmarks against alternatives
bench *args:
    python benchmarks/run.py {{ args }}

# Run benchmarks with mypyc-compiled extension
bench-compiled *args:
    #!/usr/bin/env bash
    set -e
    just compile
    python benchmarks/run.py {{ args }} || true
    just compile-clean

# Build mypyc-compiled extension
compile:
    mypyc src/dgkit/parsers.py

# Remove mypyc-compiled extension
compile-clean:
    rm -f src/dgkit/parsers*.so

# Set up benchmark
bench-setup:
    python benchmarks/setup.py

# Run all checks (lint, typecheck, test)
check:
    just lint
    just typecheck
    just test

# Remove build artifacts
clean:
    rm -rf dist/ .coverage .pytest_cache/ .ruff_cache/

# Check for outdated dependencies
deps-outdated:
    uv sync --upgrade --dry-run

# Upgrade dependencies to latest versions
deps-upgrade:
    uv sync --upgrade

# Regenerate README with cog
docs:
    cog -r README.md

# Fix fixable source code defects
fix:
    cog -r README.md            # Regenerate README.md
    ruff check --fix            # Python files
    sqlfluff fix src/dgkit/sql  # SQL files

# Format source code
format:
    ruff format                              # Python files
    pyproject-fmt pyproject.toml             # pyproject.toml
    npx markdownlint-cli2 --fix "**/*.md"    # Markdown files

# Update pre-commit hooks
hooks-update:
    pre-commit autoupdate --freeze --jobs 4

# Check source code for defects
lint:
    cog --check README.md                 # README.md is up to date
    ruff format --check                   # Python files formatting
    ruff check                            # Python files linting
    pyproject-fmt --check pyproject.toml  # pyproject.toml formatting
    sqlfluff lint src/dgkit/sql           # SQL files linting
    npx markdownlint-cli2 "**/*.md"       # Markdown files linting

# Set up development environment
setup:
    uv sync                  # Install dependencies
    pre-commit install       # Set up pre-commit git hooks
    echo "Activate with 'source .venv/bin/activate' or use 'uv run' to run commands"

# Run tests (optional: path or pytest args)
test *args:
    pytest --cov {{ args }}

# Type check source code
typecheck:
    ty check
