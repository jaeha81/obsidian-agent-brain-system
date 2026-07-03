"""
D2: 사양 코드 정합성 분석
도면 자재표(spec_codes)와 내역서 모델No. 컬럼을 대조한다.
- MISSING: 도면 코드가 내역서에 없음 → RED
- GHOST:   내역서 코드가 도면에 없음    → YELLOW
"""
from __future__ import annotations

from typing import Dict, List, Optional


def analyze(rows: List[dict], spec_codes: Dict[str, str]) -> List[dict]:
    """
    Args:
        rows:       전체내역서 정규화 row 리스트 (SPCEstimateParser.parse 반환값)
        spec_codes: {"F2": "BOH FLOOR TILE", "WT1": "주방 타일", ...}

    Returns:
        findings 리스트. 각 항목:
        {
          "id":         "D2-NNN",
          "dimension":  "D2",
          "severity":   "RED" | "YELLOW",
          "message":    str,
          "row_index":  int | None,
          "code":       str
        }
    """
    # 내역서에 실제로 존재하는 모델No. 집합
    model_nos_in_estimate: Dict[str, int] = {}  # code -> first row_index
    for row in rows:
        mn = row.get("model_no")
        if mn and mn not in model_nos_in_estimate:
            model_nos_in_estimate[mn] = row["row_index"]

    findings: List[dict] = []
    counter = 1

    # MISSING: 도면 코드가 내역서에 없음
    for code, description in spec_codes.items():
        if code not in model_nos_in_estimate:
            findings.append({
                "id":        f"D2-{counter:03d}",
                "dimension": "D2",
                "severity":  "RED",
                "message":   f"[MISSING] 도면 코드 '{code}' ({description})가 내역서 모델No.에 없음",
                "row_index": None,
                "code":      code,
            })
            counter += 1

    # GHOST: 내역서 코드가 도면에 없음
    for code, row_idx in model_nos_in_estimate.items():
        if code not in spec_codes:
            findings.append({
                "id":        f"D2-{counter:03d}",
                "dimension": "D2",
                "severity":  "YELLOW",
                "message":   f"[GHOST] 내역서 모델No. '{code}'가 도면 자재표에 없음 (행 {row_idx})",
                "row_index": row_idx,
                "code":      code,
            })
            counter += 1

    return findings
