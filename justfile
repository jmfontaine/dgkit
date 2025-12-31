set quiet := true

# List available recipes
_list:
    just --list

# Build dgkit package
build:
    uv build

# Format source code
format:
    ruff format
    pyproject-fmt

# Fix fixable source code defects
fix:
    ruff check --fix
    sqlfluff fix src/dgkit/sql

# Check source code for defects
lint:
    ruff check
    sqlfluff lint src/dgkit/sql

# Run tests (optional: path or pytest args)
test *args:
    pytest --cov {{ args }}

# Type check source code
typecheck:
    ty check
