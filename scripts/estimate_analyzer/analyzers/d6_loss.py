"""
D6: 자재 loss율 적정성 검증
SPC 표준 loss율 기준과 내역서의 실제 loss율을 비교한다.
범위를 벗어난 경우 YELLOW 알람.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple


# 작업조 라벨 → (최솟값, 최댓값)
# WHY: SPC 표준 2024 기준. 범위는 허용 오차를 포함한 실운용 기준.
LOSS_RATE_RULES: Dict[str, Tuple[float, float]] = {
    "목공":        (1.00, 1.10),
    "직영":        (1.00, 1.00),
    "타일":        (1.10, 1.20),
    "타일/부자재": (1.10, 1.20),
    "타일/메지":   (1.10, 1.10),
    "경량":        (1.10, 1.10),
    "습식":        (1.10, 1.10),
    "습식-1":      (1.10, 1.10),
    "도장":        (1.00, 1.00),
    "철거":        (1.00, 1.00),
    # 명시되지 않은 작업조: 넓은 범위 허용
    "_default":    (1.00, 1.20),
}


def _get_rule(trade_category: Optional[str], name: Optional[str]) -> Tuple[float, float]:
    """
    row의 trade_category(공종) 또는 name에서 작업조를 유추해 적용 규칙 반환.
    trade_category는 공종명이므로, 작업조는 name 또는 공종명 기반으로 추론.
    """
    # name 기반 작업조 탐지 (작업조 이름이 명칭 컬럼에 포함되는 경우 많음)
    candidates = [trade_category or "", name or ""]
    for label, rule in LOSS_RATE_RULES.items():
        if label == "_default":
            continue
        for candidate in candidates:
            if label in candidate:
                return rule
    return LOSS_RATE_RULES["_default"]


def analyze(rows: List[dict]) -> List[dict]:
    """
    Args:
        rows: 전체내역서 정규화 row 리스트

    Returns:
        findings 리스트. 각 항목:
        {
          "id":           "D6-NNN",
          "dimension":    "D6",
          "severity":     "YELLOW",
          "message":      str,
          "row_index":    int,
          "actual_rate":  float,
          "expected_min": float,
          "expected_max": float
        }
    """
    findings: List[dict] = []
    counter = 1

    for row in rows:
        loss_rate = row.get("loss_rate", 0.0)

        # loss율이 기록되지 않은 행(0.0) 또는 자재비가 없는 행은 스킵
        if loss_rate == 0.0 and row.get("material_amount", 0.0) == 0.0:
            continue
        if loss_rate == 0.0:
            # 자재비는 있으나 loss율 미기재 → 1.00으로 간주, 검증 생략
            continue

        min_rate, max_rate = _get_rule(row.get("trade_category"), row.get("name"))

        # 부동소수점 비교 오차 허용 (±0.001)
        if loss_rate < min_rate - 0.001 or loss_rate > max_rate + 0.001:
            trade = row.get("trade_category") or "미분류"
            name = row.get("name") or "(명칭없음)"
            findings.append({
                "id":           f"D6-{counter:03d}",
                "dimension":    "D6",
                "severity":     "YELLOW",
                "message": (
                    f"[LOSS율 이상] 공종='{trade}', 명칭='{name}' — "
                    f"실제 {loss_rate:.2f}, 기대범위 [{min_rate:.2f}, {max_rate:.2f}]"
                ),
                "row_index":    row["row_index"],
                "actual_rate":  loss_rate,
                "expected_min": min_rate,
                "expected_max": max_rate,
            })
            counter += 1

    return findings
