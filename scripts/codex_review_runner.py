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
load_dotenv(ROOT / ".env", encoding="utf-8-sig", override=True)

VAULT = Path(os.getenv("VAULT_PATH", str(ROOT / "ObsidianVault")))
WORKER_NAME = os.getenv("AGENTBUS_WORKER_NAME", "Bucky")
SOURCE_DIR = VAULT / "10_AgentBus" / "outbox" / WORKER_NAME
CODEX_OUTBOX = VAULT / "10_AgentBus" / "outbox" / "Codex"
COMPLETED_DIR = VAULT / "10_AgentBus" / "completed"
FAILED_DIR = VAULT / "10_AgentBus" / "failed"
PROMPT_FILE = ROOT / "prompts" / "codex_worker_prompt.md"
HANDOFF_DIR = VAULT / "10_AgentBus" / "handoffs" / "Codex"

_FM_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)
_CONTEXT_FAILURE_RE = re.compile(
    r"context|token|too large|maximum context|context length",
    re.IGNORECASE,
)


def env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


MAX_PROMPT_CHARS = env_int("CODEX_MAX_PROMPT_CHARS", 24_000)


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
        "## Codex context policy\n"
        "- Proactive context warnings are a standing user requirement.\n"
        "- At session start, say whether the work can stay in-session or should move to a handoff/new session.\n"
        "- Before multi-file edits, large reviews, long log reads, Docker/setup changes, or architecture reviews, warn first if the session is already long.\n"
        "- Do not use session compression as the normal continuation path.\n"
        "- If scope is too large, stop and leave a handoff for the next Codex session.\n"
        "- Review changed files and explicitly listed files first; ask Bucky to split oversized work.\n\n"
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
    text = path.read_text(encoding="utf-8", errors="replace").strip()
    text = _FM_RE.sub("", text, count=1).strip()
    return text[:max_chars]


def _excerpt(text: str, max_chars: int = 3000) -> str:
    stripped = text.strip()
    if len(stripped) <= max_chars:
        return stripped
    return stripped[:max_chars] + "\n\n[...truncated for handoff...]"


def write_context_handoff(
    task_id: str,
    source_path: Path,
    reason: str,
    detail: str,
    prompt_chars: int,
    request_body: str,
) -> Path:
    HANDOFF_DIR.mkdir(parents=True, exist_ok=True)
    out_path = HANDOFF_DIR / f"{ts()}_{task_id}_codex_handoff.md"
    out_path.write_text(
        f"""---
type: codex_context_handoff
task_id: {task_id}
source: {source_path.name}
created: {iso()}
status: next_session_required
reason: {reason}
prompt_chars: {prompt_chars}
---

# Codex Context Handoff: {task_id}

## Reason

{detail}

## Rule

Do not compress the Codex session to continue this work. Start a new Codex session or ask Bucky to split the review request.

## Next Session Steps

1. Run `python scripts/preflight_check.py`.
2. Run `git status --short`.
3. Review only the files listed in the request first.
4. If scope is still large, split by file or priority.
5. Report findings to Bucky and the user in the normal Codex review format.

## Original Request Excerpt

```markdown
{_excerpt(request_body)}
```
""",
        encoding="utf-8",
    )
    return out_path


def looks_like_context_failure(detail: str) -> bool:
    return bool(_CONTEXT_FAILURE_RE.search(detail))


def load_jh_role_context() -> str:
    parts = []
    for vault_rel in (
        "03_Projects/agents/codex-instructions.md",
        "03_Projects/agents/roles.md",
        "00_System/ROUTING_RULES.md",
        "06_Context_Packs/bucky-agent-os-legacy-rules.md",
        "06_Context_Packs/bucky-context-efficiency-goal-mode.md",
    ):
        content = read_optional(VAULT / vault_rel)
        if content:
            parts.append(f"### ObsidianVault/{vault_rel}\n{content}")

    legacy_enabled = os.getenv("BUCKY_ENABLE_LEGACY_CONTEXT", "0").strip().lower() in {"1", "true", "yes", "on"}
    legacy_shared = os.getenv("JH_SHARED_PATH", "").strip()
    if legacy_enabled and legacy_shared:
        shared = Path(legacy_shared)
        for rel in ("00_SYSTEM/roles.md", "00_SYSTEM/agent-onboarding.md"):
            content = read_optional(shared / rel)
            if content:
                parts.append(
                    f"### Legacy reference only: JH-SHARED/{rel}\n"
                    f"{content}"
                )
    return "\n\n---\n\n".join(parts) or "Bucky-managed Obsidian context not found."


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
    prompt_chars = len(prompt)
    if prompt_chars > MAX_PROMPT_CHARS:
        detail = (
            f"Codex prompt is {prompt_chars} chars, above "
            f"CODEX_MAX_PROMPT_CHARS={MAX_PROMPT_CHARS}. Split request before review."
        )
        handoff = write_context_handoff(task_id, path, "prompt_too_large", detail, prompt_chars, body)
        update_frontmatter(path, {
            "status": "needs_split",
            "codex_handoff": str(handoff),
            "prompt_chars": prompt_chars,
        })
        FAILED_DIR.mkdir(parents=True, exist_ok=True)
        path.rename(FAILED_DIR / path.name)
        return handoff

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
        detail = str(exc)
        if "temp_output" in locals():
            temp_output.unlink(missing_ok=True)
        if looks_like_context_failure(detail):
            handoff = write_context_handoff(
                task_id,
                path,
                "codex_context_failure",
                detail[:1000],
                prompt_chars,
                body,
            )
            update_frontmatter(path, {
                "status": "context_handoff",
                "review_error": detail[:500],
                "reviewed_at": iso(),
                "codex_handoff": str(handoff),
                "prompt_chars": prompt_chars,
            })
            FAILED_DIR.mkdir(parents=True, exist_ok=True)
            path.rename(FAILED_DIR / path.name)
            return handoff
        update_frontmatter(path, {
            "status": "failed",
            "review_error": detail[:500],
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
            print(f"Codex output {'planned' if dry_run else 'written'}: {result}")
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
