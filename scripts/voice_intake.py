#!/usr/bin/env python3
"""
Voice Intake — moves audio/transcript files from RAW_IMPORT/Voice/ into AgentBus inbox.

Supported input types:
  .txt / .md  — treated as raw transcript, written directly as inbox message
  .wav / .mp3 / .m4a / .ogg — placeholder: logs file path for manual transcription

Usage:
    python scripts/voice_intake.py --file path/to/audio_or_transcript.txt
    python scripts/voice_intake.py --dir RAW/Voice/  # process all files in directory
"""

import argparse
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent.parent
VAULT = ROOT / "ObsidianVault"
INBOX = VAULT / "10_AgentBus" / "inbox"
AUDIO_EXTS = {".wav", ".mp3", ".m4a", ".ogg", ".flac"}
TEXT_EXTS = {".txt", ".md"}


def write_inbox_message(source_file: Path, content: str, is_transcript: bool) -> Path:
    now = datetime.now()
    ts = now.strftime("%Y%m%d_%H%M%S")
    iso = now.isoformat(timespec="seconds")

    INBOX.mkdir(parents=True, exist_ok=True)
    out_path = INBOX / f"{ts}_voice_{source_file.stem}.md"

    msg_type = "voice_transcript" if is_transcript else "voice_pending_transcription"
    body = content if is_transcript else f"Audio file received. Manual transcription required.\n\nSource: `{source_file}`"

    message = f"""---
type: {msg_type}
source_file: {source_file.name}
created: {iso}
status: pending
---

# Voice Input: {source_file.stem}

{body}
"""
    out_path.write_text(message, encoding="utf-8")
    return out_path


def process_file(path: Path) -> None:
    ext = path.suffix.lower()
    if ext in TEXT_EXTS:
        content = path.read_text(encoding="utf-8")
        out = write_inbox_message(path, content, is_transcript=True)
        print(f"Transcript → inbox: {out}")
    elif ext in AUDIO_EXTS:
        out = write_inbox_message(path, "", is_transcript=False)
        print(f"Audio queued → inbox: {out}")
    else:
        print(f"Skipped (unsupported ext): {path}")


def main():
    parser = argparse.ArgumentParser(description="Voice file intake → AgentBus inbox")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--file", type=Path, help="Single file to process")
    group.add_argument("--dir", type=Path, help="Directory to scan for audio/transcript files")
    args = parser.parse_args()

    if args.file:
        if not args.file.exists():
            print(f"Error: file not found: {args.file}")
            return
        process_file(args.file)
    else:
        if not args.dir.exists():
            print(f"Error: directory not found: {args.dir}")
            return
        files = [f for f in args.dir.iterdir() if f.is_file() and f.suffix.lower() in AUDIO_EXTS | TEXT_EXTS]
        if not files:
            print(f"No supported files found in {args.dir}")
            return
        for f in sorted(files):
            process_file(f)
        print(f"Processed {len(files)} file(s).")


if __name__ == "__main__":
    main()
