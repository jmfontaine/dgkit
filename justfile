set quiet := true

# List available recipes
_list:
    just --list

# Build dgkit package
build:
    uv build

# Run all tests
test:
    pytest --cov    

# Run integration tests
test-integration:
    pytest tests/integration    

# Run unit tests
test-unit:
    pytest tests/unit
