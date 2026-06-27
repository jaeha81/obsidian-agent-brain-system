"""
D7: 제경비 적정성 검증
SPC 표준 제경비 공식을 적용해 예상값을 산출하고 내역서와 비교한다.

제경비 공식 (SPC 2024):
  산재보험료    = sum(인건비) × 0.0356
  고용보험료    = sum(인건비) × 0.0101
  안전관리비    = sum(합계) × 0.0311   (5억원 이상, 미만은 × 0.0186)
  직사입 안관비 = sum(직사입자재_합계) × 0.0311
  만단위 이하 절사
"""
from __future__ import annotations

import math
from typing import List


_RATE_WORKERS_COMP = 0.0356      # 산재보험료
_RATE_EMPLOYMENT = 0.0101        # 고용보험료
_RATE_SAFETY_HIGH = 0.0311       # 안전관리비 (5억 이상)
_RATE_SAFETY_LOW = 0.0186        # 안전관리비 (5억 미만)
_SAFETY_THRESHOLD = 500_000_000  # 5억원

# 내역서에서 제경비 라인으로 판단하는 키워드
_OVERHEAD_KEYWORDS = [
    "산재보험", "고용보험", "안전관리비", "제경비", "간접비",
]


def _floor_10k(value: float) -> float:
    """만단위 이하 절사."""
    return math.floor(value / 10_000) * 10_000


def _is_overhead_row(row: dict) -> bool:
    """행이 제경비 항목인지 키워드로 판단."""
    name = row.get("name") or ""
    remark = row.get("remark") or ""
    for kw in _OVERHEAD_KEYWORDS:
        if kw in name or kw in remark:
            return True
    return False


def analyze(rows: List[dict], direct_rows: List[dict]) -> List[dict]:
    """
    Args:
        rows:        전체내역서 정규화 row 리스트
        direct_rows: 직사입자재 row 리스트

    Returns:
        findings 리스트. 각 항목:
        {
          "id":             "D7-NNN",
          "dimension":      "D7",
          "severity":       "RED" | "YELLOW" | "INFO",
          "message":        str,
          "row_index":      int | None,
          "expected":       float | None,
          "actual":         float | None,
          "overhead_type":  str
        }
    """
    findings: List[dict] = []
    counter = 1

    # 비용 합산
    total_labor = sum(r.get("labor_amount", 0.0) for r in rows)
    total_sum = sum(r.get("total", 0.0) for r in rows)
    total_direct = sum(r.get("total", 0.0) for r in direct_rows)

    # 예상 제경비 계산
    expected_workers_comp = _floor_10k(total_labor * _RATE_WORKERS_COMP)
    expected_employment = _floor_10k(total_labor * _RATE_EMPLOYMENT)

    safety_rate = _RATE_SAFETY_HIGH if total_sum >= _SAFETY_THRESHOLD else _RATE_SAFETY_LOW
    expected_safety = _floor_10k(total_sum * safety_rate)
    expected_direct_safety = _floor_10k(total_direct * _RATE_SAFETY_HIGH)

    expected = {
        "산재보험료": expected_workers_comp,
        "고용보험료": expected_employment,
        "안전관리비": expected_safety,
        "직사입안전관리비": expected_direct_safety,
    }

    # 내역서에서 제경비 라인 추출
    overhead_rows = [r for r in rows if _is_overhead_row(r)]

    if not overhead_rows:
        # 제경비 라인 자체가 없음 → INFO (누락 가능성)
        for overhead_type, exp_val in expected.items():
            findings.append({
                "id":            f"D7-{counter:03d}",
                "dimension":     "D7",
                "severity":      "YELLOW",
                "message": (
                    f"[제경비 미기재] '{overhead_type}' 라인이 내역서에 없음. "
                    f"예상값: {exp_val:,.0f}원"
                ),
                "row_index":     None,
                "expected":      exp_val,
                "actual":        None,
                "overhead_type": overhead_type,
            })
            counter += 1
        return findings

    # 실제 제경비 라인과 예상값 비교
    actual: dict = {}
    for row in overhead_rows:
        name = row.get("name") or ""
        amount = row.get("total") or row.get("material_amount") or row.get("labor_amount") or 0.0
        for key in ["산재보험", "고용보험", "안전관리비"]:
            if key in name:
                actual[key] = (actual.get(key, 0.0) + amount, row["row_index"])

    for overhead_type, exp_val in expected.items():
        # 직사입 안전관리비는 별도 시트이므로 비교 생략 (INFO만)
        if overhead_type == "직사입안전관리비":
            findings.append({
                "id":            f"D7-{counter:03d}",
                "dimension":     "D7",
                "severity":      "INFO",
                "message": (
                    f"[직사입 안전관리비 예상] {exp_val:,.0f}원 "
                    f"(직사입자재 합계 {total_direct:,.0f}원 × {_RATE_SAFETY_HIGH:.2%})"
                ),
                "row_index":     None,
                "expected":      exp_val,
                "actual":        None,
                "overhead_type": overhead_type,
            })
            counter += 1
            continue

        # 키워드로 실제값 매핑
        matched_key = next(
            (k for k in actual if k in overhead_type or overhead_type in k), None
        )
        if matched_key is None:
            findings.append({
                "id":            f"D7-{counter:03d}",
                "dimension":     "D7",
                "severity":      "YELLOW",
                "message": (
                    f"[제경비 항목 미탐지] '{overhead_type}'에 해당하는 라인을 내역서에서 찾지 못함. "
                    f"예상값: {exp_val:,.0f}원"
                ),
                "row_index":     None,
                "expected":      exp_val,
                "actual":        None,
                "overhead_type": overhead_type,
            })
            counter += 1
            continue

        act_val, act_row_idx = actual[matched_key]
        if exp_val == 0:
            continue

        # 오차 비율 계산
        deviation = abs(act_val - exp_val) / exp_val if exp_val else 0.0

        if deviation > 0.05:  # 5% 초과 오차 → YELLOW
            findings.append({
                "id":            f"D7-{counter:03d}",
                "dimension":     "D7",
                "severity":      "YELLOW",
                "message": (
                    f"[제경비 오차] '{overhead_type}' — "
                    f"내역서 {act_val:,.0f}원 vs 예상 {exp_val:,.0f}원 "
                    f"(오차 {deviation:.1%})"
                ),
                "row_index":     act_row_idx,
                "expected":      exp_val,
                "actual":        act_val,
                "overhead_type": overhead_type,
            })
            counter += 1

    return findings
