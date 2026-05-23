#!/usr/bin/env python3
"""Watch Bucky AgentBus review requests and run Codex CLI reviews."""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import tempfile
import time
from datetime import datetime
from pathlib import Path

import yaml
from dotenv import load_dotenv
from harness_router import build_codex_review_context, is_harness_router_enabled


ROOT = Path(__file__).parent.parent
load_dotenv(ROOT / ".env", encoding="utf-8", override=True)

VAULT = Path(os.getenv("VAULT_PATH", str(ROOT / "ObsidianVault")))
WORKER_NAME = os.getenv("AGENTBUS_WORKER_NAME", "Bucky")
SOURCE_DIR = VAULT / "10_AgentBus" / "outbox" / WORKER_NAME
CODEX_OUTBOX = VAULT / "10_AgentBus" / "outbox" / "Codex"
COMPLETED_DIR = VAULT / "10_AgentBus" / "completed"
FAILED_DIR = VAULT / "10_AgentBus" / "failed"
PROMPT_FILE = ROOT / "prompts" / "codex_worker_prompt.md"

_FM_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)


def iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def ts() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def parse_frontmatter(text: str) -> tuple[dict, str]:
    match = _FM_RE.match(text)
    if not match:
        return {}, text
    try:
        return yaml.safe_load(match.group(1)) or {}, text[match.end():]
    except yaml.YAMLError:
        return {}, text


def update_frontmatter(path: Path, updates: dict) -> None:
    content = path.read_text(encoding="utf-8-sig")
    fm, body = parse_frontmatter(content)
    fm.update(updates)
    path.write_text(
        f"---\n{yaml.dump(fm, allow_unicode=True, default_flow_style=False)}---\n{body}",
        encoding="utf-8",
    )


def codex_command() -> str:
    command = os.getenv("CODEX_COMMAND", "codex").strip() or "codex"
    if any(sep in command for sep in ("\\", "/", ":")):
        return command
    return shutil.which(command) or command


def build_prompt(request_path: Path, request_body: str) -> str:
    instructions = PROMPT_FILE.read_text(encoding="utf-8") if PROMPT_FILE.exists() else ""
    jh_context = load_jh_role_context()
    harness_context = build_codex_review_context(request_body) if is_harness_router_enabled() else ""
    return (
        "# AgentBus Codex review request\n\n"
        "You are running as the Codex subscription reviewer for the local Obsidian Agent Brain System.\n"
        "Review only. Do not modify files. Write a concise, actionable review.\n\n"
        "## JH shared role and governance context\n"
        f"{jh_context}\n\n"
        "## Harness framework review context\n"
        f"{harness_context or 'Harness router disabled or no Harness signals detected.'}\n\n"
        "## Codex worker instructions\n"
        f"{instructions}\n\n"
        "## Request file\n"
        f"{request_path}\n\n"
        "## Request content\n"
        f"{request_body.strip()}\n"
    )


def read_optional(path: Path, max_chars: int = 6000) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace").strip()[:max_chars]


def load_jh_role_context() -> str:
    shared = Path(os.getenv("JH_SHARED_PATH", "G:/내 드라이브/JH-SHARED"))
    room = Path(os.getenv("JH_AGENT_ROOM_PATH", "G:/내 드라이브/JH-Agent-Room"))
    parts = []
    for rel in (
        "00_SYSTEM/roles.md",
        "00_SYSTEM/agent-onboarding.md",
        "05_TASK_LOCKS/README.md",
        "04_DAILY_REPORTS/README.md",
    ):
        content = read_optional(shared / rel)
        if content:
            parts.append(f"### JH-SHARED/{rel}\n{content}")
    room_readme = read_optional(room / "README.md")
    if room_readme:
        parts.append(f"### JH-Agent-Room/README.md\n{room_readme}")
    return "\n\n---\n\n".join(parts) or "JH shared context not found."


def run_codex(prompt: str, output_path: Path) -> None:
    timeout_s = int(os.getenv("CODEX_TIMEOUT", "900"))
    sandbox = os.getenv("CODEX_SANDBOX", "read-only").strip() or "read-only"
    command = [
        codex_command(),
        "exec",
        "-C",
        str(ROOT),
        "--sandbox",
        sandbox,
        "--output-last-message",
        str(output_path),
        "-",
    ]
    model = os.getenv("CODEX_MODEL", "").strip()
    if model:
        command[2:2] = ["--model", model]

    result = subprocess.run(
        command,
        input=prompt,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=str(ROOT),
        timeout=timeout_s,
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()
        raise RuntimeError(f"Codex CLI failed with code {result.returncode}: {detail}")


def process_request(path: Path, *, dry_run: bool = False) -> Path | None:
    content = path.read_text(encoding="utf-8-sig")
    fm, body = parse_frontmatter(content)
    if fm.get("status") != "pending" or fm.get("to") != "Codex":
        return None

    task_id = str(fm.get("task_id") or path.stem)
    CODEX_OUTBOX.mkdir(parents=True, exist_ok=True)
    output_path = CODEX_OUTBOX / f"{ts()}_{task_id}_review.md"

    if dry_run:
        print(f"DRY RUN: would review {path.name} -> {output_path.name}")
        return output_path

    update_frontmatter(path, {"status": "processing", "codex_started": iso()})
    prompt = build_prompt(path, body)
    try:
        with tempfile.NamedTemporaryFile("w", delete=False, encoding="utf-8", suffix=".md") as tmp:
            temp_output = Path(tmp.name)
        run_codex(prompt, temp_output)
        review = temp_output.read_text(encoding="utf-8", errors="replace").strip()
        output_path.write_text(
            f"---\ntype: codex_review\ntask_id: {task_id}\nsource: {path.name}\n"
            f"reviewer: Codex\ncreated: {iso()}\n---\n\n{review}\n",
            encoding="utf-8",
        )
        update_frontmatter(path, {
            "status": "done",
            "reviewed_by": "CodexCLI",
            "reviewed_at": iso(),
            "output": str(output_path),
        })
        COMPLETED_DIR.mkdir(parents=True, exist_ok=True)
        path.rename(COMPLETED_DIR / path.name)
        temp_output.unlink(missing_ok=True)
        return output_path
    except Exception as exc:
        update_frontmatter(path, {
            "status": "failed",
            "review_error": str(exc)[:500],
            "reviewed_at": iso(),
        })
        FAILED_DIR.mkdir(parents=True, exist_ok=True)
        path.rename(FAILED_DIR / path.name)
        raise


def run_once(*, dry_run: bool = False) -> int:
    count = 0
    for path in sorted(SOURCE_DIR.glob("*.md")):
        result = process_request(path, dry_run=dry_run)
        if result:
            print(f"Codex review {'planned' if dry_run else 'written'}: {result}")
            count += 1
    return count


def watch(*, dry_run: bool = False) -> None:
    interval = int(os.getenv("CODEX_REVIEW_INTERVAL", "10"))
    print(f"[CodexReviewRunner] Watching: {SOURCE_DIR}")
    print(f"  command={codex_command()}  interval={interval}s")
    while True:
        run_once(dry_run=dry_run)
        time.sleep(interval)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Codex CLI reviews for AgentBus requests")
    parser.add_argument("--once", action="store_true", help="Process pending requests once and exit")
    parser.add_argument("--dry-run", action="store_true", help="Show pending work without running Codex")
    args = parser.parse_args()

    if os.getenv("CODEX_REVIEW_ENABLED", "1").strip().lower() in {"0", "false", "no"}:
        print("CODEX_REVIEW_ENABLED=0; exiting.")
        return

    if args.once:
        run_once(dry_run=args.dry_run)
    else:
        watch(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
