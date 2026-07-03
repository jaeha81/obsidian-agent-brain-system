#!/usr/bin/env bash
set -e

SOURCE_DIR="./vault_scaffold"
TARGET_DIR="$1"

if [ -z "$TARGET_DIR" ]; then
  echo "Usage: ./scripts/init_vault_scaffold.sh /path/to/ObsidianVault"
  exit 1
fi

if [ ! -d "$SOURCE_DIR" ]; then
  echo "Error: Source vault_scaffold not found at $SOURCE_DIR"
  exit 1
fi

echo "Initializing vault scaffold..."
echo "  Source : $SOURCE_DIR"
echo "  Target : $TARGET_DIR"
echo ""

mkdir -p "$TARGET_DIR"

# rsync: copy only if destination file does not exist
rsync -av --ignore-existing "$SOURCE_DIR/" "$TARGET_DIR/"

echo ""
echo "Vault scaffold initialized at: $TARGET_DIR"
echo "Open this folder as Obsidian Vault."
