#!/usr/bin/env python3
"""
Voice Intake — moves audio/transcript files from RAW_IMPORT/Voice/ into AgentBus inbox.

Supported input types:
  .txt / .md  — treated as raw transcript, written directly as inbox message
  .wav / .mp3 / .m4a / .ogg — Whisper로 자동 전사 후 inbox 저장
                               (openai-whisper 미설치 시 수동 전사 대기로 fallback)

Usage:
    python scripts/voice_intake.py --file path/to/audio_or_transcript.txt
    python scripts/voice_intake.py --file audio.mp3 --model small --language ko
    python scripts/voice_intake.py --dir RAW/Voice/
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent.parent
VAULT = ROOT / "ObsidianVault"
INBOX = VAULT / "10_AgentBus" / "inbox"
AUDIO_EXTS = {".wav", ".mp3", ".m4a", ".ogg", ".flac"}
TEXT_EXTS = {".txt", ".md"}


def write_inbox_message(
    source_file: Path,
    content: str,
    is_transcript: bool,
    whisper_model: str = "N/A",
) -> Path:
    now = datetime.now()
    ts = now.strftime("%Y%m%d_%H%M%S")
    iso = now.isoformat(timespec="seconds")

    INBOX.mkdir(parents=True, exist_ok=True)
    out_path = INBOX / f"{ts}_voice_{source_file.stem}.md"

    if is_transcript:
        msg_type = "voice_transcript"
        transcription_line = f"transcription_model: {whisper_model}\n" if whisper_model != "N/A" else ""
        body = content
    else:
        msg_type = "voice_pending_transcription"
        transcription_line = ""
        body = (
            f"오디오 파일 수신 — 수동 전사 필요.\n\n"
            f"Source: `{source_file.name}`\n\n"
            f"자동 전사 방법: `python scripts/whisper_transcribe.py {source_file.name}`"
        )

    message = f"""---
type: {msg_type}
source_file: {source_file.name}
created: {iso}
{transcription_line}status: pending
---

# Voice Input: {source_file.stem}

{body}
"""
    out_path.write_text(message, encoding="utf-8")
    return out_path


def process_file(path: Path, whisper_model: str = "base", language: str = "ko") -> None:
    ext = path.suffix.lower()
    if ext in TEXT_EXTS:
        content = path.read_text(encoding="utf-8")
        out = write_inbox_message(path, content, is_transcript=True)
        print(f"Transcript → inbox: {out}")
    elif ext in AUDIO_EXTS:
        # Whisper 자동 전사 시도
        try:
            sys.path.insert(0, str(ROOT))
            from scripts.whisper_transcribe import transcribe  # type: ignore
            text = transcribe(path, model_name=whisper_model, language=language)
        except Exception as e:
            print(f"Warning: Whisper 호출 실패 ({e}) — 수동 전사 대기로 fallback")
            text = None

        if text:
            out = write_inbox_message(path, text, is_transcript=True, whisper_model=whisper_model)
            print(f"Whisper 전사 완료 → inbox: {out}")
        else:
            out = write_inbox_message(path, "", is_transcript=False)
            print(f"수동 전사 대기 → inbox: {out}")
    else:
        print(f"Skipped (unsupported ext): {path}")


def main():
    parser = argparse.ArgumentParser(description="Voice file intake → AgentBus inbox")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--file", type=Path, help="처리할 단일 파일")
    group.add_argument("--dir", type=Path, help="스캔할 디렉토리 (오디오/전사 파일)")
    parser.add_argument("--model", default="base", help="Whisper 모델 크기 (기본: base)")
    parser.add_argument("--language", default="ko", help="전사 언어 (기본: ko)")
    args = parser.parse_args()

    if args.file:
        if not args.file.exists():
            print(f"Error: 파일 없음 — {args.file}")
            return
        process_file(args.file, whisper_model=args.model, language=args.language)
    else:
        if not args.dir.exists():
            print(f"Error: 디렉토리 없음 — {args.dir}")
            return
        files = [f for f in args.dir.iterdir() if f.is_file() and f.suffix.lower() in AUDIO_EXTS | TEXT_EXTS]
        if not files:
            print(f"No supported files found in {args.dir}")
            return
        for f in sorted(files):
            process_file(f, whisper_model=args.model, language=args.language)
        print(f"Processed {len(files)} file(s).")


if __name__ == "__main__":
    main()
