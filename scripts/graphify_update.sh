#!/usr/bin/env bash
# Incrementally update an existing Graphify knowledge graph.
set -e

PROJECT_DIR="$1"
OUTPUT_DIR="${2:-./graphify-out}"

if [ -z "$PROJECT_DIR" ]; then
  echo "Usage: ./scripts/graphify_update.sh /path/to/project [/path/to/output]"
  exit 1
fi

echo "Updating Graphify knowledge graph..."
echo "  Project : $PROJECT_DIR"
echo "  Output  : $OUTPUT_DIR"

python -m graphifyy update \
  --source "$PROJECT_DIR" \
  --output "$OUTPUT_DIR" \
  --ignore ".graphifyignore"

echo "Graph update complete."
