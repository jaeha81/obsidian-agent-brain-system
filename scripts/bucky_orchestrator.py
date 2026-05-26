#!/usr/bin/env python3
"""
Bucky Orchestrator (P3) — 복잡한 작업을 에이전트별로 분류·병렬 실행
P0(지식캡처) → P1(패턴감지) → P2(자기반성) 피드백 루프를 통합

사용법:
  python bucky_orchestrator.py --task "구현 작업 설명" --notify
  python bucky_orchestrator.py --run-loop     # 주기적 P1/P2 실행
  python bucky_orchestrator.py --status       # 시스템 상태 확인
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import requests
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# 경로 설정
# ---------------------------------------------------------------------------
ROOT = Path(__file__).parent.parent
load_dotenv(ROOT / ".env", encoding="utf-8", override=True)

VAULT = Path(os.getenv("VAULT_PATH", str(ROOT / "ObsidianVault")))
SCRIPTS_DIR = ROOT / "scripts"

DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK_URL", "")

EVOLUTION_LOG = ROOT / "ObsidianVault" / "09_Knowledge_Capture" / "evolution-log.jsonl"
ORCHESTRATOR_LOG = ROOT / "ObsidianVault" / "09_Knowledge_Capture" / "orchestrator-log.jsonl"

# AgentBus 경로 (bucky_dispatcher.py와 동일 구조)
AGENTBUS = VAULT / "10_AgentBus"
INBOX = AGENTBUS / "inbox"

# ---------------------------------------------------------------------------
# 의도 카테고리
# ---------------------------------------------------------------------------
CATEGORY_CODE = "CODE"
CATEGORY_KNOWLEDGE = "KNOWLEDGE"
CATEGORY_ANALYSIS = "ANALYSIS"
CATEGORY_SYSTEM = "SYSTEM"

# 카테고리별 키워드 (우선순위 높은 순)
INTENT_KEYWORDS: dict[str, list[str]] = {
    CATEGORY_CODE: [
        "구현", "만들어", "작성", "코드", "스크립트", "파일 생성", "추가", "수정", "삭제",
        "리팩토링", "버그", "수정해", "고쳐", "픽스",
        "implement", "create", "build", "add", "fix", "refactor", "write", "code",
        "debug", "patch",
    ],
    CATEGORY_KNOWLEDGE: [
        "저장", "기록", "캡처", "URL", "링크", "요약", "정보 검색", "검색해",
        "노트", "지식", "유튜브", "youtube", "웹페이지", "저장해줘",
        "save", "capture", "note", "knowledge", "url", "summarize", "fetch",
    ],
    CATEGORY_ANALYSIS: [
        "분석", "패턴", "통계", "데이터", "리포트", "보고서", "진단", "평가",
        "얼마나", "얼마", "현황", "트렌드",
        "analyze", "analysis", "pattern", "report", "statistics", "diagnose", "evaluate",
    ],
    CATEGORY_SYSTEM: [
        "배포", "설정", "시스템", "환경", "설치", "업그레이드", "마이그레이션",
        "서버", "도커", "vercel", "railway", "github actions",
        "deploy", "config", "system", "setup", "install", "migrate", "docker",
    ],
}

# 카테고리 → 에이전트 매핑
CATEGORY_TO_AGENTS: dict[str, list[str]] = {
    CATEGORY_CODE: ["claude_code"],
    CATEGORY_KNOWLEDGE: ["bucky_knowledge_capture"],
    CATEGORY_ANALYSIS: ["bucky_pattern_extractor", "bucky_self_reflection"],
    CATEGORY_SYSTEM: ["bucky_dispatcher"],
}

# 카테고리 → 실행 스크립트 매핑 (직접 실행 가능한 경우)
AGENT_SCRIPTS: dict[str, str] = {
    "bucky_knowledge_capture": "bucky_knowledge_capture.py",
    "bucky_pattern_extractor": "bucky_pattern_extractor.py",
    "bucky_self_reflection": "bucky_self_reflection.py",
}


# ---------------------------------------------------------------------------
# 내부 유틸
# ---------------------------------------------------------------------------

def _iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _ts() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _discord(msg: str) -> None:
    """Discord webhook으로 메시지 전송. 실패해도 예외 전파 없음."""
    if not DISCORD_WEBHOOK:
        return
    try:
        requests.post(DISCORD_WEBHOOK, json={"content": msg}, timeout=5)
    except Exception:
        pass


def _run_script(script_name: str, args: list[str] | None = None) -> tuple[int, str]:
    """서브스크립트 실행. (returncode, stdout+stderr) 반환."""
    cmd = [sys.executable, str(SCRIPTS_DIR / script_name)] + (args or [])
    result = subprocess.run(
        cmd, cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8"
    )
    output = (result.stdout + result.stderr).strip()
    return result.returncode, output


def _log_orchestrator(event: str, data: dict) -> None:
    """오케스트레이터 이벤트 JSONL 로그."""
    ORCHESTRATOR_LOG.parent.mkdir(parents=True, exist_ok=True)
    entry = {"event": event, "data": data, "timestamp": _iso()}
    with ORCHESTRATOR_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------------------
# 1. IntentClassifier
# ---------------------------------------------------------------------------

class IntentClassifier:
    """사용자 요청 텍스트 → 카테고리 분류."""

    @staticmethod
    def classify(text: str) -> dict:
        """
        Parameters
        ----------
        text : str
            사용자 요청 원문

        Returns
        -------
        dict
            {
              "action": str,       # 핵심 동사 (감지된 첫 번째 키워드)
              "category": str,     # CODE | KNOWLEDGE | ANALYSIS | SYSTEM
              "confidence": float, # 0.0 ~ 1.0
              "scores": dict,      # 카테고리별 점수
            }
        """
        body = text.lower()
        scores: dict[str, int] = {cat: 0 for cat in INTENT_KEYWORDS}
        first_action: dict[str, str] = {}

        for cat, keywords in INTENT_KEYWORDS.items():
            for kw in keywords:
                if kw in body:
                    scores[cat] += 1
                    if cat not in first_action:
                        first_action[cat] = kw

        best_cat = max(scores, key=lambda c: scores[c])
        best_score = scores[best_cat]
        total = sum(scores.values()) or 1
        confidence = round(best_score / total, 2)

        # 점수가 0이면 CODE로 기본 처리 (구현 에이전트가 fallback)
        if best_score == 0:
            best_cat = CATEGORY_CODE
            confidence = 0.1

        return {
            "action": first_action.get(best_cat, text[:30]),
            "category": best_cat,
            "confidence": confidence,
            "scores": scores,
        }


# ---------------------------------------------------------------------------
# 2. AgentRouter
# ---------------------------------------------------------------------------

class AgentRouter:
    """의도 카테고리 → 에이전트 선택 및 실행."""

    def route(self, intent: dict, task: str) -> dict:
        """
        Parameters
        ----------
        intent : dict
            IntentClassifier.classify() 결과
        task : str
            원본 사용자 요청

        Returns
        -------
        dict
            {
              "category": str,
              "agents": list[str],
              "results": list[dict],  # 각 에이전트 실행 결과
            }
        """
        category = intent["category"]
        agents = CATEGORY_TO_AGENTS.get(category, ["bucky_dispatcher"])

        results = []
        for agent in agents:
            result = self._execute_agent(agent, task, category)
            results.append(result)

        return {
            "category": category,
            "agents": agents,
            "results": results,
        }

    def _execute_agent(self, agent: str, task: str, category: str) -> dict:
        """에이전트별 실행 로직."""
        script = AGENT_SCRIPTS.get(agent)

        # 스크립트가 존재하는 에이전트는 직접 실행
        if script and (SCRIPTS_DIR / script).exists():
            if agent == "bucky_knowledge_capture":
                code, out = _run_script(script, ["--text", task])
            else:
                code, out = _run_script(script)
            return {
                "agent": agent,
                "status": "ok" if code == 0 else "error",
                "output": out[:400],
            }

        # claude_code / bucky_dispatcher: AgentBus inbox에 태스크 생성
        if agent in ("claude_code", "bucky_dispatcher"):
            return self._create_inbox_task(agent, task, category)

        # 스크립트 없는 경우 — 태스크 파일만 생성
        return self._create_inbox_task(agent, task, category)

    @staticmethod
    def _create_inbox_task(agent: str, task: str, category: str) -> dict:
        """AgentBus inbox에 MD 태스크 파일 생성."""
        inbox_dir = INBOX / agent
        inbox_dir.mkdir(parents=True, exist_ok=True)

        task_id = f"{_ts()}_{category.lower()}"
        filename = f"{task_id}.md"
        task_path = inbox_dir / filename

        content = (
            f"---\n"
            f"task_id: {task_id}\n"
            f"agent: {agent}\n"
            f"category: {category}\n"
            f"status: pending\n"
            f"created_at: {_iso()}\n"
            f"---\n\n"
            f"{task}\n"
        )
        task_path.write_text(content, encoding="utf-8")

        return {
            "agent": agent,
            "status": "queued",
            "task_id": task_id,
            "inbox_path": str(task_path),
            "output": f"태스크 생성 완료: {task_path.name}",
        }


# ---------------------------------------------------------------------------
# 3. 피드백 루프 (P1 + P2)
# ---------------------------------------------------------------------------

def run_feedback_loop() -> dict:
    """
    P1 패턴 추출 → P2 자기 반성 순차 실행.
    bucky_evolution_engine.py 의 P1/P2를 직접 호출한다.

    Returns
    -------
    dict
        {"P1": ..., "P2": ...}
    """
    print("[Orchestrator] 피드백 루프 시작: P1 → P2")

    # P1 패턴 추출
    p1_code, p1_out = _run_script("bucky_pattern_extractor.py")
    p1_result = {
        "phase": "P1",
        "status": "ok" if p1_code == 0 else "error",
        "output": p1_out[:400],
    }
    print(f"[Orchestrator] P1 완료: {p1_result['status']}")

    # P2 자기 반성
    p2_code, p2_out = _run_script("bucky_self_reflection.py")
    p2_result = {
        "phase": "P2",
        "status": "ok" if p2_code == 0 else "error",
        "output": p2_out[:400],
    }
    print(f"[Orchestrator] P2 완료: {p2_result['status']}")

    results = {"P1": p1_result, "P2": p2_result}
    _log_orchestrator("feedback_loop", results)
    return results


# ---------------------------------------------------------------------------
# 4. 시스템 상태
# ---------------------------------------------------------------------------

def get_system_status() -> dict:
    """
    각 Phase 상태 요약.

    Returns
    -------
    dict
        P0 ~ P3 각 항목의 파일 존재 여부 및 카운트
    """
    raw_dir = VAULT / "01_RAW"
    patterns_dir = VAULT / "09_Knowledge_Capture" / "patterns"
    reflection_dir = VAULT / "09_Knowledge_Capture" / "self-reflection"
    error_dir = VAULT / "09_Knowledge_Capture" / "error"
    suggested_skills_dir = ROOT / ".claude" / "skills" / "suggested"
    inbox_dir = INBOX

    def _count(path: Path, glob: str = "*.md") -> int:
        return len(list(path.glob(glob))) if path.exists() else 0

    def _last_modified(path: Path, glob: str = "*.md") -> str:
        files = sorted(path.glob(glob)) if path.exists() else []
        if not files:
            return "없음"
        latest = max(files, key=lambda f: f.stat().st_mtime)
        mtime = datetime.fromtimestamp(latest.stat().st_mtime)
        return mtime.strftime("%Y-%m-%d %H:%M")

    # 스크립트 존재 여부
    scripts = {
        "bucky_knowledge_capture.py": (SCRIPTS_DIR / "bucky_knowledge_capture.py").exists(),
        "bucky_pattern_extractor.py": (SCRIPTS_DIR / "bucky_pattern_extractor.py").exists(),
        "bucky_self_reflection.py": (SCRIPTS_DIR / "bucky_self_reflection.py").exists(),
        "bucky_evolution_engine.py": (SCRIPTS_DIR / "bucky_evolution_engine.py").exists(),
        "bucky_sub_agent_manager.py": (SCRIPTS_DIR / "bucky_sub_agent_manager.py").exists(),
        "bucky_orchestrator.py": (SCRIPTS_DIR / "bucky_orchestrator.py").exists(),
    }

    # 인박스 큐 카운트
    inbox_counts: dict[str, int] = {}
    if inbox_dir.exists():
        for agent_dir in inbox_dir.iterdir():
            if agent_dir.is_dir():
                inbox_counts[agent_dir.name] = _count(agent_dir)

    status = {
        "timestamp": _iso(),
        "phases": {
            "P0_knowledge_capture": {
                "raw_notes": _count(raw_dir),
                "last_captured": _last_modified(raw_dir),
                "script_ok": scripts["bucky_knowledge_capture.py"],
            },
            "P1_pattern_extractor": {
                "pattern_reports": _count(patterns_dir),
                "last_report": _last_modified(patterns_dir),
                "suggested_skills": _count(suggested_skills_dir),
                "script_ok": scripts["bucky_pattern_extractor.py"],
            },
            "P2_self_reflection": {
                "reflection_reports": _count(reflection_dir),
                "error_notes": _count(error_dir),
                "last_reflection": _last_modified(reflection_dir),
                "script_ok": scripts["bucky_self_reflection.py"],
            },
            "P3_orchestrator": {
                "script_ok": scripts["bucky_orchestrator.py"],
                "evolution_engine_ok": scripts["bucky_evolution_engine.py"],
                "sub_agent_manager_ok": scripts["bucky_sub_agent_manager.py"],
                "inbox_queue": inbox_counts,
            },
        },
        "discord_webhook_configured": bool(DISCORD_WEBHOOK),
        "vault_path": str(VAULT),
    }
    return status


# ---------------------------------------------------------------------------
# 5. 메인 오케스트레이션 진입점
# ---------------------------------------------------------------------------

def orchestrate(task: str, notify: bool = True) -> dict:
    """
    사용자 태스크를 받아 의도 분류 → 에이전트 라우팅 → 피드백 루프 결정까지 실행.

    Parameters
    ----------
    task : str
        사용자 요청 텍스트
    notify : bool
        Discord webhook 알림 여부

    Returns
    -------
    dict
        {
          "task": str,
          "intent": dict,
          "routing": dict,
          "feedback_triggered": bool,
          "feedback_result": dict | None,
        }
    """
    print(f"[Orchestrator] 태스크 수신: {task[:80]}...")

    # 1. 의도 분류
    intent = IntentClassifier.classify(task)
    category = intent["category"]
    print(f"[Orchestrator] 의도 분류: {category} (신뢰도 {intent['confidence']})")

    # 2. 에이전트 라우팅
    router = AgentRouter()
    routing = router.route(intent, task)
    print(f"[Orchestrator] 라우팅 완료: {routing['agents']}")

    # 3. Discord 시작 알림
    if notify:
        _discord(
            f"🤖 **Bucky Orchestrator** 작업 시작\n"
            f"📋 카테고리: `{category}`\n"
            f"🔧 에이전트: {', '.join(routing['agents'])}\n"
            f"📝 요청: {task[:120]}"
        )

    # 4. 피드백 루프 트리거 결정
    # ANALYSIS/SYSTEM 카테고리이거나, KNOWLEDGE 캡처 성공 시 P1/P2 실행
    should_run_feedback = category in (CATEGORY_ANALYSIS, CATEGORY_KNOWLEDGE)
    feedback_result = None

    if should_run_feedback:
        print("[Orchestrator] 피드백 루프 자동 트리거 (P1 → P2)")
        feedback_result = run_feedback_loop()

    # 5. Discord 완료 알림
    agent_statuses = [
        f"{'✅' if r.get('status') in ('ok', 'queued') else '❌'} `{r['agent']}`: {r['status']}"
        for r in routing["results"]
    ]

    if notify:
        feedback_msg = ""
        if feedback_result:
            p1_ok = feedback_result.get("P1", {}).get("status") == "ok"
            p2_ok = feedback_result.get("P2", {}).get("status") == "ok"
            feedback_msg = (
                f"\n🔄 피드백 루프: P1={'✅' if p1_ok else '❌'} P2={'✅' if p2_ok else '❌'}"
            )

        _discord(
            f"✅ **Bucky Orchestrator** 완료\n"
            + "\n".join(agent_statuses)
            + feedback_msg
        )

    result = {
        "task": task,
        "intent": intent,
        "routing": routing,
        "feedback_triggered": should_run_feedback,
        "feedback_result": feedback_result,
    }

    _log_orchestrator("orchestrate", {
        "category": category,
        "agents": routing["agents"],
        "feedback_triggered": should_run_feedback,
    })

    return result


# ---------------------------------------------------------------------------
# 6. CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Bucky Orchestrator (P3) — 복잡한 작업을 에이전트별로 분류·실행",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:
  python bucky_orchestrator.py --task "Discord 봇 명령어 추가 구현해줘" --notify
  python bucky_orchestrator.py --task "유튜브 영상 URL 저장해줘"
  python bucky_orchestrator.py --run-loop
  python bucky_orchestrator.py --status
        """,
    )

    parser.add_argument("--task", type=str, help="처리할 작업 설명")
    parser.add_argument(
        "--notify",
        action="store_true",
        default=False,
        help="Discord webhook 알림 활성화",
    )
    parser.add_argument(
        "--run-loop",
        action="store_true",
        default=False,
        help="P1(패턴) + P2(자기반성) 피드백 루프 즉시 실행",
    )
    parser.add_argument(
        "--status",
        action="store_true",
        default=False,
        help="시스템 상태 요약 출력",
    )
    parser.add_argument(
        "--classify",
        type=str,
        metavar="TEXT",
        help="의도 분류만 수행 (에이전트 실행 없음)",
    )

    args = parser.parse_args()

    # --status
    if args.status:
        status = get_system_status()
        print(json.dumps(status, ensure_ascii=False, indent=2))
        return

    # --run-loop
    if args.run_loop:
        result = run_feedback_loop()
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    # --classify
    if args.classify:
        intent = IntentClassifier.classify(args.classify)
        print(json.dumps(intent, ensure_ascii=False, indent=2))
        return

    # --task (메인 오케스트레이션)
    if args.task:
        result = orchestrate(args.task, notify=args.notify)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    # 인자 없이 실행 시 도움말
    parser.print_help()


if __name__ == "__main__":
    main()
