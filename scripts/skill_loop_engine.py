"""스킬 개선 루프 엔진.

영상 방법론을 스킬 파이프라인에 적용:
  1. 스킬별 골든 테스트 케이스 유지 (고정 기준점)
  2. 스킬 변경 후 테스트 케이스 통과율 측정
  3. 개선됐으면 유지, 안 됐으면 롤백
  4. 이력을 data/skill_loop_history.json에 저장

사용법:
    python -X utf8 scripts/skill_loop_engine.py --list          # 등록된 스킬 목록
    python -X utf8 scripts/skill_loop_engine.py --eval <skill>  # 특정 스킬 평가
    python -X utf8 scripts/skill_loop_engine.py --record <skill> --score 85 --note "키워드 추가"
    python -X utf8 scripts/skill_loop_engine.py --history       # 전체 이력
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent.parent
SKILLS_DIR = ROOT / ".claude" / "skills"
HISTORY_PATH = ROOT / "data" / "skill_loop_history.json"
TEST_CASES_PATH = ROOT / "data" / "skill_test_cases.json"


# ── 기본 테스트 케이스 정의 ───────────────────────────────────────────────
DEFAULT_TEST_CASES = {
    "wishket_scoring": {
        "description": "위시켓 공고 채점 정확도",
        "golden_set": "data/wishket_golden_set.json",
        "eval_script": "scripts/wishket_eval.py",
        "pass_threshold": 0.80,
    },
    "jh-brain": {
        "description": "브레인 시스템 응답 품질",
        "checklist": [
            "Vault 파일 경로 정확히 참조",
            "YAML 필드 누락 없이 반환",
            "한국어 응답 유지",
        ],
        "pass_threshold": 1.0,
    },
    "jh-deploy": {
        "description": "배포 스킬 안전성",
        "checklist": [
            "배포 전 확인 단계 포함",
            "롤백 절차 명시",
            "환경변수 노출 없음",
        ],
        "pass_threshold": 1.0,
    },
    "wishket_proposal": {
        "description": "위시켓 제안서 생성 품질",
        "checklist": [
            "제안서 길이 300자 이상",
            "프로젝트 요구사항 반영",
            "재하님 기술 스택 언급",
            "예산 범위 명시",
        ],
        "pass_threshold": 0.75,
    },
}


def load_history() -> list[dict]:
    if HISTORY_PATH.exists():
        return json.loads(HISTORY_PATH.read_text(encoding="utf-8"))
    return []


def save_history(history: list[dict]):
    HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    HISTORY_PATH.write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8")


def load_test_cases() -> dict:
    if TEST_CASES_PATH.exists():
        saved = json.loads(TEST_CASES_PATH.read_text(encoding="utf-8"))
        return {**DEFAULT_TEST_CASES, **saved}
    return DEFAULT_TEST_CASES


def list_skills():
    """등록된 스킬과 테스트 케이스 목록 출력."""
    test_cases = load_test_cases()
    skill_files = list(SKILLS_DIR.glob("**/*.md")) if SKILLS_DIR.exists() else []

    print("\n── 스킬 루프 엔진 현황 ─────────────────────────────────────")
    print(f"  스킬 파일 {len(skill_files)}개  |  테스트 케이스 {len(test_cases)}개\n")

    history = load_history()
    latest = {}
    for h in history:
        latest[h["skill"]] = h

    for skill_name, tc in test_cases.items():
        last = latest.get(skill_name)
        if last:
            trend = "↑" if last.get("improved") else "→"
            last_score = f"{last['score']:.0%}" if isinstance(last.get("score"), float) else str(last.get("score", "?"))
            status = f"{trend} 최근: {last_score}  ({last['timestamp'][:10]})"
        else:
            status = "미평가"
        print(f"  [{skill_name}]  {tc['description']}")
        print(f"    임계값: {tc.get('pass_threshold', 0.8):.0%}  |  {status}\n")

    print("────────────────────────────────────────────────────────\n")


def eval_skill(skill_name: str):
    """스킬 평가 — wishket_scoring은 wishket_eval.py 자동 실행, 나머지는 체크리스트."""
    test_cases = load_test_cases()
    if skill_name not in test_cases:
        print(f"'{skill_name}' 테스트 케이스가 없습니다. 등록된 스킬: {list(test_cases.keys())}")
        return

    tc = test_cases[skill_name]
    print(f"\n── {skill_name} 평가 ─────────────────────────────────────")
    print(f"  {tc['description']}")
    print(f"  통과 임계값: {tc.get('pass_threshold', 0.8):.0%}\n")

    if skill_name == "wishket_scoring" and "eval_script" in tc:
        import subprocess
        result = subprocess.run(
            [sys.executable, "-X", "utf8", str(ROOT / tc["eval_script"]), "--verbose"],
            capture_output=True, text=True, encoding="utf-8"
        )
        print(result.stdout)
        if result.returncode != 0:
            print(result.stderr)
    elif "checklist" in tc:
        print("  체크리스트 (수동 평가):")
        for i, item in enumerate(tc["checklist"], 1):
            print(f"    {i}. {item}")
        print(f"\n  --record {skill_name} --score <0-100> --note \"변경 내용\" 으로 점수 기록")

    print("────────────────────────────────────────────────────────\n")


def record_result(skill_name: str, score: float, note: str = ""):
    """평가 결과를 이력에 기록 (루프의 keep/discard 판단 근거)."""
    history = load_history()
    test_cases = load_test_cases()
    threshold = test_cases.get(skill_name, {}).get("pass_threshold", 0.8)

    # 이전 점수와 비교
    prev_scores = [h["score"] for h in history if h["skill"] == skill_name]
    prev_score = prev_scores[-1] if prev_scores else None
    improved = (prev_score is None) or (score > prev_score)

    entry = {
        "timestamp": datetime.now().isoformat(),
        "skill": skill_name,
        "score": score,
        "threshold": threshold,
        "passed": score >= threshold,
        "improved": improved,
        "note": note,
        "prev_score": prev_score,
    }
    history.append(entry)
    save_history(history)

    marker = "✓" if entry["passed"] else "✗"
    trend = "↑ 개선" if improved else ("= 유지" if score == prev_score else "↓ 하락")
    prev_str = f"  이전: {prev_score:.0%}" if prev_score is not None else ""
    print(f"\n  {marker} [{skill_name}]  점수: {score:.0%}  {trend}{prev_str}")
    if note:
        print(f"     메모: {note}")
    print(f"  기록 완료: {HISTORY_PATH}\n")


def print_history():
    history = load_history()
    if not history:
        print("이력 없음.")
        return
    print("\n── 스킬 루프 이력 ──────────────────────────────────────────")
    for h in history:
        marker = "✓" if h.get("passed") else "✗"
        trend = "↑" if h.get("improved") else "↓"
        note_str = f"  '{h['note']}'" if h.get("note") else ""
        print(
            f"  {marker} {h['timestamp'][:16]}  [{h['skill']}]  {h['score']:.0%} {trend}{note_str}"
        )
    print("────────────────────────────────────────────────────────\n")


if __name__ == "__main__":
    args = sys.argv[1:]

    if "--history" in args:
        print_history()
        sys.exit(0)

    if "--list" in args:
        list_skills()
        sys.exit(0)

    if "--eval" in args:
        idx = args.index("--eval")
        skill = args[idx + 1] if idx + 1 < len(args) else ""
        if not skill:
            print("사용법: --eval <skill_name>")
            sys.exit(1)
        eval_skill(skill)
        sys.exit(0)

    if "--record" in args:
        idx = args.index("--record")
        skill = args[idx + 1] if idx + 1 < len(args) else ""
        score = 0.0
        note = ""
        if "--score" in args:
            si = args.index("--score")
            raw = float(args[si + 1]) if si + 1 < len(args) else 0
            score = raw / 100 if raw > 1 else raw
        if "--note" in args:
            ni = args.index("--note")
            note = args[ni + 1] if ni + 1 < len(args) else ""
        if not skill:
            print("사용법: --record <skill_name> --score <0-100> --note \"메모\"")
            sys.exit(1)
        record_result(skill, score, note)
        sys.exit(0)

    print(__doc__)
