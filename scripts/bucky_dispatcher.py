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

# 스코어링 기반 분류표 — positive/negative 키워드 + 가중치
# score = len(positive_matches) * weight - len(negative_matches) * 2
# 최고 점수 에이전트 선택 (동점·전부 0점 → "bucky" 직접 처리)
TASK_KEYWORDS: dict[str, dict] = {
    "claude": {
        "positive": ["구현", "만들어", "작성", "코드", "개발", "추가", "삭제", "리팩토링",
                     "함수", "클래스", "스크립트", "자동화", "연동", "API 만들"],
        "negative": ["검수", "리뷰", "확인해줘"],
        "weight": 2,
    },
    "codex": {
        "positive": ["검수", "리뷰", "오류", "버그", "디버그", "검증", "테스트", "점검",
                     "확인해줘", "뭐가 문제", "왜 안돼"],
        "negative": ["만들어", "구현"],
        "weight": 2,
    },
    "gemini-research": {
        "positive": ["검색해", "리서치", "최신", "시장조사", "출처", "자료 찾아", "트렌드",
                     "조사해", "어떤 회사", "어떤 기술"],
        "negative": [],
        "weight": 2,
    },
    "gemini-rag": {
        "positive": ["vault", "노트에서", "obsidian", "기록에서", "저장된", "지식베이스",
                     "이전에 저장", "노트 찾아"],
        "negative": [],
        "weight": 2,
    },
    "gemini-multimodal": {
        "positive": ["이미지 분석", "사진 분석", "도면", "현장사진", "자재사진", "이미지 설명",
                     "사진 보고"],
        "negative": [],
        "weight": 3,
    },
    "gemini-content": {
        "positive": ["블로그", "유튜브", "쇼츠", "광고문구", "콘텐츠", "영상프롬프트", "SNS",
                     "포스팅", "글 써줘", "카피"],
        "negative": [],
        "weight": 2,
    },
    "gemini-validator": {
        "positive": ["교차검증", "리스크 점검", "모순", "누락 확인", "validator", "이중검토",
                     "두 번 확인"],
        "negative": [],
        "weight": 2,
    },
    "reporter": {
        "positive": ["리포트", "보고", "오늘 한 일", "데일리", "일일 보고"],
        "negative": [],
        "weight": 1,
    },
    "collector": {
        "positive": ["수집", "가져와", "ChatGPT", "GPT", "대화 내용"],
        "negative": [],
        "weight": 1,
    },
    "distiller": {
        "positive": ["정제", "지식으로 변환", "노트 정리", "핵심 추출"],
        "negative": ["요약"],  # 단순 요약은 bucky가 직접
        "weight": 1,
    },
}

def classify_task(instruction: str) -> str:
    """스코어링 기반 에이전트 분류. 동점·전부 0점 시 'bucky' 반환."""
    scores: dict[str, float] = {}
    for agent, cfg in TASK_KEYWORDS.items():
        pos = sum(1 for kw in cfg["positive"] if kw in instruction)
        neg = sum(1 for kw in cfg["negative"] if kw in instruction)
        scores[agent] = pos * cfg["weight"] - neg * 2

    best_agent = max(scores, key=scores.get)
    if scores[best_agent] <= 0:
        return "bucky"  # 명확한 키워드 없으면 Bucky가 직접 처리
    return best_agent

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
    elif agent.startswith("gemini-"):
        inbox = AGENTBUS / "inbox/gemini" / agent.replace("gemini-", "")
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
    gemini_roles = ["research", "rag", "multimodal", "content", "validator"]
    gemini_inboxes = [AGENTBUS / "inbox/gemini" / r for r in gemini_roles]
    for inbox_dir in [INBOX_CLAUDE, INBOX_CODEX, *gemini_inboxes]:
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
