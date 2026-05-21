#!/usr/bin/env bash
# Build a Graphify knowledge graph for a specified project folder.
# Output is always written to <PROJECT_DIR>/graphify-out/graph.json
set -e

PROJECT_DIR="$1"

if [ -z "$PROJECT_DIR" ]; then
  echo "Usage: ./scripts/graphify_build.sh /path/to/project"
  exit 1
fi

if ! python -c "import graphify" 2>/dev/null; then
  echo "Error: graphify not installed. Run: pip install graphify"
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Building Graphify knowledge graph..."
echo "  Project : $PROJECT_DIR"
echo "  Output  : $PROJECT_DIR/graphify-out/graph.json"

python -m graphify update "$PROJECT_DIR" --no-cluster

echo "Graph build complete. Output at: $PROJECT_DIR/graphify-out/"

# Auto-generate GRAPH_REPORT.md from build output
echo "Generating GRAPH_REPORT.md..."
python "$SCRIPT_DIR/graphify_post_build.py" "$PROJECT_DIR/graphify-out"
