---
title: 고정 CTA가 만든 큰 차이
date: 2026-05-28
source: daily-plus/2026-05-28.md (Card 8)
priority: P3
category: knowledge
status: distilled
tags:
- cro
- conversion
- cta
- ux
- ab-test
- daily-plus
- knowledge
graph_cluster: daily-practice
---

# 고정 CTA가 만든 큰 차이

> ChatGPT Pulse 2026-05-28 Card 8 증류 (P3 · knowledge)

## 목적
결정적 행동 요소(CTA)를 사용자 여정 초반에 노출시키는 단순 변화가 전환율에 큰 효과. The Clermont 호텔 예약 버튼 고정 배치로 전환율 대폭 향상 사례. 스크롤 없이도 CTA에 접근 가능하게 만드는 것이 핵심 인사이트.

## 핵심 내용
- **The Clermont 호텔 사례**: 예약 버튼을 스크롤해야 보이는 위치에서 화면 상단 고정으로 이동 → 전환율 대폭 향상
- **고정 CTA 구현 방식**:
  ```css
  .cta-sticky {
    position: sticky;
    top: 0;
    z-index: 100;
    background: var(--primary-color);
    padding: 12px 24px;
  }
  /* 또는 fixed + scroll 감지 */
  .cta-fixed {
    position: fixed;
    bottom: 24px;
    right: 24px;
  }
  ```
- **A/B 테스트 설계**:
  - 대조군: 기존 CTA 위치 (스크롤 필요)
  - 실험군: sticky/fixed CTA
  - 측정 지표: 클릭률, 전환율, 페이지 이탈률
  - 최소 샘플: 통계적 유의성 95% 기준 계산
- **스크롤 없이 CTA 노출**: 랜딩 페이지 첫 화면(above the fold)에 CTA 항상 노출

## 구현 체크리스트
- [ ] 현재 서비스 CTA 위치 스크린샷 및 히트맵 분석
- [ ] sticky/fixed CTA CSS 구현
- [ ] A/B 테스트 설정 (Google Optimize 또는 직접 구현)
- [ ] 전환율 기준값 측정 (현재 상태)
- [ ] 2주 테스트 후 통계적 유의성 검증

## 관련 컨텍스트
- 묶음 상품으로 ARPU 키우기: `2026-05-28-dp-bundle-arpu-growth.md`
- 파주권 번들 10일 파일럿: `2026-05-29-dp-paju-bundle-10day-pilot.md`
- 이 항목은 P3(낮은 우선순위)이므로 수익화 관련 P1 항목 완료 후 검토
