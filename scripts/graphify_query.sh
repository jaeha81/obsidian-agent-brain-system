#!/usr/bin/env bash
# Query a Graphify knowledge graph.
set -e

QUERY="$1"
GRAPH_DIR="${2:-./graphify-out}"

if [ -z "$QUERY" ]; then
  echo "Usage: ./scripts/graphify_query.sh \"query text\" [/path/to/graph]"
  exit 1
fi

echo "Querying Graphify graph..."
echo "  Query : $QUERY"
echo "  Graph : $GRAPH_DIR"

python -m graphifyy query \
  --graph "$GRAPH_DIR" \
  --query "$QUERY"
