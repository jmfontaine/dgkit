set quiet := true

# List available recipes
_list:
    just --list

# Build dgkit package
build:
    uv build
