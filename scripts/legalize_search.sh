#!/usr/bin/env bash
# Search legalize-kr for a legal term or article.
set -e

QUERY="$1"
LEGALIZE_DIR="${2:-./external_data/legalize-kr}"

if [ -z "$QUERY" ]; then
  echo "Usage: ./scripts/legalize_search.sh \"검색어\" [/path/to/legalize-kr]"
  exit 1
fi

if [ ! -d "$LEGALIZE_DIR" ]; then
  echo "Error: legalize-kr not found at $LEGALIZE_DIR"
  exit 1
fi

echo "Searching legalize-kr for: $QUERY"
grep -r "$QUERY" "$LEGALIZE_DIR" --include="*.json" --include="*.md" -l 2>/dev/null | head -20
