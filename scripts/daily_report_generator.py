#!/usr/bin/env python3
"""
Daily Report Generator — AgentBus 완료·실패 태스크 → 데일리 리포트 생성

수집 대상:
  - ObsidianVault/10_AgentBus/completed/*.md  (오늘 날짜 processed_at)
  - ObsidianVault/10_AgentBus/failed/*.md     (오늘 날짜 processed_at)
  - ObsidianVault/10_AgentBus/tasks/session_tasks.json (task_tracker 세션)

출력:
  - G:/내 드라이브/JH-SHARED/04_DAILY_REPORTS/2026/YYYY-MM/YYYY-MM-DD.md (업데이트)
  - ObsidianVault/07_Daily/YYYY-MM-DD.md (Obsidian 내부 기록)

Requirements: pip install python-dotenv pyyaml
"""

import json
import os
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import yaml
from dotenv import load_dotenv

_ROOT = Path(__file__).parent.parent
load_dotenv(_ROOT / ".env", encoding="utf-8", override=True)

VAULT = Path(os.getenv("VAULT_PATH", str(_ROOT / "ObsidianVault")))
AGENTBUS = VAULT / "10_AgentBus"
COMPLETED_DIR = AGENTBUS / "completed"
FAILED_DIR = AGENTBUS / "failed"
TASKS_FILE = AGENTBUS / "tasks" / "session_tasks.json"

JH_SHARED = Path(os.getenv("JH_SHARED_PATH", "G:/내 드라이브/JH-SHARED"))
TODAY = datetime.now().strftime("%Y-%m-%d")
YEAR_MONTH = datetime.now().strftime("%Y/%Y-%m")

DAILY_REPORT_PATH = JH_SHARED / "04_DAILY_REPORTS" / YEAR_MONTH / f"{TODAY}.md"
OBSIDIAN_DAILY_PATH = VAULT / "07_Daily" / f"{TODAY}.md"

_FM_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)


def _parse_frontmatter(text: str) -> dict:
    m = _FM_RE.match(text)
    if m:
        try:
            return yaml.safe_load(m.group(1)) or {}
        except yaml.YAMLError:
            pass
    return {}


def _is_today(dt_str: str | None) -> bool:
    if not dt_str:
        return False
    return str(dt_str).startswith(TODAY)


def _collect_agentbus_tasks() -> tuple[list[dict], list[dict]]:
    """completed / failed 디렉토리에서 오늘 처리된 태스크 수집."""
    done_tasks = []
    fail_tasks = []

    for md in sorted(COMPLETED_DIR.glob("*.md")) if COMPLETED_DIR.exists() else []:
        try:
            fm = _parse_frontmatter(md.read_text(encoding="utf-8", errors="replace"))
            if _is_today(fm.get("processed_at") or fm.get("created")):
                done_tasks.append({
                    "id": fm.get("task_id", md.stem[:20]),
                    "title": fm.get("title", md.stem),
                    "type": fm.get("type", "unknown"),
                    "processed_by": fm.get("processed_by", ""),
                    "output": fm.get("output", ""),
                })
        except Exception:
            continue

    for md in sorted(FAILED_DIR.glob("*.md")) if FAILED_DIR.exists() else []:
        try:
            fm = _parse_frontmatter(md.read_text(encoding="utf-8", errors="replace"))
            if _is_today(fm.get("processed_at") or fm.get("created")):
                fail_tasks.append({
                    "id": fm.get("task_id", md.stem[:20]),
                    "title": fm.get("title", md.stem),
                    "type": fm.get("type", "unknown"),
                    "error": fm.get("error", ""),
                })
        except Exception:
            continue

    return done_tasks, fail_tasks


def _collect_session_tasks() -> list[dict]:
    """task_tracker.py 세션 파일에서 오늘 태스크 수집."""
    if not TASKS_FILE.exists():
        return []
    try:
        tasks = json.loads(TASKS_FILE.read_text(encoding="utf-8"))
        return [t for t in tasks if _is_today(t.get("created"))]
    except Exception:
        return []


def _group_by_type(tasks: list[dict]) -> dict[str, list[dict]]:
    groups: dict[str, list[dict]] = defaultdict(list)
    for t in tasks:
        groups[t.get("type", "general")].append(t)
    return dict(groups)


def generate_report() -> str:
    """데일리 리포트 마크다운 생성."""
    done_bus, fail_bus = _collect_agentbus_tasks()
    session_tasks = _collect_session_tasks()

    # session_tasks는 상세 상태 포함
    session_done = [t for t in session_tasks if t.get("status") == "done"]
    session_fail = [t for t in session_tasks if t.get("status") == "failed"]
    session_pending = [t for t in session_tasks if t.get("status") in ("pending", "in_progress")]

    # AgentBus와 세션 합산 (중복 제거)
    all_done = done_bus + [t for t in session_done if t not in done_bus]
    all_fail = fail_bus + [t for t in session_fail if t not in fail_bus]

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [
        f"---",
        f"date: {TODAY}",
        f"generated: {now_str}",
        f"tags:",
        f"  - daily-report",
        f"  - auto-generated",
        f"---",
        f"",
        f"# 데일리 리포트 — {TODAY}",
        f"",
        f"> 생성: {now_str}  |  완료: {len(all_done)}  |  실패: {len(all_fail)}  |  대기: {len(session_pending)}",
        f"",
    ]

    # 완료 항목
    lines += ["## ✅ 완료", ""]
    if all_done:
        groups = _group_by_type(all_done)
        for gtype, gtasks in groups.items():
            lines.append(f"### {gtype}")
            for t in gtasks:
                lines.append(f"- **{t.get('id', '')}** {t.get('title', '')}  _{t.get('processed_by', '')}_")
                if t.get("output"):
                    lines.append(f"  - 출력: `{str(t['output'])[:80]}`")
            lines.append("")
    else:
        lines += ["_없음_", ""]

    # 실패 항목
    lines += ["## ❌ 실패·오류", ""]
    if all_fail:
        for t in all_fail:
            lines.append(f"- **{t.get('id', '')}** {t.get('title', '')}  `{t.get('error', '')[:80]}`")
        lines.append("")
    else:
        lines += ["_없음_", ""]

    # 미완료 (세션)
    lines += ["## ⏳ 미완료 (다음 세션 인계)", ""]
    if session_pending:
        for t in session_pending:
            router = t.get("router", "")
            lines.append(f"- **{t.get('id', '')}** [{router}] {t.get('title', '')}")
        lines.append("")
    else:
        lines += ["_없음_", ""]

    # 파트별 요약
    lines += ["## 📊 파트별 분류", ""]
    all_tasks = all_done + all_fail + session_pending
    if all_tasks:
        groups = _group_by_type(all_tasks)
        for gtype, gtasks in groups.items():
            d = sum(1 for t in gtasks if t in all_done)
            f = sum(1 for t in gtasks if t in all_fail)
            p = sum(1 for t in gtasks if t in session_pending)
            lines.append(f"| {gtype} | {len(gtasks)} | ✅{d} | ❌{f} | ⏳{p} |")
        lines = lines[:-0]  # keep trailing newline
    else:
        lines.append("_태스크 없음_")

    lines.append("")
    return "\n".join(lines)


def save_report(content: str) -> tuple[Path, Path | None]:
    """JH-SHARED 데일리 리포트 + Obsidian 내부 일지 저장."""
    # JH-SHARED
    DAILY_REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    if DAILY_REPORT_PATH.exists():
        existing = DAILY_REPORT_PATH.read_text(encoding="utf-8")
        # 기존 보고서가 있으면 자동생성 섹션만 교체
        marker = "\n## ✅ 완료"
        if marker in existing:
            split_at = existing.index(marker)
            content = existing[:split_at] + content[content.index(marker):]
    DAILY_REPORT_PATH.write_text(content, encoding="utf-8")

    # Obsidian 내부 (선택)
    obs_path = None
    try:
        OBSIDIAN_DAILY_PATH.parent.mkdir(parents=True, exist_ok=True)
        OBSIDIAN_DAILY_PATH.write_text(content, encoding="utf-8")
        obs_path = OBSIDIAN_DAILY_PATH
    except Exception:
        pass

    return DAILY_REPORT_PATH, obs_path


def run() -> tuple[str, Path, Path | None]:
    """리포트 생성 + 저장 후 (마크다운 텍스트, jh경로, obsidian경로) 반환."""
    content = generate_report()
    jh_path, obs_path = save_report(content)
    return content, jh_path, obs_path


if __name__ == "__main__":
    content, jh_path, obs_path = run()
    print(f"리포트 저장: {jh_path}")
    if obs_path:
        print(f"Obsidian 저장: {obs_path}")
    print("\n" + content[:1000])
