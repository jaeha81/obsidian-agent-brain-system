---
type: knowledge-note
date: 2026-06-03
source: daily-plus
category: knowledge-candidate
tags:
  - "#area/ai_automation"
  - "#status/active"
summary: 14일 30주문 자동 결정 — A/B 실험 자동 종료 및 프로모션 매니페스트, ARPU·전환율 기준으로 B 승격 또는 롤백 자동 판단
status: applied
applied_at: 2026-06-11
---

# 14일 30주문 자동 결정 (A/B Auto-Decision)

## 실험 자동 종료 조건

A/B 실험은 다음 중 **먼저 도달한 조건**에서 자동 종료된다:

| 조건 | 기준값 |
|------|--------|
| 실험 기간 | 14일 경과 |
| 주문 수 | 총 30주문 달성 |

## 자동 판단 기준

### B 승격 (Promote B) 조건

모든 조건 충족 시 자동 승격:
- B 그룹 ARPU >= A 그룹 ARPU × 1.05 (+5% 이상)
- B 그룹 전환율 >= A 그룹 전환율 - 0.02 (2% 이내 감소 허용)
- 통계적 유의성 p-value < 0.05

### 롤백 (Rollback to A) 조건

하나라도 해당 시 자동 롤백:
- B 그룹 ARPU < A 그룹 ARPU × 0.95 (-5% 이상 하락)
- B 그룹 전환율 < A 그룹 전환율 - 0.05 (5% 이상 하락)
- 결제 오류율 > 2%

## 프로모션 매니페스트

```python
AB_AUTO_DECISION_CONFIG = {
    "stop_at_days": 14,
    "stop_at_orders": 30,
    "promote_b_if": {
        "arpu_ratio_min": 1.05,       # B ARPU / A ARPU
        "conversion_drop_max": 0.02,   # 허용 전환율 하락
        "p_value_max": 0.05
    },
    "rollback_if": {
        "arpu_ratio_max": 0.95,        # B ARPU / A ARPU
        "conversion_drop_min": 0.05,   # 롤백 트리거 전환율 하락
        "error_rate_max": 0.02
    }
}
```

## 자동 판단 실행 패턴

```python
def auto_decide_ab_test(experiment_id: str):
    metrics = get_experiment_metrics(experiment_id)

    # 종료 조건 확인
    days_elapsed = (datetime.now() - metrics["start_date"]).days
    total_orders = metrics["a_orders"] + metrics["b_orders"]

    if days_elapsed < 14 and total_orders < 30:
        return {"status": "running", "days": days_elapsed, "orders": total_orders}

    # 자동 판단
    arpu_ratio = metrics["b_arpu"] / metrics["a_arpu"]
    conversion_drop = metrics["a_conversion"] - metrics["b_conversion"]

    if (arpu_ratio >= 1.05 and conversion_drop <= 0.02):
        decision = "promote_b"
    elif (arpu_ratio <= 0.95 or conversion_drop >= 0.05):
        decision = "rollback_to_a"
    else:
        decision = "manual_review_needed"

    record_decision(experiment_id, decision, metrics)
    execute_decision(decision)
    return {"status": "decided", "decision": decision}
```

## 보고 포맷

자동 결정 시 Bucky 채널 전송:
```
[A/B 자동 결정] {experiment_id}
기간: {days}일 / 주문: {orders}건
A ARPU: {a_arpu}원 | B ARPU: {b_arpu}원
전환율 A: {a_conv}% | B: {b_conv}%
결정: {decision}
```

## 관련 노트

- [[2026-06-03-dp-ibujang-oneclick-pilot]]
- [[2026-06-03-dp-pulse-manager-manifest]]
