#!/usr/bin/env bash
# Manual sync script for cases where Google Drive auto-sync is not available.
set -e

VAULT_DIR="$1"
DRIVE_DIR="$2"

if [ -z "$VAULT_DIR" ] || [ -z "$DRIVE_DIR" ]; then
  echo "Usage: ./scripts/sync_to_drive.sh /local/ObsidianVault /drive/obsidian-agent-brain-system"
  exit 1
fi

echo "Syncing Vault to Google Drive..."
echo "  Source : $VAULT_DIR"
echo "  Target : $DRIVE_DIR/ObsidianVault"

rsync -av --exclude='.smart-env/' --exclude='.trash/' \
  "$VAULT_DIR/" "$DRIVE_DIR/ObsidianVault/"

echo "Sync complete."
