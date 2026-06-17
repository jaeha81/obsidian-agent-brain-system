#!/usr/bin/env python3
"""
Bucky Sub-Agent Manager — 복잡한 작업을 서브에이전트에게 분리 위임

역할 분담:
  Bucky        → 조율(오케스트레이터), 지식 정제, 갭 분석
  ClaudeCode   → 구현(코드 작성, 스크립트, 파일 생성)
  Codex        → 검토, 검수, 리뷰, 테스트 검증
  Chris        → Graphify 기반 지식 구조 분석, 브레인 성능 개선 제안
  Collector    → 데이터 수집 파이프라인 실행
  Distiller    → 원시 대화 → 구조화 지식 변환

흐름:
  User Request → classify_complexity() → 단순이면 직접 처리
               → 복잡이면 split_into_subtasks() → dispatch_to_agents()
               → 진행 모니터링 → aggregate_results() → Discord 보고
"""

import json
import os
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
import yaml

_ROOT = Path(__file__).parent.parent
load_dotenv(_ROOT / ".env", encoding="utf-8-sig", override=True)

VAULT = Path(os.getenv("VAULT_PATH", str(_ROOT / "ObsidianVault")))
INBOX = VAULT / "10_AgentBus" / "inbox"
TASKS_DIR = VAULT / "10_AgentBus" / "tasks"

AgentRole = Literal["bucky", "claude_code", "codex", "chris", "collector", "distiller"]

AGENT_CAPABILITIES = {
    "claude_code": [
        "구현", "만들어", "작성", "코드", "스크립트", "파일 생성", "추가", "수정",
        "implement", "create", "build", "add", "fix", "refactor", "write",
    ],
    "codex": [
        "검토", "검수", "리뷰", "테스트", "검증", "확인",
        "review", "verify", "check", "validate", "test",
    ],
    "chris": [
        "chris", "크리스", "graphify", "그래피파이", "그래프파이",
        "지식 그래프", "knowledge graph", "지식 구조", "지식 정리",
        "브레인 성능", "연결성", "고립 노드", "isolated node",
        "context pack 후보", "컨텍스트팩 후보", "지식 갭", "knowledge gap",
    ],
    "collector": [
        "수집", "가져와", "임포트", "동기화",
        "collect", "import", "sync", "fetch",
    ],
    "distiller": [
        "정제", "요약", "변환", "지식화", "분류",
        "distill", "summarize", "transform", "extract knowledge",
    ],
}

_COMPLEX_THRESHOLD = 3  # 서브태스크 감지 시 이 개수 이상이면 분리


def _iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _ts() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def select_agent(task_body: str) -> AgentRole:
    """작업 내용 → 가장 적합한 에이전트 선택"""
    body = task_body.lower()
    scores: dict[AgentRole, int] = {a: 0 for a in AGENT_CAPABILITIES}  # type: ignore[assignment]
    for agent, keywords in AGENT_CAPABILITIES.items():
        for kw in keywords:
            if kw in body:
                scores[agent] += 1  # type: ignore[index]
    best = max(scores, key=lambda a: scores[a])  # type: ignore[arg-type]
    if scores[best] == 0:
        return "bucky"
    return best  # type: ignore[return-value]


def classify_complexity(request: str) -> tuple[bool, list[str]]:
    """
    요청 복잡도 판단 → (is_complex, subtask_list)
    여러 동사/목적이 감지되면 복잡 판단
    """
    # 간단한 분리: '그리고', '또한', '추가로', 줄바꿈 기반
    separators = ["그리고", "또한", "추가로", "그 다음", "\n-", "\n•", " and ", " also "]
    parts = [request]
    for sep in separators:
        new_parts = []
        for p in parts:
            new_parts.extend(p.split(sep))
        parts = new_parts
    subtasks = [p.strip() for p in parts if len(p.strip()) > 10]

    is_complex = len(subtasks) >= _COMPLEX_THRESHOLD
    return is_complex, subtasks if is_complex else [request]


def create_inbox_task(task_id: str, body: str, agent: AgentRole, parent_id: str = "") -> Path:
    """AgentBus inbox에 서브태스크 MD 파일 생성"""
    INBOX.mkdir(parents=True, exist_ok=True)
    ts = _ts()
    filename = f"{ts}_{task_id}_{agent}.md"
    task_path = INBOX / filename

    frontmatter = {
        "task_id": task_id,
        "parent_id": parent_id,
        "agent": agent,
        "status": "pending",
        "created_at": _iso(),
        "body": body[:200],
    }
    content = f"---\n{yaml.dump(frontmatter, allow_unicode=True, default_flow_style=False)}---\n\n{body}\n"
    task_path.write_text(content, encoding="utf-8")
    return task_path


def dispatch_subtasks(request: str, parent_id: str = "") -> list[dict]:
    """
    복잡한 요청 → 서브태스크 분리 → 각 에이전트에 인박스 파일 생성
    반환: 생성된 태스크 목록
    """
    is_complex, subtasks = classify_complexity(request)
    created = []

    for i, task_body in enumerate(subtasks):
        agent = select_agent(task_body)
        task_id = f"{_ts()}_sub{i+1:02d}"
        path = create_inbox_task(task_id, task_body, agent, parent_id=parent_id)
        created.append({
            "task_id": task_id,
            "agent": agent,
            "body": task_body[:100],
            "inbox_path": str(path),
        })
        print(f"[SubAgentMgr] 태스크 생성: {task_id} → {agent}: {task_body[:60]}...")

    return created


def delegate(request: str, parent_id: str = "") -> dict:
    """
    메인 진입점 — 요청을 받아 서브에이전트에게 위임
    Returns summary dict
    """
    is_complex, subtasks = classify_complexity(request)

    if not is_complex:
        agent = select_agent(request)
        print(f"[SubAgentMgr] 단순 태스크 → {agent}에게 직접 위임")
        task_id = f"{_ts()}_single"
        path = create_inbox_task(task_id, request, agent, parent_id=parent_id)
        return {
            "mode": "single",
            "tasks": [{"task_id": task_id, "agent": agent, "body": request[:100], "inbox_path": str(path)}],
        }

    print(f"[SubAgentMgr] 복잡 요청 감지 — {len(subtasks)}개 서브태스크로 분리")
    tasks = dispatch_subtasks(request, parent_id=parent_id)
    return {"mode": "parallel", "tasks": tasks}


def summary_report(delegation_result: dict) -> str:
    """위임 결과 Discord용 요약 문자열 생성"""
    mode = delegation_result["mode"]
    tasks = delegation_result["tasks"]
    lines = [f"**서브에이전트 위임 완료** (모드: {mode})\n"]
    agent_emojis = {
        "claude_code": "🛠️",
        "codex": "🔍",
        "chris": "🧭",
        "collector": "📥",
        "distiller": "🧠",
        "bucky": "🤖",
    }
    for t in tasks:
        emoji = agent_emojis.get(t["agent"], "⚙️")
        lines.append(f"{emoji} `{t['task_id']}` → **{t['agent']}**: {t['body'][:60]}...")
    return "\n".join(lines)


if __name__ == "__main__":
    import sys
    request = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "GPT 세션 수집하고 지식 정제한 다음 갭 분석해서 태스크 등록해줘"
    result = delegate(request)
    print("\n" + summary_report(result))
