"""Wishket 루프 엔진 — 스코어링 파라미터 자동 진화.

영상 방법론 적용:
  1. 평가(Evaluate) → 골든 셋으로 현재 정확도 측정
  2. 하나만 변경(Change One) → 키워드 가중치 or 예산 임계값 or 우선순위 컷 중 하나
  3. 검증(Verify) → 같은 골든 셋으로 재측정
  4. 합치기/버리기(Keep/Discard) → 정확도 올랐으면 반영, 아니면 롤백

평가자(wishket_eval.py) ≠ 실행자(wishket_scorer.py) 분리 원칙 유지.

사용법:
    python -X utf8 scripts/wishket_loop.py --run       # 루프 1회 실행
    python -X utf8 scripts/wishket_loop.py --baseline  # 현재 베이스라인만 출력
    python -X utf8 scripts/wishket_loop.py --history   # 이력 출력
    python -X utf8 scripts/wishket_loop.py --run --n 5 # 루프 5회 연속
"""

from __future__ import annotations

import copy
import json
import random
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import wishket_scorer as scorer  # noqa: E402
from wishket_eval import evaluate, load_golden_set  # noqa: E402

HISTORY_PATH = ROOT / "data" / "wishket_loop_history.json"


# ── 변경 가능한 파라미터 후보 ─────────────────────────────────────────────
CHANGE_CANDIDATES = [
    # (type, description, apply_fn, revert_fn)
    # 키워드 HIGH 가중치 +1
    {
        "id": "high_weight_up",
        "desc": "HIGH 키워드 가중치 3→4",
        "apply": lambda: setattr(scorer, "_HIGH_W", 4),
        "revert": lambda: setattr(scorer, "_HIGH_W", 3),
    },
    # 키워드 MED 가중치 +1
    {
        "id": "med_weight_up",
        "desc": "MED 키워드 가중치 2→3",
        "apply": lambda: setattr(scorer, "_MED_W", 3),
        "revert": lambda: setattr(scorer, "_MED_W", 2),
    },
    # P1 커트 65점으로 낮춤
    {
        "id": "p1_cut_65",
        "desc": "P1 컷오프 70→65점",
        "apply": lambda: setattr(scorer, "_P1_CUT", 65),
        "revert": lambda: setattr(scorer, "_P1_CUT", 70),
    },
    # P1 커트 75점으로 높임
    {
        "id": "p1_cut_75",
        "desc": "P1 컷오프 70→75점",
        "apply": lambda: setattr(scorer, "_P1_CUT", 75),
        "revert": lambda: setattr(scorer, "_P1_CUT", 75),
    },
    # P2 커트 45점으로 낮춤
    {
        "id": "p2_cut_45",
        "desc": "P2 컷오프 50→45점",
        "apply": lambda: setattr(scorer, "_P2_CUT", 45),
        "revert": lambda: setattr(scorer, "_P2_CUT", 50),
    },
    # AI 카테고리 보너스 +5
    {
        "id": "ai_bonus_30",
        "desc": "AI 카테고리 보너스 25→30점",
        "apply": lambda: setattr(scorer, "_AI_BONUS", 30),
        "revert": lambda: setattr(scorer, "_AI_BONUS", 25),
    },
    # 인테리어 보너스 -3
    {
        "id": "interior_bonus_15",
        "desc": "인테리어 카테고리 보너스 18→15점",
        "apply": lambda: setattr(scorer, "_INTERIOR_BONUS", 15),
        "revert": lambda: setattr(scorer, "_INTERIOR_BONUS", 18),
    },
]


def _patch_scorer():
    """scorer에 패치 가능한 상수를 추가 (없으면 원본 로직 사용)."""
    if not hasattr(scorer, "_HIGH_W"):
        scorer._HIGH_W = 3
    if not hasattr(scorer, "_MED_W"):
        scorer._MED_W = 2
    if not hasattr(scorer, "_P1_CUT"):
        scorer._P1_CUT = 70
    if not hasattr(scorer, "_P2_CUT"):
        scorer._P2_CUT = 50
    if not hasattr(scorer, "_AI_BONUS"):
        scorer._AI_BONUS = 25
    if not hasattr(scorer, "_INTERIOR_BONUS"):
        scorer._INTERIOR_BONUS = 18

    # 패치된 버전의 _keyword_score 주입
    def _patched_keyword_score(combined: str) -> int:
        pts = 0
        for kw in scorer._HIGH:
            if kw in combined:
                pts += scorer._HIGH_W
        for kw in scorer._MED:
            if kw in combined:
                pts += scorer._MED_W
        for kw in scorer._LOW:
            if kw in combined:
                pts += 1
        return min(pts, 30)

    def _patched_category_bonus(combined: str) -> int:
        for kw in scorer._PENALTY:
            if kw in combined:
                return -10
        ai_match = sum(1 for kw in ["ai", "llm", "claude", "gpt", "에이전트", "생성형", "인공지능"] if kw in combined)
        if ai_match >= 1:
            return scorer._AI_BONUS
        auto_match = sum(1 for kw in ["자동화", "봇", "에이전트", "크롤링", "스크래핑", "수집엔진", "파이프라인"] if kw in combined)
        if auto_match >= 1:
            return 20
        interior_match = sum(1 for kw in scorer._INTERIOR if kw in combined)
        if interior_match >= 1:
            return scorer._INTERIOR_BONUS
        web_match = sum(1 for kw in ["웹", "fastapi", "django", "flask"] if kw in combined)
        if web_match >= 1:
            return 12
        return 5

    def _patched_score_project(project: dict) -> dict:
        title = scorer._lower(project.get("title", ""))
        description = scorer._lower(project.get("description", ""))
        budget_wan = project.get("budget_wan", 0) or 0
        combined = title + " " + description

        budget_pts = scorer._budget_score(budget_wan)
        keyword_pts = _patched_keyword_score(combined)
        category_pts = _patched_category_bonus(combined)
        desc_pts = scorer._desc_score(project.get("description", ""))

        raw = budget_pts + keyword_pts + category_pts + desc_pts
        score = max(0, min(100, raw))

        p1_cut = getattr(scorer, "_P1_CUT", 70)
        p2_cut = getattr(scorer, "_P2_CUT", 50)

        if score >= p1_cut:
            priority = "P1"
        elif score >= p2_cut:
            priority = "P2"
        elif score >= 30:
            priority = "P3"
        else:
            priority = "P4"

        return {
            **project,
            "score": score,
            "priority": priority,
            "score_breakdown": {
                "budget": budget_pts,
                "keyword": keyword_pts,
                "category": category_pts,
                "description": desc_pts,
            },
        }

    scorer.score_project = _patched_score_project


def load_history() -> list[dict]:
    if HISTORY_PATH.exists():
        return json.loads(HISTORY_PATH.read_text(encoding="utf-8"))
    return []


def save_history(history: list[dict]):
    HISTORY_PATH.write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8")


def run_loop(n: int = 1, verbose: bool = True) -> list[dict]:
    _patch_scorer()
    golden_set = load_golden_set()
    history = load_history()

    results = []
    for i in range(n):
        baseline = evaluate(golden_set)
        baseline_f1 = baseline["f1"]
        baseline_acc = baseline["accuracy"]

        if verbose:
            print(f"\n[루프 {i+1}/{n}] 베이스라인: 정확도 {baseline_acc:.1%}  F1 {baseline_f1:.3f}")

        # 이미 시도한 변경 제외
        tried_ids = {h["change_id"] for h in history}
        candidates = [c for c in CHANGE_CANDIDATES if c["id"] not in tried_ids]

        if not candidates:
            if verbose:
                print("  모든 변경 후보를 소진했습니다. 루프 종료.")
            break

        change = random.choice(candidates)
        if verbose:
            print(f"  시도: {change['desc']}")

        # 변경 적용
        change["apply"]()
        after = evaluate(golden_set)
        after_f1 = after["f1"]
        after_acc = after["accuracy"]

        improved = after_f1 > baseline_f1
        if verbose:
            marker = "✓ 개선" if improved else "✗ 미개선"
            print(f"  결과: {marker} — 정확도 {after_acc:.1%}  F1 {after_f1:.3f}")

        if improved:
            action = "kept"
            if verbose:
                print(f"  → 변경 유지: {change['desc']}")
        else:
            change["revert"]()
            action = "discarded"
            if verbose:
                print(f"  → 롤백: 이전 설정 복원")

        entry = {
            "timestamp": datetime.now().isoformat(),
            "change_id": change["id"],
            "change_desc": change["desc"],
            "baseline_f1": round(baseline_f1, 4),
            "after_f1": round(after_f1, 4),
            "baseline_acc": round(baseline_acc, 4),
            "after_acc": round(after_acc, 4),
            "action": action,
        }
        history.append(entry)
        results.append(entry)

    save_history(history)
    return results


def print_history():
    history = load_history()
    if not history:
        print("이력 없음.")
        return
    print("\n── 위시켓 루프 이력 ────────────────────────────────────────")
    for h in history:
        marker = "✓" if h["action"] == "kept" else "✗"
        delta = h["after_f1"] - h["baseline_f1"]
        sign = "+" if delta >= 0 else ""
        print(
            f"  {marker} {h['timestamp'][:16]}  {h['change_desc']:<40}"
            f"  F1 {h['baseline_f1']:.3f}→{h['after_f1']:.3f} ({sign}{delta:.3f})  [{h['action']}]"
        )
    print("────────────────────────────────────────────────────────\n")


if __name__ == "__main__":
    args = sys.argv[1:]

    if "--history" in args:
        print_history()
        sys.exit(0)

    if "--baseline" in args:
        _patch_scorer()
        golden_set = load_golden_set()
        evaluate(golden_set, verbose=True)
        sys.exit(0)

    if "--run" in args:
        n = 1
        if "--n" in args:
            idx = args.index("--n")
            n = int(args[idx + 1]) if idx + 1 < len(args) else 1
        run_loop(n=n, verbose=True)
        sys.exit(0)

    print(__doc__)
