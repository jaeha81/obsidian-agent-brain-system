---
title: CTA A/B 테스트 + 스나이퍼 가격 A/B 실행 계획
date: 2026-06-11
source: experiment-tracker E2/E9 통합 실행 문서
priority: P1
category: strategy
status: active
tags:
- ab-test
- cta
- conversion
- pricing
- sniper
- daily-plus
- source/today_plus
graph_cluster: marketing
---

# CTA A/B 테스트 + 스나이퍼 가격 A/B 실행 계획

> E2(UGC/CTA 전환율) + E9(구매대행 가격 A/B) 통합 실행 문서

---

## 1. CTA Sticky 테스트 (E2)

### 가설
> 화면 상단 고정 CTA(sticky/fixed)가 기존 스크롤 필요 CTA 대비 클릭률을 2배 이상 향상시킨다.

### A/B 배정

```js
// 세션 기반 결정론적 배정
function assignVariant(sessionId) {
  const stored = localStorage.getItem('cta_variant');
  if (stored) return stored;
  const hash = sessionId.split('').reduce((acc, c) => acc + c.charCodeAt(0), 0);
  const variant = (hash % 2 === 0) ? 'A' : 'B';
  localStorage.setItem('cta_variant', variant);
  return variant;
}
```

### 구현 CSS

```css
/* Variant B: sticky CTA */
.cta-sticky {
  position: sticky;
  top: 0;
  z-index: 100;
  background: var(--primary-color, #1a1a2e);
  padding: 12px 24px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.2);
}

/* 또는 fixed (모바일 하단) */
.cta-fixed-bottom {
  position: fixed;
  bottom: 24px;
  right: 24px;
  z-index: 100;
}
```

### 측정 지표

| 지표 | 대조군 A | 실험군 B | 성공 기준 |
|------|---------|---------|---------|
| CTA 클릭률 | 기준값 | +50% 이상 | B > A × 1.5 |
| 전환율 | 기준값 | 통계 유의성 | p < 0.05 |
| 이탈률 | 기준값 | 감소 | B < A |

### 적용 대상 페이지
- [ ] `docs/daily-plus.html` CTA 영역
- [ ] 스나이퍼 랜딩페이지 메인 CTA
- [ ] Express Mockup 랜딩페이지 (구현 후)

---

## 2. 스나이퍼 구매대행 가격 A/B (E9)

### 현재 상태
- 사이트: https://sniper-buying-dashboard.vercel.app/
- 현재 가격: 미설정 (MVP 단계)

### 가격 실험 설계

```
Variant A (파일럿가): 스코어링 리포트 무료, 소싱 대행 건당 5%
Variant B (표준가): 월 구독 ₩29,000 + 소싱 대행 건당 3%
```

### 측정 기간: 2주 (100 세션 이상 확보 후 판단)

```js
const SNIPER_PRICES = {
  A: { model: '건당 수수료', commission: 0.05, base: 0 },
  B: { model: '구독+수수료', monthly: 29000, commission: 0.03 }
};

// ARPU 비교 공식
// ARPU_A = avg_order_value × commission_A
// ARPU_B = monthly_fee + avg_order_value × commission_B
// 승격 → B if ARPU_B > ARPU_A AND p-value < 0.05
```

### 실행 체크리스트
- [ ] 스나이퍼 대시보드 가격 페이지 추가
- [ ] Variant A: "무료 스코어 + 수수료" 랜딩 설계
- [ ] Variant B: "구독 플랜" 랜딩 설계
- [ ] 결제 이벤트 로깅 (`/api/telemetry` 또는 Google Analytics)
- [ ] 14일 후 ARPU 비교 트리거 (Bucky 알림 등록)

---

## 3. 롤백 조건

| 조건 | 액션 |
|------|------|
| B 전환율 < 1% (7일 경과) | 즉시 A로 롤백 |
| 결제 오류율 > 5% | 즉시 롤백 + 알림 |
| 사용자 컴플레인 급증 | 48시간 내 검토 |

---

## 관련 문서

- 소스: `2026-05-28-dp-fixed-cta-conversion.md`, `2026-06-01-dp-price-ab-decision-manifest.md`
- 수익 모델: `2026-06-11-revenue-model-framework.md`
- 실험 트래커: `00_UPGRADE/experiment-tracker-2026-06.md`

## 관련 노트
- [[hubs/JH System]]
