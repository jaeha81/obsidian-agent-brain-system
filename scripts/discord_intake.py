#!/usr/bin/env python3
"""
Discord Intake — converts Discord export/dump files into AgentBus inbox messages.

Supported input formats:
  .txt  — plain chat log (one message per line or continuous)
  .md   — markdown-formatted export
  .json — Discord JSON export (DiscordChatExporter format)

Usage:
    python scripts/discord_intake.py --file path/to/export.json --channel general
    python scripts/discord_intake.py --file path/to/chat_log.txt --channel voice-notes
"""

import argparse
import json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent.parent
VAULT = ROOT / "ObsidianVault"
INBOX = VAULT / "10_AgentBus" / "inbox"


def parse_json_export(path: Path) -> str:
    """Parse DiscordChatExporter JSON format."""
    data = json.loads(path.read_text(encoding="utf-8"))
    lines = []
    messages = data.get("messages", []) if isinstance(data, dict) else data
    for msg in messages[:100]:  # cap at 100 messages per intake
        author = msg.get("author", {}).get("name", "unknown") if isinstance(msg.get("author"), dict) else str(msg.get("author", "unknown"))
        ts = msg.get("timestamp", "")[:19].replace("T", " ")
        content = msg.get("content", "").strip()
        if content:
            lines.append(f"[{ts}] {author}: {content}")
    return "\n".join(lines)


def parse_text_export(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    # Trim to 4000 chars to keep inbox messages manageable
    if len(text) > 4000:
        text = text[:4000] + "\n\n[... truncated]"
    return text


def write_inbox_message(source_file: Path, channel: str, content: str) -> Path:
    now = datetime.now()
    ts = now.strftime("%Y%m%d_%H%M%S")
    iso = now.isoformat(timespec="seconds")

    INBOX.mkdir(parents=True, exist_ok=True)
    out_path = INBOX / f"{ts}_discord_{channel}_{source_file.stem}.md"

    message = f"""---
type: discord_intake
source_file: {source_file.name}
channel: {channel}
created: {iso}
status: pending
---

# Discord Import: #{channel}

Source: `{source_file}`

## Messages

{content}
"""
    out_path.write_text(message, encoding="utf-8")
    return out_path


def main():
    parser = argparse.ArgumentParser(description="Discord export → AgentBus inbox")
    parser.add_argument("--file", type=Path, required=True, help="Discord export file (.txt/.md/.json)")
    parser.add_argument("--channel", default="general", help="Channel name label (default: general)")
    args = parser.parse_args()

    if not args.file.exists():
        print(f"Error: file not found: {args.file}")
        return

    ext = args.file.suffix.lower()
    if ext == ".json":
        content = parse_json_export(args.file)
    else:
        content = parse_text_export(args.file)

    out_path = write_inbox_message(args.file, args.channel, content)
    print(f"Discord intake written → inbox: {out_path}")


if __name__ == "__main__":
    main()
