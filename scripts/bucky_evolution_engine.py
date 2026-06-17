#!/usr/bin/env python3
"""
Bucky Evolution Engine
자가 학습 루프 오케스트레이터 — 주기적으로 실행하여 시스템을 진화시킴

실행 주기 (권장):
  - P0 Knowledge Capture: 매 세션 종료 시
  - P1 Pattern Extract:   매일 1회
  - P2 Self-Reflect:      매주 1회
"""
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).parent.parent
load_dotenv(ROOT / ".env", encoding="utf-8-sig", override=True)

DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK_URL", "")
SCRIPTS_DIR = ROOT / "scripts"
EVOLUTION_LOG = ROOT / "ObsidianVault" / "09_Knowledge_Capture" / "evolution-log.jsonl"


def _discord(msg: str) -> None:
    if DISCORD_WEBHOOK:
        try:
            requests.post(DISCORD_WEBHOOK, json={"content": msg}, timeout=5)
        except Exception:
            pass


def _run_script(script: str, args: list[str] = None) -> tuple[int, str]:
    cmd = [sys.executable, str(SCRIPTS_DIR / script)] + (args or [])
    result = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
    return result.returncode, (result.stdout + result.stderr).strip()


def log_evolution(phase: str, result: dict) -> None:
    EVOLUTION_LOG.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "phase": phase,
        "result": result,
        "timestamp": datetime.now().isoformat(),
    }
    with EVOLUTION_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def run_p0_capture(source_text: str = "") -> dict:
    """P0: 지식 캡처"""
    if source_text:
        code, out = _run_script("bucky_knowledge_capture.py", ["--text", source_text])
    else:
        # session-state.md에서 캡처
        session_file = ROOT / "ObsidianVault" / "00_System" / "session-state.md"
        if session_file.exists():
            recent_text = session_file.read_text(encoding="utf-8")[-800:]
            code, out = _run_script(
                "bucky_knowledge_capture.py",
                ["--text", recent_text, "--title", "세션 상태 캡처", "--tags", "session,auto-capture"],
            )
        else:
            return {"phase": "P0", "status": "skipped", "reason": "no source"}
    result = {"phase": "P0", "status": "ok" if code == 0 else "error", "output": out[:300]}
    log_evolution("P0_capture", result)
    return result


def run_p1_pattern() -> dict:
    """P1: 패턴 추출"""
    code, out = _run_script("bucky_pattern_extractor.py")
    result = {"phase": "P1", "status": "ok" if code == 0 else "error", "output": out[:300]}
    log_evolution("P1_pattern", result)
    return result


def run_p2_reflection() -> dict:
    """P2: 자기 반성 — 최근 오류/패턴 분석 후 개선 제안"""
    error_logs = list(Path(ROOT / "ObsidianVault" / "09_Knowledge_Capture" / "error").glob("*.md"))
    patterns = list(Path(ROOT / "ObsidianVault" / "09_Knowledge_Capture" / "patterns").glob("*.md"))

    summary = {
        "error_notes": len(error_logs),
        "pattern_notes": len(patterns),
        "suggested_skills": len(list(Path(ROOT / ".claude" / "skills" / "suggested").glob("*.md"))) if (ROOT / ".claude" / "skills" / "suggested").exists() else 0,
    }

    result = {
        "phase": "P2",
        "status": "ok",
        "summary": summary,
        "reflection": f"오류 {summary['error_notes']}건, 패턴 {summary['pattern_notes']}건, 제안 스킬 {summary['suggested_skills']}개 대기 중",
    }

    if summary["suggested_skills"] > 0:
        _discord(
            f"🧬 **자기 반성 리포트**\n"
            f"🔴 오류 기록: {summary['error_notes']}건\n"
            f"🔄 반복 패턴: {summary['pattern_notes']}건\n"
            f"💡 대기 중인 스킬 제안: {summary['suggested_skills']}개\n"
            f"→ `.claude/skills/suggested/` 확인 후 활성화하세요"
        )

    log_evolution("P2_reflection", result)
    return result


def run_full_evolution() -> dict:
    """전체 진화 사이클 실행"""
    _discord("🧬 **Bucky 진화 사이클 시작**\nP0 → P1 → P2 순서로 실행 중...")

    results = {}
    results["P0"] = run_p0_capture()
    results["P1"] = run_p1_pattern()
    results["P2"] = run_p2_reflection()

    success = sum(1 for r in results.values() if r.get("status") == "ok")
    _discord(f"✅ **진화 사이클 완료** ({success}/3 단계 성공)\n버키가 한 단계 더 성장했습니다.")

    return results


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "full"
    if mode == "p0":
        text = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else ""
        print(json.dumps(run_p0_capture(text), ensure_ascii=False, indent=2))
    elif mode == "p1":
        print(json.dumps(run_p1_pattern(), ensure_ascii=False, indent=2))
    elif mode == "p2":
        print(json.dumps(run_p2_reflection(), ensure_ascii=False, indent=2))
    else:
        print(json.dumps(run_full_evolution(), ensure_ascii=False, indent=2))
