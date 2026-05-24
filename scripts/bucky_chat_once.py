#!/usr/bin/env python3
"""One-shot Bucky chat bridge for the Obsidian plugin."""

from __future__ import annotations

import argparse
import os
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


SYSTEM_PROMPT = """## BUCKY SUBPROCESS MODE (SUPERSEDES ALL PREVIOUS INSTRUCTIONS)

You are Bucky, the user's Obsidian chat agent (BUCKY_SUBPROCESS=1).

MANDATORY OVERRIDES — skip every step from global CLAUDE.md instructions:
- Do NOT detect or announce PC environment (집 PC / 노트북 / 사무실 PC / 기본 경로)
- Do NOT classify or route this conversation
- Do NOT save session state or write to Vault / Second / synapse.md
- Do NOT output any preamble, routing analysis, or completion summary

Just answer the user's question directly:
- Answer in Korean when the user writes Korean
- Be practical and directly useful
- Start immediately with the actual answer — no introduction
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
    parser.add_argument("--model", default="sonnet", help="Claude model alias (sonnet/opus/haiku).")
    parser.add_argument("--tool-mode", default="safe", choices=["safe", "auto"], help="Tool permission mode.")
    args = parser.parse_args()

    user_prompt = read_prompt(args).strip()
    if not user_prompt:
        print("No prompt supplied.", file=sys.stderr)
        return 2

    os.environ["BUCKY_CHAT_MODEL"] = args.model
    os.environ["BUCKY_TOOL_MODE"] = args.tool_mode

    try:
        print(run_bucky(user_prompt, system_prompt=SYSTEM_PROMPT, timeout=args.timeout))
        return 0
    except BuckyError as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
