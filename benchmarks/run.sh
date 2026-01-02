#!/bin/bash
# Benchmark dgkit against alternatives
# Requires: hyperfine, gtime (GNU time)

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"
RESULTS_DIR="$SCRIPT_DIR/results"
SAMPLES_DIR="$REPO_DIR/samples"
XML2DB_DIR="$SCRIPT_DIR/alternatives/discogs-xml2db"

mkdir -p "$RESULTS_DIR"

# Default to releases sample (largest)
SAMPLE="${1:-$SAMPLES_DIR/discogs_20260101_releases_sample_1000000.xml.gz}"
SAMPLE_NAME="$(basename "$SAMPLE" .xml.gz)"

echo "Benchmarking: $SAMPLE_NAME"
echo ""

# Output directories
OUT_XML2DB="/tmp/bench-xml2db"
OUT_DGKIT="/tmp/bench-dgkit"

# Commands
CMD_XML2DB="$XML2DB_DIR/.venv/bin/python $XML2DB_DIR/run.py --output $OUT_XML2DB $SAMPLE"
CMD_DGKIT="uv run --directory $REPO_DIR dgkit convert $SAMPLE -f jsonl -o $OUT_DGKIT --no-progress --no-summary -w"

echo "=== Timing Comparison (hyperfine) ==="
hyperfine \
    --warmup 1 \
    --runs 3 \
    --prepare "rm -rf $OUT_XML2DB $OUT_DGKIT && mkdir -p $OUT_XML2DB $OUT_DGKIT" \
    --export-json "$RESULTS_DIR/${SAMPLE_NAME}_timing.json" \
    --command-name "discogs-xml2db" "$CMD_XML2DB" \
    --command-name "dgkit" "$CMD_DGKIT"

echo ""
echo "=== Memory Usage (single run) ==="

# discogs-xml2db
rm -rf "$OUT_XML2DB" && mkdir -p "$OUT_XML2DB"
echo "discogs-xml2db:"
gtime -v $CMD_XML2DB 2>&1 | grep -E "(wall clock|Maximum resident)"

# dgkit
rm -rf "$OUT_DGKIT" && mkdir -p "$OUT_DGKIT"
echo ""
echo "dgkit:"
gtime -v $CMD_DGKIT 2>&1 | grep -E "(wall clock|Maximum resident)"

echo ""
echo "=== Output Size ==="
echo "discogs-xml2db:"
du -sh "$OUT_XML2DB"
ls -lh "$OUT_XML2DB"

echo ""
echo "dgkit:"
du -sh "$OUT_DGKIT"
ls -lh "$OUT_DGKIT"

echo ""
echo "Results saved to: $RESULTS_DIR/${SAMPLE_NAME}_timing.json"
