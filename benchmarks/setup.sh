#!/bin/bash
# Setup script for benchmarking alternatives
# Run from dgkit/benchmarks directory

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ALTERNATIVES_DIR="$SCRIPT_DIR/alternatives"
mkdir -p "$ALTERNATIVES_DIR"

echo "Setting up benchmark alternatives..."
echo ""

# discogs-xml2db (Python + C#)
echo "=== discogs-xml2db (Python) ==="
if [ ! -d "$ALTERNATIVES_DIR/discogs-xml2db" ]; then
    git clone --depth 1 https://github.com/philipmat/discogs-xml2db.git "$ALTERNATIVES_DIR/discogs-xml2db"
fi
cd "$ALTERNATIVES_DIR/discogs-xml2db"
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
fi
source .venv/bin/activate
pip install -q -r requirements.txt
deactivate
echo "Done: discogs-xml2db"
echo ""

# dgtools (Go)
echo "=== dgtools (Go) ==="
if [ ! -d "$ALTERNATIVES_DIR/dgtools" ]; then
    git clone --depth 1 https://github.com/marcw/dgtools.git "$ALTERNATIVES_DIR/dgtools"
fi
cd "$ALTERNATIVES_DIR/dgtools"
if command -v go &> /dev/null; then
    go build -o dgtools .
    echo "Done: dgtools"
else
    echo "Skipped: Go not installed"
fi
echo ""

# discogs-load (Rust)
echo "=== discogs-load (Rust) ==="
if [ ! -d "$ALTERNATIVES_DIR/discogs-load" ]; then
    git clone --depth 1 https://github.com/DylanBartels/discogs-load.git "$ALTERNATIVES_DIR/discogs-load"
fi
cd "$ALTERNATIVES_DIR/discogs-load"
if command -v cargo &> /dev/null; then
    cargo build --release --quiet
    echo "Done: discogs-load"
else
    echo "Skipped: Rust not installed"
fi
echo ""

# discogs-batch (Java/Gradle)
echo "=== discogs-batch (Java) ==="
if [ ! -d "$ALTERNATIVES_DIR/discogs-batch" ]; then
    git clone --depth 1 https://github.com/echovisionlab/discogs-batch.git "$ALTERNATIVES_DIR/discogs-batch"
fi
cd "$ALTERNATIVES_DIR/discogs-batch"
if java -version &> /dev/null; then
    ./gradlew build -x test --quiet
    echo "Done: discogs-batch"
else
    echo "Skipped: Java not installed"
fi
echo ""

echo "Setup complete."
echo ""
echo "Binaries:"
echo "  discogs-xml2db: $ALTERNATIVES_DIR/discogs-xml2db/.venv/bin/python $ALTERNATIVES_DIR/discogs-xml2db/discogs2db.py"
echo "  dgtools:        $ALTERNATIVES_DIR/dgtools/dgtools"
echo "  discogs-load:   $ALTERNATIVES_DIR/discogs-load/target/release/discogs-load"
echo "  discogs-batch:  java -jar $ALTERNATIVES_DIR/discogs-batch/build/libs/discogs-batch-*.jar"
