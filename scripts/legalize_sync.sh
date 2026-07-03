#!/usr/bin/env bash
# Sync the legalize-kr repository in external_data/.
set -e

LEGALIZE_DIR="${1:-./external_data/legalize-kr}"

if [ ! -d "$LEGALIZE_DIR/.git" ]; then
  echo "Error: legalize-kr not found at $LEGALIZE_DIR"
  echo "Run: git clone https://github.com/legalize-kr/legalize-kr.git $LEGALIZE_DIR"
  exit 1
fi

echo "Syncing legalize-kr..."
git -C "$LEGALIZE_DIR" pull --ff-only
echo "legalize-kr sync complete."
