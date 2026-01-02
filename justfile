set quiet := true

default := "_list"

# List available recipes
_list:
    just --list

# Run all checks (lint, typecheck, test)
check:
    just lint
    just typecheck
    just test

# Remove build artifacts
clean:
    rm -rf dist/ .coverage .pytest_cache/ .ruff_cache/

# Regenerate README with cog
docs:
    uv run cog -r README.md

# Format source code
format:
    ruff format                              # Python files
    pyproject-fmt pyproject.toml             # pyproject.toml
    npx markdownlint-cli2 --fix "**/*.md"    # Markdown files

# Fix fixable source code defects
fix:
    ruff check --fix            # Python files
    sqlfluff fix src/dgkit/sql  # SQL files

# Check source code for defects
lint:
    ruff format --check                   # Python files formatting
    ruff check                            # Python files linting
    pyproject-fmt --check pyproject.toml  # pyproject.toml formatting
    sqlfluff lint src/dgkit/sql           # SQL files linting
    npx markdownlint-cli2 "**/*.md"       # Markdown files linting

# Run tests (optional: path or pytest args)
test *args:
    pytest --cov {{ args }}

# Set up development environment
setup:
    uv sync                  # Install dependencies
    pre-commit install       # Set up pre-commit git hooks
    echo "Activate with 'source .venv/bin/activate' or use 'uv run' to run commands"

# Type check source code
typecheck:
    ty check

# Update pre-commit hooks
update:
    pre-commit autoupdate
