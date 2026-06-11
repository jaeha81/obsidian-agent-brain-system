---
title: 가격 A/B와 결정 매니페스트
date: 2026-06-01
source: daily-plus/2026-06-01.md (Card 4)
priority: P1
category: knowledge
status: distilled
tags:
  - ab-test
  - pricing
  - stripe
  - conversion
  - manifest
  - daily-plus
  - knowledge
---

# 가격 A/B와 결정 매니페스트

> Daily Plus Pulse 2026-06-01 Card 4 증류 (P1 · knowledge-candidate)

## 목적

파일럿 가격(Variant A) vs. 인상 가격(Variant B) 2주 A/B 테스트 설계. 수익/전환 균형 데이터 기반 결정, 로깅 포맷, 승격 규칙 포함.

## A/B 배정 방식

```js
// 세션 기반 결정론적 배정 (쿠키 or localStorage)
function assignVariant(userId) {
  // 기존 배정이 있으면 재사용 (일관성 보장)
  const stored = localStorage.getItem('price_variant');
  if (stored) return stored;

  // 해시 기반 50/50 분할
  const hash = userId.split('').reduce((acc, c) => acc + c.charCodeAt(0), 0);
  const variant = (hash % 2 === 0) ? 'A' : 'B';
  localStorage.setItem('price_variant', variant);
  return variant;
}

const PRICES = {
  A: { amount: 49000, label: '파일럿가' },
  B: { amount: 79000, label: '정가' }
};
```

## 로깅 스키마

```json
{
  "event": "price_variant_assigned",
  "ts": "2026-06-01T10:00:00Z",
  "session_id": "sess_xxx",
  "user_id": "usr_xxx",
  "variant": "A",
  "price": 49000,
  "currency": "KRW",
  "pilot_id": "EP-001"
}
```

```json
{
  "event": "checkout_completed",
  "ts": "2026-06-01T10:05:00Z",
  "session_id": "sess_xxx",
  "variant": "A",
  "revenue": 49000,
  "payment_id": "cs_xxx"
}
```

## 승격 판단 기준값

| 지표 | Variant A 목표 | Variant B 목표 | 승격 조건 |
|------|-------------|-------------|--------|
| 전환율 | ≥ 5% | ≥ 3% | B CVR ≥ 3% AND ARPU > A |
| ARPU | ≥ ₩2,450 | ≥ ₩2,370 | 통계 유의성 p < 0.05 |
| 샘플 수 | 100명 | 100명 | 양쪽 모두 충족 |
| 테스트 기간 | 14일 | 14일 | 기간 완료 후 판단 |

**승격 판단 공식**:

```
ARPU(A) = CVR_A × price_A
ARPU(B) = CVR_B × price_B

승격 → B if ARPU(B) > ARPU(A) AND p-value < 0.05
유지 → A if ARPU(A) >= ARPU(B) OR 샘플 부족
```

## 롤백 조건

| 조건 | 액션 |
|------|------|
| B 전환율 < 1% (7일 경과) | 즉시 A로 롤백 |
| B 결제 오류율 > 5% | 즉시 롤백 + 알림 |
| 사용자 컴플레인 급증 (>10건/일) | 48시간 내 롤백 검토 |
| 수익이 A 대비 -20% 이상 하락 | 롤백 및 원인 분석 |

## 구현 우선순위

- [ ] `assignVariant()` 함수 랜딩 페이지 삽입
- [ ] Stripe Payment Link 2종 생성 (A/B 각각)
- [ ] 로깅 스키마 `/api/telemetry` 적용
- [ ] 14일 후 판단 알림 Bucky 트리거 등록
- [ ] 결과 대시보드 (단순 스프레드시트 가능)

## 관련 컨텍스트

- Express Mockup 파일럿 수익 최적화 단계
- [[익스프레스-모크업-즉시-실행-매니페스트]], [[수익-우선-안전-매니페스트]]
