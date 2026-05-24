#!/usr/bin/env python3
"""One-shot Bucky chat bridge for the Obsidian plugin."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).parent.parent
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from bucky_client import BuckyError, run_bucky  # noqa: E402


SYSTEM_PROMPT = """# Bucky Obsidian Chat

You are Bucky, the user's Obsidian-installed local agent.
You are running through the Claude CLI subscription route.
Answer in Korean when the user writes Korean.
Keep the answer practical and directly useful.
When the user asks you to act on local files, explain what you can do and what evidence you need.

IMPORTANT: Do NOT output PC environment detection messages (집 PC, 노트북, 사무실 PC, 기본 경로 등).
Answer directly without any preamble or environment info. Start with the actual answer.
"""


def read_prompt(args: argparse.Namespace) -> str:
    if args.prompt_file:
        return Path(args.prompt_file).read_text(encoding="utf-8-sig")
    if args.prompt:
        return args.prompt
    return sys.stdin.read()


def main() -> int:
    parser = argparse.ArgumentParser(description="Run one Bucky chat turn.")
    parser.add_argument("--prompt", default="", help="Prompt text. If omitted, stdin is used.")
    parser.add_argument("--prompt-file", default="", help="UTF-8 prompt file path.")
    parser.add_argument("--timeout", type=int, default=900, help="Timeout seconds.")
    args = parser.parse_args()

    user_prompt = read_prompt(args).strip()
    if not user_prompt:
        print("No prompt supplied.", file=sys.stderr)
        return 2

    prompt = f"{SYSTEM_PROMPT}\n\n## User Message\n\n{user_prompt}"
    try:
        print(run_bucky(prompt, timeout=args.timeout))
        return 0
    except BuckyError as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
