#!/usr/bin/env python3
"""
세션 종료 시 자동 실행되는 훅.
P1 Pattern Extractor + P2 Self-Reflection을 순차 실행하고
결과를 ObsidianVault/00_System/session-end-log.md에 기록한다.

사용법:
    python scripts/session_end_hook.py [--quiet]

    --quiet   Discord 알림 없이 실행 (CI / 자동화 용도)
"""
import argparse
import json
import os
import sys
import traceback
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent.parent
VAULT = ROOT / "ObsidianVault"
SESSION_LOG = VAULT / "00_System" / "session-end-log.md"

# scripts 디렉토리를 path에 추가해 형제 모듈 import 가능하게 함
SCRIPTS_DIR = str(Path(__file__).parent)
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

# 패턴 추출 시 메시지별 Claude API 호출(NLP 강화)을 억제한다.
# 319개 메시지를 일일이 API 호출하면 과금·시간 낭비가 발생하므로
# session_end_hook 컨텍스트에서는 규칙 기반 분류만 사용한다.
os.environ.setdefault("NLP_ENHANCE", "0")


def _run_pattern_extractor(notify_discord: bool) -> dict:
    try:
        import bucky_pattern_extractor as pe
        result = pe.run(notify_discord=notify_discord)
        return {"status": "ok", "patterns": len(result.get("patterns", [])), "suggestions": len(result.get("suggestions", []))}
    except Exception as e:
        return {"status": "error", "error": str(e), "trace": traceback.format_exc(limit=3)}


def _run_self_reflection(notify_discord: bool) -> dict:
    try:
        import bucky_self_reflection as sr
        result = sr.run(notify_discord=notify_discord)
        return {"status": "ok", "path": result.get("path", "")}
    except Exception as e:
        return {"status": "error", "error": str(e), "trace": traceback.format_exc(limit=3)}


def _append_log(now: datetime, p1: dict, p2: dict) -> Path:
    """session-end-log.md에 세션 종료 결과를 추가한다."""
    SESSION_LOG.parent.mkdir(parents=True, exist_ok=True)

    p1_line = (
        f"패턴 {p1['patterns']}개 감지, 스킬 제안 {p1['suggestions']}개"
        if p1["status"] == "ok"
        else f"오류: {p1['error']}"
    )
    p2_line = (
        f"저장: `{Path(p2['path']).name}`"
        if p2["status"] == "ok"
        else f"오류: {p2['error']}"
    )

    entry = (
        f"\n## {now.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        f"| 단계 | 결과 |\n"
        f"|------|------|\n"
        f"| P1 패턴 추출 | {p1_line} |\n"
        f"| P2 자기 반성 | {p2_line} |\n"
    )

    with SESSION_LOG.open("a", encoding="utf-8") as f:
        # 파일이 없거나 비어있으면 헤더를 먼저 기록
        if SESSION_LOG.stat().st_size == 0 if SESSION_LOG.exists() else True:
            f.write("# 세션 종료 훅 로그\n\n")
        f.write(entry)

    return SESSION_LOG


def main() -> None:
    parser = argparse.ArgumentParser(description="Bucky 세션 종료 훅 (P1 + P2)")
    parser.add_argument("--quiet", action="store_true", help="Discord 알림 없이 실행")
    args = parser.parse_args()

    notify = not args.quiet
    now = datetime.now()

    print(f"[session_end_hook] 실행 시작: {now.strftime('%Y-%m-%d %H:%M:%S')}", flush=True)
    print(f"[session_end_hook] Discord 알림: {'OFF (--quiet)' if not notify else 'ON'}", flush=True)

    # P1: 패턴 추출
    print("\n[P1] bucky_pattern_extractor 실행...", flush=True)
    p1 = _run_pattern_extractor(notify)
    if p1["status"] == "ok":
        print(f"[P1] 완료 — 패턴 {p1['patterns']}개, 제안 {p1['suggestions']}개", flush=True)
    else:
        print(f"[P1] 오류: {p1['error']}", flush=True)

    # P2: 자기 반성
    print("\n[P2] bucky_self_reflection 실행...", flush=True)
    p2 = _run_self_reflection(notify)
    if p2["status"] == "ok":
        print(f"[P2] 완료 — {p2['path']}", flush=True)
    else:
        print(f"[P2] 오류: {p2['error']}", flush=True)

    # 결과 로그 기록
    log_path = _append_log(now, p1, p2)
    print(f"\n[session_end_hook] 로그 기록: {log_path}", flush=True)

    # 요약 출력
    summary = {
        "timestamp": now.isoformat(),
        "p1_pattern_extractor": p1,
        "p2_self_reflection": p2,
        "log": str(log_path),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2, default=str))

    # 어느 한 단계라도 오류 시 exit code 1
    if p1["status"] == "error" or p2["status"] == "error":
        sys.exit(1)


if __name__ == "__main__":
    main()
