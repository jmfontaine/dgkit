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

# Run all tests
test:
    pytest --cov    

# Run integration tests
test-integration:
    pytest tests/integration    

# Run unit tests
test-unit:
    pytest tests/unit
