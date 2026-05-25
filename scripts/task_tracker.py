#!/usr/bin/env python3
"""
Task Tracker — 세션 내 다중 작업 분류·배분·상태 추적

흐름:
  사용자 지시 (Discord / 직접 호출)
    → classify() 로 태스크 유형 판단
    → route_task() 로 Claude Code / Codex / Bucky 배분
    → AgentBus inbox 파일 생성
    → 상태 파일(session_tasks.json)에 기록

Requirements: pip install python-dotenv pyyaml
"""

import json
import os
import re
from datetime import datetime
from pathlib import Path

import yaml
from dotenv import load_dotenv

_ROOT = Path(__file__).parent.parent
load_dotenv(_ROOT / ".env", encoding="utf-8", override=True)

VAULT = Path(os.getenv("VAULT_PATH", str(_ROOT / "ObsidianVault")))
INBOX = VAULT / "10_AgentBus" / "inbox"
TASKS_DIR = VAULT / "10_AgentBus" / "tasks"
TASKS_FILE = TASKS_DIR / "session_tasks.json"

_IMPL_KEYWORDS = (
    "구현", "만들어", "작성해", "코드", "스크립트", "파일 생성", "추가해", "수정해",
    "implement", "create", "write code", "build", "add", "fix", "refactor",
)
_REVIEW_KEYWORDS = ("검토", "검수", "리뷰", "review", "verify", "check", "validate")
_RESEARCH_KEYWORDS = ("분석", "조사", "알아봐", "research", "analyze", "explore", "찾아봐")


def _iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _ts() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _next_id(tasks: list[dict]) -> str:
    existing = {t.get("id", "") for t in tasks}
    for i in range(1, 999):
        tid = f"T{i:03d}"
        if tid not in existing:
            return tid
    return f"T{_ts()}"


def classify(body: str) -> str:
    """태스크 유형 분류: implementation_request / review_request / research / general"""
    b = body.lower()
    if any(k in b for k in _REVIEW_KEYWORDS):
        return "review_request"
    if any(k in b for k in _IMPL_KEYWORDS):
        return "implementation_request"
    if any(k in b for k in _RESEARCH_KEYWORDS):
        return "research"
    return "general"


def _router_for(task_type: str) -> str:
    """태스크 유형 → 실행 주체"""
    if task_type == "review_request":
        return "Codex"
    if task_type == "implementation_request":
        return "ClaudeCode"
    return "Bucky"


def _load_tasks() -> list[dict]:
    TASKS_DIR.mkdir(parents=True, exist_ok=True)
    if not TASKS_FILE.exists():
        return []
    try:
        return json.loads(TASKS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []


def _save_tasks(tasks: list[dict]) -> None:
    TASKS_DIR.mkdir(parents=True, exist_ok=True)
    TASKS_FILE.write_text(json.dumps(tasks, ensure_ascii=False, indent=2), encoding="utf-8")


def add_task(title: str, body: str, task_type: str | None = None, source: str = "user") -> dict:
    """새 태스크 등록 → AgentBus inbox 파일 생성 → 상태 파일 갱신"""
    tasks = _load_tasks()
    task_type = task_type or classify(body)
    router = _router_for(task_type)
    tid = _next_id(tasks)
    created = _iso()

    # AgentBus inbox 파일 생성
    INBOX.mkdir(parents=True, exist_ok=True)
    safe_title = re.sub(r"[^\w가-힣\-]", "_", title)[:40]
    inbox_path = INBOX / f"{_ts()}_{tid}_{safe_title}.md"
    frontmatter = {
        "type": task_type,
        "task_id": tid,
        "title": title,
        "source": source,
        "router": router,
        "status": "pending",
        "created": created,
    }
    inbox_path.write_text(
        f"---\n{yaml.dump(frontmatter, allow_unicode=True, default_flow_style=False)}---\n\n{body}\n",
        encoding="utf-8",
    )

    task = {
        "id": tid,
        "title": title,
        "type": task_type,
        "router": router,
        "status": "pending",
        "created": created,
        "inbox_file": inbox_path.name,
        "result": None,
    }
    tasks.append(task)
    _save_tasks(tasks)
    return task


def update_task(task_id: str, status: str, result: str | None = None) -> bool:
    tasks = _load_tasks()
    for t in tasks:
        if t["id"] == task_id:
            t["status"] = status
            t["updated"] = _iso()
            if result is not None:
                t["result"] = result[:300]
            _save_tasks(tasks)
            return True
    return False


def get_all_tasks() -> list[dict]:
    return _load_tasks()


def get_today_tasks() -> list[dict]:
    today = datetime.now().strftime("%Y-%m-%d")
    return [t for t in _load_tasks() if t.get("created", "").startswith(today)]


def clear_session() -> int:
    tasks = _load_tasks()
    count = len(tasks)
    _save_tasks([])
    return count


def format_task_list(tasks: list[dict] | None = None) -> str:
    """Discord용 태스크 현황 포매팅"""
    if tasks is None:
        tasks = get_today_tasks()
    if not tasks:
        return "오늘 등록된 태스크가 없습니다."

    status_icon = {"pending": "⏳", "in_progress": "🔄", "done": "✅", "failed": "❌"}
    router_icon = {"ClaudeCode": "🤖", "Codex": "🔬", "Bucky": "💬"}

    lines = ["**📋 오늘 태스크 현황**\n"]
    for t in tasks:
        icon = status_icon.get(t.get("status", ""), "❓")
        r_icon = router_icon.get(t.get("router", ""), "")
        lines.append(f"{icon} `{t['id']}` {r_icon} **{t['title']}**  _{t.get('type', '')}_")
        if t.get("result"):
            lines.append(f"   └ {t['result'][:80]}...")

    done = sum(1 for t in tasks if t.get("status") == "done")
    failed = sum(1 for t in tasks if t.get("status") == "failed")
    pending = sum(1 for t in tasks if t.get("status") in ("pending", "in_progress"))
    lines.append(f"\n**합계:** ✅{done} | ❌{failed} | ⏳{pending}")
    return "\n".join(lines)


if __name__ == "__main__":
    # 간단한 CLI 테스트
    import sys
    if len(sys.argv) < 2:
        print(format_task_list())
    elif sys.argv[1] == "add":
        body = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else "테스트 태스크"
        t = add_task(body[:40], body)
        print(f"등록: {t['id']} → {t['type']} → {t['router']}")
    elif sys.argv[1] == "clear":
        n = clear_session()
        print(f"세션 초기화: {n}개 삭제")
