"""
D4: 중복 계상 탐지
같은 내역서 내에서 동일하거나 매우 유사한 항목을 찾는다.
- 완전 중복: 모델No. + 단위 + 수량이 동일 → RED
- 유사 중복: (명칭 + 규격) 유사도 ≥ 0.85   → YELLOW
difflib.SequenceMatcher 사용 (외부 라이브러리 불필요).
"""
from __future__ import annotations

from difflib import SequenceMatcher
from typing import List


_SIMILARITY_THRESHOLD = 0.85


def _text_similarity(a: str, b: str) -> float:
    """두 문자열의 SequenceMatcher 유사도 (0.0 ~ 1.0)."""
    return SequenceMatcher(None, a, b).ratio()


def analyze(rows: List[dict]) -> List[dict]:
    """
    Args:
        rows: 전체내역서 정규화 row 리스트

    Returns:
        findings 리스트. 각 항목:
        {
          "id":         "D4-NNN",
          "dimension":  "D4",
          "severity":   "RED" | "YELLOW",
          "message":    str,
          "row_index":  int,
          "pair_index": int
        }
    """
    findings: List[dict] = []
    counter = 1

    # 유효 행만 인덱스와 함께 추출 (name 또는 model_no가 있는 행)
    valid_rows = [
        (i, r) for i, r in enumerate(rows)
        if r.get("name") or r.get("model_no")
    ]

    seen_exact: dict = {}  # (model_no, unit, quantity) -> row_index

    for i, (orig_i, row) in enumerate(valid_rows):
        # ── 완전 중복 체크 ──────────────────────────────────
        mn = row.get("model_no") or ""
        unit = row.get("unit") or ""
        qty = row.get("quantity", 0.0)

        if mn:  # 모델No. 없는 행은 완전 중복 체크 불가
            key = (mn, unit, qty)
            if key in seen_exact:
                pair_row_idx = seen_exact[key]
                findings.append({
                    "id":         f"D4-{counter:03d}",
                    "dimension":  "D4",
                    "severity":   "RED",
                    "message": (
                        f"[완전중복] 모델No.='{mn}', 단위='{unit}', 수량={qty} — "
                        f"행 {pair_row_idx}와 행 {row['row_index']} 중복"
                    ),
                    "row_index":  row["row_index"],
                    "pair_index": pair_row_idx,
                })
                counter += 1
            else:
                seen_exact[key] = row["row_index"]

        # ── 유사 중복 체크 ──────────────────────────────────
        # 현재 행 이전 행들과만 비교 (조합 중복 방지)
        name_i = (row.get("name") or "") + " " + (row.get("spec") or "")
        name_i = name_i.strip()

        for _, (_, prev_row) in enumerate(valid_rows[:i]):
            name_j = (prev_row.get("name") or "") + " " + (prev_row.get("spec") or "")
            name_j = name_j.strip()

            if not name_i or not name_j:
                continue

            sim = _text_similarity(name_i, name_j)
            if sim >= _SIMILARITY_THRESHOLD:
                # 완전 중복으로 이미 잡힌 쌍은 중복 보고 방지
                already_reported = any(
                    f["row_index"] == row["row_index"]
                    and f["pair_index"] == prev_row["row_index"]
                    and f["severity"] == "RED"
                    for f in findings
                )
                if not already_reported:
                    findings.append({
                        "id":         f"D4-{counter:03d}",
                        "dimension":  "D4",
                        "severity":   "YELLOW",
                        "message": (
                            f"[유사중복] 유사도 {sim:.0%} — "
                            f"행 {prev_row['row_index']} '{name_j[:30]}' "
                            f"↔ 행 {row['row_index']} '{name_i[:30]}'"
                        ),
                        "row_index":  row["row_index"],
                        "pair_index": prev_row["row_index"],
                    })
                    counter += 1

    return findings
