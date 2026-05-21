#!/usr/bin/env bash
# Build a Graphify knowledge graph for a specified project folder.
set -e

PROJECT_DIR="$1"
OUTPUT_DIR="${2:-./graphify-out}"

if [ -z "$PROJECT_DIR" ]; then
  echo "Usage: ./scripts/graphify_build.sh /path/to/project [/path/to/output]"
  exit 1
fi

if ! python -c "import graphifyy" 2>/dev/null; then
  echo "Error: graphifyy not installed. Run: pip install graphifyy"
  exit 1
fi

echo "Building Graphify knowledge graph..."
echo "  Project : $PROJECT_DIR"
echo "  Output  : $OUTPUT_DIR"

mkdir -p "$OUTPUT_DIR"

python -m graphifyy build \
  --source "$PROJECT_DIR" \
  --output "$OUTPUT_DIR" \
  --ignore ".graphifyignore"

echo "Graph build complete. Output at: $OUTPUT_DIR"
