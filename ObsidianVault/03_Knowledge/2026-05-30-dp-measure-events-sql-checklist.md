---
title: 측정 이벤트와 SQL 체크리스트
date: 2026-05-30
source: daily-plus/2026-05-30.md (Card 5)
priority: P1
category: knowledge
status: distilled
tags:
- analytics
- sql
- events
- upsell
- stripe
- daily-plus
- knowledge
- source/today_plus
- type/reference
graph_cluster: daily-practice
---

# 측정 이벤트와 SQL 체크리스트

> ChatGPT Pulse 2026-05-30 Card 5 증류 (P1 · knowledge-candidate)

## 목적

업셀 파일럿 계측·결제 세팅 패키지. checkout:upsell_shown, clicked, completed 이벤트 스키마, SQL 검증 쿼리, Stripe 연동 확인.

## 이벤트 스키마 정의

```json
// checkout:upsell_shown
{
  "event": "checkout:upsell_shown",
  "user_id": "string",
  "session_id": "string",
  "upsell_id": "string",
  "price_krw": 15000,
  "variant": "A | B",
  "ts": "ISO8601"
}

// checkout:upsell_clicked
{
  "event": "checkout:upsell_clicked",
  "user_id": "string",
  "session_id": "string",
  "upsell_id": "string",
  "ts": "ISO8601"
}

// checkout:upsell_completed
{
  "event": "checkout:upsell_completed",
  "user_id": "string",
  "session_id": "string",
  "upsell_id": "string",
  "stripe_payment_intent": "pi_...",
  "amount_krw": 15000,
  "ts": "ISO8601"
}
```

## SQL 체크 쿼리 샘플

```sql
-- 전환율 (CVR)
SELECT
  DATE_TRUNC('day', ts) AS day,
  COUNT(*) FILTER (WHERE event = 'checkout:upsell_shown')    AS shown,
  COUNT(*) FILTER (WHERE event = 'checkout:upsell_clicked')  AS clicked,
  COUNT(*) FILTER (WHERE event = 'checkout:upsell_completed') AS completed,
  ROUND(
    COUNT(*) FILTER (WHERE event = 'checkout:upsell_completed')::numeric
    / NULLIF(COUNT(*) FILTER (WHERE event = 'checkout:upsell_shown'), 0), 4
  ) AS cvr
FROM events
WHERE event LIKE 'checkout:upsell_%'
  AND ts >= NOW() - INTERVAL '7 days'
GROUP BY 1
ORDER BY 1 DESC;

-- Stripe 연동 확인 — payment_intent 미매칭 탐지
SELECT e.session_id, e.stripe_payment_intent
FROM events e
LEFT JOIN stripe_payments s ON e.stripe_payment_intent = s.payment_intent_id
WHERE e.event = 'checkout:upsell_completed'
  AND s.payment_intent_id IS NULL;
```

## KPI 기준값

| KPI | 목표 | 경고 | 위험 |
|-----|------|------|------|
| CVR (shown → completed) | ≥8% | 2~8% | <2% |
| 클릭율 (shown → clicked) | ≥25% | 10~25% | <10% |
| 평균 결제금액 | ≥15,000원 | 8,000~15,000원 | <8,000원 |
| Stripe 불일치 건수 | 0 | - | ≥1 |

## Stripe 연동 확인 포인트

- `payment_intent_id` 이벤트 기록 후 Stripe Dashboard와 교차 검증
- Webhook `payment_intent.succeeded` 수신 → DB 상태 업데이트
- 환불 발생 시 `checkout:upsell_refunded` 이벤트 발행 필수

## 관련 컨텍스트

- [[2026-05-30-dp-bucky-launch-gate]] — 런치 게이트 KPI 연동
- [[2026-05-31-dp-instant-render-billing-pilot]] — 즉시 렌더 과금 파일럿
