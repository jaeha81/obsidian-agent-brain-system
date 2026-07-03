#!/usr/bin/env python3
"""Pre-commit hook — synchronous Codex review on staged code files."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent.parent

CODE_EXTS = {".py", ".js", ".ts", ".jsx", ".tsx"}
TIMEOUT = int(os.getenv("CODEX_PRECOMMIT_TIMEOUT", "120"))
MAX_FILES = int(os.getenv("CODEX_PRECOMMIT_MAX_FILES", "10"))
MAX_DIFF_CHARS = 3000


def codex_cmd() -> str:
    import shutil
    cmd = os.getenv("CODEX_COMMAND", "codex").strip() or "codex"
    if any(sep in cmd for sep in ("\\", "/", ":")):
        return cmd
    return shutil.which(cmd) or cmd


def get_staged_files() -> list[str]:
    # Discord /codex review 가 파일 목록을 환경변수로 전달할 수 있음
    env_files = os.getenv("CODEX_PRECOMMIT_FILES", "").strip()
    if env_files:
        return [f.strip() for f in env_files.split(",") if f.strip() and Path(f).suffix in CODE_EXTS]
    r = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
        capture_output=True, text=True, cwd=str(ROOT),
    )
    return [f for f in r.stdout.strip().splitlines() if Path(f).suffix in CODE_EXTS]


def get_diff(filepath: str) -> str:
    r = subprocess.run(
        ["git", "diff", "--cached", filepath],
        capture_output=True, text=True, cwd=str(ROOT),
    )
    return r.stdout[:MAX_DIFF_CHARS]


def build_prompt(files_with_diffs: list[tuple[str, str]]) -> str:
    lines = [
        "# Pre-commit Codex Review\n",
        "You are Codex, reviewing staged changes BEFORE commit.\n",
        "Focus on: security vulnerabilities, critical bugs, breaking API changes.\n",
        "Skip: style, formatting, naming conventions.\n\n",
        "Response format (one line per issue):\n",
        "- BLOCK: <file>:<line> — <reason>  (security or critical bug only)\n",
        "- WARN: <file>:<line> — <reason>   (non-critical issue)\n",
        "- OK if no issues.\n\n",
        "## Staged Diffs\n\n",
    ]
    for filepath, diff in files_with_diffs:
        lines.append(f"### {filepath}\n```diff\n{diff}\n```\n\n")
    return "".join(lines)


def run_codex(prompt: str) -> tuple[str | None, str | None]:
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as f:
        out_path = Path(f.name)
    try:
        r = subprocess.run(
            [codex_cmd(), "exec", "-C", str(ROOT), "--sandbox", "read-only",
             "--output-last-message", str(out_path), "-"],
            input=prompt,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=TIMEOUT,
            cwd=str(ROOT),
        )
        if r.returncode != 0:
            detail = (r.stderr or r.stdout or "").strip()[:400]
            return None, f"Codex CLI 오류 (code {r.returncode}): {detail}"
        text = out_path.read_text(encoding="utf-8").strip()
        return text, None
    except subprocess.TimeoutExpired:
        return None, f"Codex 타임아웃 ({TIMEOUT}s)"
    except FileNotFoundError:
        return None, "Codex CLI를 찾을 수 없음 (PATH 확인 또는 CODEX_COMMAND 환경변수 설정)"
    finally:
        out_path.unlink(missing_ok=True)


def save_log(review_text: str, files: list[str]) -> None:
    log_dir = ROOT / "ObsidianVault" / "10_AgentBus" / "codex-precommit-logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    iso = datetime.now().isoformat(timespec="seconds")
    file_list = "\n".join(f"- {f}" for f in files)
    (log_dir / f"{ts}_precommit.md").write_text(
        f"---\ntype: precommit_review\ndate: {iso}\n---\n\n"
        f"## Files\n{file_list}\n\n## Review\n{review_text}\n",
        encoding="utf-8",
    )


def main() -> None:
    staged = get_staged_files()
    if not staged:
        sys.exit(0)

    if len(staged) > MAX_FILES:
        print(f"[Codex] {len(staged)}개 파일 ({MAX_FILES}개 초과) — precommit 검수 스킵")
        sys.exit(0)

    print(f"[Codex] {len(staged)}개 파일 검수 중...", end="", flush=True)

    diffs = [(f, get_diff(f)) for f in staged]
    prompt = build_prompt(diffs)
    review, err = run_codex(prompt)

    if err:
        print(f"\n[Codex] ⚠️ {err} — 커밋 허용")
        sys.exit(0)

    try:
        save_log(review, staged)
    except Exception:
        pass

    upper = review.upper()
    if "BLOCK:" in upper:
        block_lines = [l for l in review.splitlines() if "BLOCK:" in l.upper()]
        print(f"\n[Codex] ❌ 커밋 차단\n" + "\n".join(block_lines))
        sys.exit(1)
    elif "WARN:" in upper:
        warn_lines = [l for l in review.splitlines() if "WARN:" in l.upper()]
        print(f"\n[Codex] ⚠️ " + " | ".join(warn_lines[:3]))
        sys.exit(0)
    else:
        print(" ✅")
        sys.exit(0)


if __name__ == "__main__":
    main()
