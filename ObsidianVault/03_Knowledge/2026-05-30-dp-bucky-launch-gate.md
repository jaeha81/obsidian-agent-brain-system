---
title: 버키 실행형 런치 게이트
date: 2026-05-30
source: daily-plus/2026-05-30.md (Card 4)
priority: P1
category: knowledge
status: distilled
tags:
- launch
- gate
- upsell
- metrics
- automation
- daily-plus
- knowledge
graph_cluster: daily-practice
---

# 버키 실행형 런치 게이트

> ChatGPT Pulse 2026-05-30 Card 4 증류 (P1 · knowledge-candidate)

## 목적

업셀 런치 게이트를 60분마다 자동 점검해 프로모트/일시중지/에스컬레이트를 결정하는 규칙. 롤링 지표(24시간, 10일)로 변동성을 억제하고 명확한 커트라인으로 결정한다.

## 판단 지표 목록

| 지표 | 측정 윈도우 | 설명 |
|------|------------|------|
| 전환율 (CVR) | 24h 롤링 | upsell_shown → upsell_completed |
| 평균 매출 (ARPU) | 24h 롤링 | 업셀 완료 건당 평균 금액 |
| 환불율 | 10일 롤링 | 완료 건 대비 환불 건수 |
| 에러율 | 1h 롤링 | 결제 시도 중 오류 비율 |
| 노출 볼륨 | 24h 롤링 | upsell_shown 이벤트 수 |

## 통과/실패 기준값

```yaml
launch_gate:
  promote:           # 프로모트 → 전체 트래픽 확장
    cvr_min: 0.08    # CVR 8% 이상
    arpu_min: 15000  # 원 이상
    refund_max: 0.03 # 3% 이하
    error_max: 0.01  # 1% 이하
  pause:             # 일시중지
    cvr_max: 0.02    # CVR 2% 미만
    error_min: 0.05  # 에러율 5% 초과
  escalate:          # 인간 판단 요청
    refund_min: 0.05 # 환불율 5% 초과
    volume_max: 0    # 24h 노출 0건 (파이프라인 중단 의심)
```

## 에스컬레이트 트리거

다음 중 하나라도 해당되면 즉시 Discord #jh-알림 채널에 에스컬레이트:

1. 환불율 5% 초과 (사기 또는 품질 문제)
2. 24h 내 노출 0건 (이벤트 파이프라인 단절)
3. 에러율 10% 초과 (결제 연동 장애)
4. 급격한 CVR 하락 — 전일 대비 50% 이상 감소

## Bucky 명령 템플릿

```
/bucky gate check upsell-launch
/bucky gate promote upsell-launch --confirm
/bucky gate pause upsell-launch --reason "cvr_below_threshold"
/bucky escalate upsell-launch --alert-channel "#jh-알림"
```

## 60분 자동 점검 루프

```python
# cron: */60 * * * *
def launch_gate_check():
    metrics = fetch_rolling_metrics(windows=["24h", "10d"])
    decision = evaluate_gate(metrics, rules=LAUNCH_GATE_CONFIG)
    if decision == "escalate":
        notify_discord(channel="#jh-알림", payload=metrics)
    elif decision == "pause":
        pause_upsell_pipeline()
    log_gate_result(decision, metrics)
```

## 관련 컨텍스트

- [[2026-05-30-dp-measure-events-sql-checklist]] — 측정 이벤트 스키마
- [[2026-05-30-dp-orchestrator-approval-gate]] — 오케스트레이터 승인 게이트
