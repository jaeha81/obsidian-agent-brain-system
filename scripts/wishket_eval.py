"""Wishket 골든 셋 평가기 (루프 엔진의 독립 채점자).

평가자 AI ≠ 실행자 AI 원칙 — 이 스크립트는 wishket_scorer.py를 호출하지만
채점 기준(골든 셋)은 독립적으로 관리한다.

사용법:
    python -X utf8 scripts/wishket_eval.py
    python -X utf8 scripts/wishket_eval.py --verbose
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from wishket_scorer import score_project  # noqa: E402

GOLDEN_SET_PATH = ROOT / "data" / "wishket_golden_set.json"


def load_golden_set() -> list[dict]:
    return json.loads(GOLDEN_SET_PATH.read_text(encoding="utf-8"))


def evaluate(golden_set: list[dict], verbose: bool = False) -> dict:
    """골든 셋 전체를 채점하고 정확도 지표를 반환."""
    results = []
    for item in golden_set:
        scored = score_project(item)
        predicted_recommend = scored["priority"] in ("P1", "P2")
        correct = predicted_recommend == item["should_recommend"]
        results.append({
            "id": item["id"],
            "title": item["title"][:45],
            "expected_priority": item["expected_priority"],
            "actual_priority": scored["priority"],
            "score": scored["score"],
            "should_recommend": item["should_recommend"],
            "predicted_recommend": predicted_recommend,
            "correct": correct,
            "breakdown": scored["score_breakdown"],
        })

    total = len(results)
    correct_count = sum(1 for r in results if r["correct"])
    accuracy = correct_count / total if total > 0 else 0.0

    # P1/P2 예측 정밀도 & 재현율
    tp = sum(1 for r in results if r["predicted_recommend"] and r["should_recommend"])
    fp = sum(1 for r in results if r["predicted_recommend"] and not r["should_recommend"])
    fn = sum(1 for r in results if not r["predicted_recommend"] and r["should_recommend"])

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0

    if verbose:
        print("\n── Wishket 골든 셋 평가 결과 ──────────────────────────────")
        for r in results:
            mark = "✓" if r["correct"] else "✗"
            recommend_str = "추천" if r["predicted_recommend"] else "제외"
            expected_str = "추천" if r["should_recommend"] else "제외"
            print(
                f"  {mark} [{r['actual_priority']}] {r['score']:3d}점  "
                f"예측:{recommend_str} / 정답:{expected_str}  — {r['title']}"
            )
        print(f"\n  정확도: {accuracy:.1%}  ({correct_count}/{total})")
        print(f"  정밀도: {precision:.1%}  재현율: {recall:.1%}  F1: {f1:.3f}")
        print("────────────────────────────────────────────────────────\n")

    return {
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "correct": correct_count,
        "total": total,
        "results": results,
    }


if __name__ == "__main__":
    verbose = "--verbose" in sys.argv or "-v" in sys.argv
    golden_set = load_golden_set()
    metrics = evaluate(golden_set, verbose=True)
    if not verbose:
        print(f"정확도: {metrics['accuracy']:.1%}  F1: {metrics['f1']:.3f}  ({metrics['correct']}/{metrics['total']})")
