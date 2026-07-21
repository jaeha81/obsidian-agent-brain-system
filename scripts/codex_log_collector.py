#!/usr/bin/env python3
"""
Codex Log Collector
Claude Code / Codex 작업 로그를 수집하여 ObsidianVault에 저장.

수집 소스:
  1. git log — 최근 커밋 (코드 변경 요약)
  2. AgentBus — completed/failed 메시지
  3. Claude Code 세션 파일 (~/.claude/projects/...)
  4. 기존 handoff 파일

Usage:
    python codex_log_collector.py --collect
    python codex_log_collector.py --collect --since 2026-05-20
    python codex_log_collector.py --collect --dry-run
"""

import sys
import os
import json
import argparse
import subprocess
import logging
from pathlib import Path
from datetime import datetime, timezone, timedelta, date

VAULT_BASE = Path("D:/ai프로젝트/obsidian-agent-brain-system/ObsidianVault")
OUTPUT_BASE = VAULT_BASE / "01_RAW" / "codex-sessions"
AGENTBUS_DIR = VAULT_BASE / "10_AgentBus"
REPO_ROOT = Path(__file__).parent.parent
STATE_FILE = Path(__file__).parent / ".codex_collector_state.json"

# Claude Code 세션 디렉토리 (Windows)
CLAUDE_SESSIONS_DIR = Path(os.environ.get("USERPROFILE", "~")) / ".claude" / "projects"

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s", stream=sys.stdout)
log = logging.getLogger(__name__)


def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"last_collected_at": None}


def save_state(state: dict) -> None:
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def parse_iso(ts: str | None) -> datetime | None:
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except Exception:
        return None


# ── Git 커밋 수집 ──────────────────────────────────────────────────────────────

def collect_git_commits(since: datetime | None, dry_run: bool) -> list[Path]:
    """git log에서 최근 커밋을 수집해 Obsidian 노트로 저장한다."""
    saved = []
    since_str = since.strftime("%Y-%m-%d") if since else "1970-01-01"

    try:
        result = subprocess.run(
            ["git", "log", f"--since={since_str}", "--format=%H|%ai|%s|%an", "--no-merges"],
            capture_output=True, text=True, encoding="utf-8",
            cwd=str(REPO_ROOT), timeout=30
        )
        if result.returncode != 0 or not result.stdout.strip():
            log.info("새 커밋 없음")
            return []
    except Exception as e:
        log.error(f"git log 실패: {e}")
        return []

    commits = []
    for line in result.stdout.strip().splitlines():
        parts = line.split("|", 3)
        if len(parts) < 4:
            continue
        commits.append({
            "hash": parts[0][:12],
            "datetime": parts[1],
            "subject": parts[2],
            "author": parts[3],
        })

    if not commits:
        return []

    # 날짜별로 그룹핑
    by_date: dict[str, list[dict]] = {}
    for c in commits:
        dt = parse_iso(c["datetime"])
        d = dt.astimezone().strftime("%Y-%m-%d") if dt else date.today().isoformat()
        by_date.setdefault(d, []).append(c)

    for d, day_commits in by_date.items():
        out_dir = OUTPUT_BASE / d
        out_path = out_dir / "git-commits.md"

        lines = [
            "---",
            "source: Codex/ClaudeCode",
            f"date: {d}",
            f"type: git-commits",
            f"commit_count: {len(day_commits)}",
            "---",
            "",
            f"# Git Commits — {d}",
            "",
        ]
        for c in day_commits:
            lines.append(f"## `{c['hash']}` — {c['subject']}")
            lines.append(f"- 날짜: {c['datetime']}")
            lines.append(f"- 작성자: {c['author']}")
            # diff stats
            try:
                stat_result = subprocess.run(
                    ["git", "show", "--stat", "--format=", c["hash"][:12]],
                    capture_output=True, text=True, encoding="utf-8",
                    cwd=str(REPO_ROOT), timeout=10
                )
                if stat_result.stdout.strip():
                    lines.append("")
                    lines.append("```")
                    lines.append(stat_result.stdout.strip()[:500])
                    lines.append("```")
            except Exception:
                pass
            lines.append("")

        lines.append("*자동 수집: codex_log_collector.py*")
        content = "\n".join(lines)

        if dry_run:
            log.info(f"[DRY-RUN] git 커밋 저장 예정: {out_path} ({len(day_commits)}개)")
        else:
            out_dir.mkdir(parents=True, exist_ok=True)
            out_path.write_text(content, encoding="utf-8")
            log.info(f"git 커밋 저장: {out_path}")
        saved.append(out_path)

    return saved


# ── AgentBus 메시지 수집 ───────────────────────────────────────────────────────

def collect_agentbus_messages(since: datetime | None, dry_run: bool) -> list[Path]:
    """AgentBus completed/failed 메시지를 수집한다."""
    saved = []

    for subdir in ["completed", "failed", "outbox"]:
        bus_dir = AGENTBUS_DIR / subdir
        if not bus_dir.exists():
            continue

        for f in sorted(bus_dir.glob("*.json")) + sorted(bus_dir.glob("*.md")):
            try:
                mtime = datetime.fromtimestamp(f.stat().st_mtime, tz=timezone.utc)
                if since and mtime <= since.replace(tzinfo=timezone.utc) if since.tzinfo is None else since:
                    continue

                content_raw = f.read_text(encoding="utf-8", errors="ignore")
                date_str = mtime.astimezone().strftime("%Y-%m-%d")
                out_dir = OUTPUT_BASE / date_str
                out_path = out_dir / f"agentbus_{subdir}_{f.name}"

                note = "\n".join([
                    "---",
                    "source: AgentBus",
                    f"date: {date_str}",
                    f"type: agentbus-{subdir}",
                    f"original_file: {f.name}",
                    "---",
                    "",
                    f"# AgentBus {subdir.upper()} — {f.stem}",
                    "",
                    "```",
                    content_raw[:2000],
                    "```",
                    "",
                    "*자동 수집: codex_log_collector.py*",
                ])

                if dry_run:
                    log.info(f"[DRY-RUN] AgentBus 저장 예정: {out_path}")
                else:
                    out_dir.mkdir(parents=True, exist_ok=True)
                    out_path.write_text(note, encoding="utf-8")
                    log.info(f"AgentBus 저장: {out_path}")
                saved.append(out_path)

            except Exception as e:
                log.warning(f"AgentBus 파일 처리 실패 ({f.name}): {e}")

    return saved


# ── Claude Code 세션 파일 수집 ─────────────────────────────────────────────────

def collect_claude_code_sessions(since: datetime | None, dry_run: bool) -> list[Path]:
    """~/.claude/projects/ 하위 JSONL 세션 파일을 수집한다."""
    saved = []

    if not CLAUDE_SESSIONS_DIR.exists():
        log.info(f"Claude Code 세션 디렉토리 없음: {CLAUDE_SESSIONS_DIR}")
        return []

    for jsonl_file in sorted(CLAUDE_SESSIONS_DIR.rglob("*.jsonl")):
        try:
            mtime = datetime.fromtimestamp(jsonl_file.stat().st_mtime, tz=timezone.utc)
            if since:
                since_utc = since.replace(tzinfo=timezone.utc) if since.tzinfo is None else since
                if mtime <= since_utc:
                    continue

            date_str = mtime.astimezone().strftime("%Y-%m-%d")
            out_dir = OUTPUT_BASE / date_str
            proj_name = jsonl_file.parent.name[:40]
            out_path = out_dir / f"claude_code_{proj_name}_{jsonl_file.stem[:20]}.md"

            # JSONL 파싱 — 메시지 요약
            messages = []
            try:
                for line in jsonl_file.read_text(encoding="utf-8", errors="ignore").splitlines()[:200]:
                    if not line.strip():
                        continue
                    try:
                        obj = json.loads(line)
                        role = obj.get("role", obj.get("type", "unknown"))
                        content = ""
                        if isinstance(obj.get("content"), str):
                            content = obj["content"][:300]
                        elif isinstance(obj.get("content"), list):
                            for block in obj["content"]:
                                if isinstance(block, dict) and block.get("type") == "text":
                                    content = block.get("text", "")[:300]
                                    break
                        if content:
                            messages.append({"role": role, "content": content})
                    except json.JSONDecodeError:
                        pass
            except Exception as e:
                log.warning(f"JSONL 파싱 실패 ({jsonl_file.name}): {e}")

            lines = [
                "---",
                "source: ClaudeCode-Session",
                f"date: {date_str}",
                f"type: claude-code-session",
                f"project: {proj_name}",
                f"message_count: {len(messages)}",
                "---",
                "",
                f"# Claude Code Session — {proj_name}",
                f"*파일: {jsonl_file.name}*",
                "",
            ]
            for msg in messages[:30]:
                label = "**Human**" if "human" in msg["role"] else "**Assistant**"
                lines.append(f"{label}\n\n{msg['content']}\n\n---\n")

            lines.append("*자동 수집: codex_log_collector.py*")
            note = "\n".join(lines)

            if dry_run:
                log.info(f"[DRY-RUN] Claude Code 세션 저장 예정: {out_path}")
            else:
                out_dir.mkdir(parents=True, exist_ok=True)
                out_path.write_text(note, encoding="utf-8")
                log.info(f"Claude Code 세션 저장: {out_path}")
            saved.append(out_path)

        except Exception as e:
            log.warning(f"세션 파일 처리 실패 ({jsonl_file.name}): {e}")

    return saved


# ── 진입점 ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Codex Log Collector — ClaudeCode/Codex 작업 로그를 ObsidianVault에 저장")
    parser.add_argument("--collect", action="store_true", default=True)
    parser.add_argument("--since", type=str, help="수집 시작 날짜 (YYYY-MM-DD), 기본: 마지막 수집 시각")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    state = load_state()
    last_str = args.since or state.get("last_collected_at")
    since: datetime | None = parse_iso(last_str) if last_str else None

    if since:
        log.info(f"증분 수집 시작 (since: {since.isoformat()})")
    else:
        log.info("전체 수집 시작 (최초 실행)")

    now_utc = datetime.now(timezone.utc)
    all_saved: list[Path] = []

    log.info("=== git 커밋 수집 ===")
    all_saved += collect_git_commits(since, args.dry_run)

    log.info("=== AgentBus 메시지 수집 ===")
    all_saved += collect_agentbus_messages(since, args.dry_run)

    log.info("=== Claude Code 세션 수집 ===")
    all_saved += collect_claude_code_sessions(since, args.dry_run)

    if not args.dry_run:
        state["last_collected_at"] = now_utc.isoformat()
        save_state(state)

    label = "[DRY-RUN] " if args.dry_run else ""
    log.info(f"{label}수집 완료: 총 {len(all_saved)}개 파일")
    for p in all_saved:
        print(str(p))


if __name__ == "__main__":
    main()
