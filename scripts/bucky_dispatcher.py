"""
Bucky Dispatcher — 태스크 유형 분류 + 에이전트 배분
Bucky는 오케스트레이터. 직접 구현하지 않고 배분만 함.
"""
import json
import os
from pathlib import Path
from datetime import datetime

VAULT = Path("G:/내 드라이브/obsidian-agent-brain-system/ObsidianVault")
AGENTBUS = VAULT / "AgentBus"
INBOX_CLAUDE = AGENTBUS / "inbox/claude"
INBOX_CODEX = AGENTBUS / "inbox/codex"
OUTBOX_COMPLETED = AGENTBUS / "outbox/completed"
OUTBOX_FAILED = AGENTBUS / "outbox/failed"
MESSAGES = AGENTBUS / "messages/agent-room-messages.jsonl"

# 금지 경로 — 절대 접근 불가
FORBIDDEN_PATHS = [
    "G:/내 드라이브/JH-Agent-Room",
    "D:/ai프로젝트/JH-Agent-Room",
]

TASK_KEYWORDS = {
    "claude": ["구현", "만들어", "작성", "코드", "수정", "추가", "삭제", "리팩토링"],
    "codex": ["검수", "리뷰", "확인", "분석", "검증", "테스트"],
    "collector": ["수집", "가져와", "ChatGPT", "GPT", "대화"],
    "distiller": ["정제", "요약", "지식", "변환"],
    "gap": ["갭", "부족", "빠진", "없는"],
    "reporter": ["리포트", "보고", "오늘 한 일", "데일리"],
}

def classify_task(instruction: str) -> str:
    for agent, keywords in TASK_KEYWORDS.items():
        if any(kw in instruction for kw in keywords):
            return agent
    return "claude"  # 기본값: Claude Code

def dispatch(instruction: str, requester: str = "user") -> dict:
    agent = classify_task(instruction)
    task_id = f"task-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

    task = {
        "id": task_id,
        "instruction": instruction,
        "agent": agent,
        "requester": requester,
        "status": "pending",
        "created_at": datetime.now().isoformat(),
    }

    # AgentBus inbox에 저장
    if agent == "claude":
        inbox = INBOX_CLAUDE
    elif agent == "codex":
        inbox = INBOX_CODEX
    else:
        inbox = AGENTBUS / f"inbox/{agent}"

    inbox.mkdir(parents=True, exist_ok=True)
    task_file = inbox / f"{task_id}.json"
    task_file.write_text(json.dumps(task, ensure_ascii=False, indent=2), encoding="utf-8")

    # 메시지 로그
    _log_message(agent="bucky", kind="dispatch", body=f"[{agent}] {instruction[:80]}", task_id=task_id)

    print(f"✅ [{agent}] 배분 완료: {task_id}")
    return task

def _log_message(agent: str, kind: str, body: str, task_id: str = ""):
    MESSAGES.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "ts": datetime.now().isoformat(),
        "speaker": agent,
        "kind": kind,
        "body": body,
        "task_id": task_id,
    }
    with open(MESSAGES, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

def get_pending_tasks() -> list:
    tasks = []
    for inbox_dir in [INBOX_CLAUDE, INBOX_CODEX]:
        if inbox_dir.exists():
            for f in inbox_dir.glob("*.json"):
                tasks.append(json.loads(f.read_text(encoding="utf-8")))
    return sorted(tasks, key=lambda x: x["created_at"])

def get_completed_tasks() -> list:
    tasks = []
    OUTBOX_COMPLETED.mkdir(parents=True, exist_ok=True)
    for f in OUTBOX_COMPLETED.glob("*.json"):
        tasks.append(json.loads(f.read_text(encoding="utf-8")))
    return sorted(tasks, key=lambda x: x.get("completed_at", ""), reverse=True)

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("사용법: python bucky_dispatcher.py '태스크 내용'")
        sys.exit(1)
    instruction = " ".join(sys.argv[1:])
    task = dispatch(instruction)
    print(json.dumps(task, ensure_ascii=False, indent=2))
