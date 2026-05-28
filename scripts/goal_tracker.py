#!/usr/bin/env python3
"""
Goal Tracker — Bucky 골모드.
!골 <목표> 로 목표 선언 → Claude가 서브태스크 분해 → 큐 자동 투입
!골상태 / !골종료 / !골포커스 지원
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

_ROOT = Path(__file__).parent.parent
load_dotenv(_ROOT / ".env", encoding="utf-8", override=True)

VAULT = Path(os.getenv("VAULT_PATH", str(_ROOT / "ObsidianVault")))
_GOAL_FILE = VAULT / "00_System" / "active_goal.json"

_DECOMPOSE_PROMPT = """\
사용자 목표를 5~8개 구체적 서브태스크로 분해해라.
각 태스크는 단독으로 실행 가능한 작업 단위여야 한다.
JSON 배열로만 응답. 다른 텍스트 없음.

형식:
["태스크1 설명", "태스크2 설명", ...]

목표: {goal}
"""


def load() -> Optional[dict]:
    if not _GOAL_FILE.exists():
        return None
    try:
        return json.loads(_GOAL_FILE.read_text(encoding="utf-8"))
    except Exception:
        return None


def save(goal_data: dict) -> None:
    _GOAL_FILE.parent.mkdir(parents=True, exist_ok=True)
    _GOAL_FILE.write_text(json.dumps(goal_data, ensure_ascii=False, indent=2), encoding="utf-8")


def clear() -> None:
    if _GOAL_FILE.exists():
        _GOAL_FILE.unlink()


def set_goal(goal: str, subtasks: list[str]) -> dict:
    data = {
        "goal": goal,
        "created": datetime.now().isoformat(timespec="seconds"),
        "subtasks": [
            {"id": i + 1, "body": t, "status": "pending", "task_id": None}
            for i, t in enumerate(subtasks)
        ],
        "focus": False,
    }
    save(data)
    return data


def mark_task(task_id: str, status: str) -> None:
    data = load()
    if not data:
        return
    for st in data["subtasks"]:
        if st.get("task_id") == task_id:
            st["status"] = status
            break
    save(data)


def set_focus(enabled: bool) -> None:
    data = load()
    if not data:
        return
    data["focus"] = enabled
    save(data)


def is_focus() -> bool:
    data = load()
    return bool(data and data.get("focus"))


def status_text() -> str:
    data = load()
    if not data:
        return "활성 목표 없음. `!골 <목표>` 로 설정하세요."
    goal = data["goal"]
    subtasks = data["subtasks"]
    done = sum(1 for s in subtasks if s["status"] == "done")
    total = len(subtasks)
    pct = int(done / total * 100) if total else 0
    bar = "█" * (pct // 10) + "░" * (10 - pct // 10)
    focus_tag = " 🎯 포커스ON" if data.get("focus") else ""

    lines = [
        f"**🎯 목표{focus_tag}**: {goal}",
        f"진행률: [{bar}] {pct}% ({done}/{total})",
        "",
    ]
    for s in subtasks:
        icon = {"done": "✅", "in_progress": "🔄", "failed": "❌"}.get(s["status"], "⬜")
        tid = f" `{s['task_id'][-6:]}`" if s.get("task_id") else ""
        lines.append(f"{icon} {s['id']}. {s['body']}{tid}")
    return "\n".join(lines)


def decompose(goal: str) -> list[str]:
    """Claude CLI로 목표 분해. 실패 시 단일 태스크 반환."""
    try:
        from bucky_client import run_bucky
        prompt = _DECOMPOSE_PROMPT.format(goal=goal)
        # task_type='reasoning' → Opus 라우팅 (목표 분해 정확성 우선, Sonnet 한도 분산)
        raw = run_bucky(prompt, timeout=60, task_type="reasoning")
        start = raw.find("[")
        end = raw.rfind("]") + 1
        if start != -1 and end > start:
            subtasks = json.loads(raw[start:end])
            if isinstance(subtasks, list) and subtasks:
                return [str(s) for s in subtasks[:8]]
    except Exception as e:
        print(f"[GoalTracker] 분해 실패: {e}", flush=True)
    return [goal]
