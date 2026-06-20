---
title: 2주 매출 실험 플랜 (E8 + E10 통합)
date: 2026-06-11
source: experiment-tracker E8/E10 통합 실행 문서
priority: P1
category: strategy
status: active
tags:
- revenue
- experiment
- 2weeks
- ab-test
- daily-plus
- source/today_plus
graph_cluster: misc
---

# 2주 매출 실험 플랜

> E8(24시간 매출 실험 4가지) + E10(2주 안에 돌릴 매출 실험 5개) 통합 실행 문서
> 기간: 2026-06-11 ~ 2026-06-25

---

## 실험 목록 (우선순위 순)

| 실험 | 기간 | 예상 투자 | 예상 수익 | 상태 |
|------|------|---------|---------|------|
| EXP-1: Express Mockup 첫 5건 | 3일 | 0원 | ₩15,000~₩75,000 | ⏳ 시작 |
| EXP-2: CTA Sticky 전환율 | 7일 | 0원 | 전환율 데이터 | ⏳ 시작 |
| EXP-3: 영업 이메일 10건 발송 | 5일 | 0원 | 미팅 1~2건 | ⏳ 시작 |
| EXP-4: 스나이퍼 가격 A/B | 14일 | 0원 | ARPU 데이터 | ⏳ 시작 |
| EXP-5: Wishket 제안서 자동화 | 7일 | 0원 | 수주 1건 | ⏳ 시작 |

---

## EXP-1: Express Mockup 첫 5건

**가설**: 인테리어 현장 사진을 받아 24시간 내 AI 렌더링을 제공하면 ₩15,000~₩65,000 수익이 발생한다.

**실행 순서**:
```
1. 카카오채널 또는 인스타 DM으로 고객 모집 공지
2. 고객 공간 사진 수신 (이메일 or 카카오)
3. AI 렌더링 작업 (Midjourney or SD, 2~4시간)
4. 무료 저화질 미리보기 → 결제 CTA
5. 결제 완료 → 고화질 파일 전송
```

**성공 기준**: 5건 중 3건 이상 유료 전환 (전환율 60%)

---

## EXP-2: CTA Sticky 전환율 측정

**가설**: Sticky CTA가 스크롤 CTA 대비 클릭률 50% 이상 향상

**대상 페이지**:
1. `docs/daily-plus.html` 상단 CTA
2. 스나이퍼 대시보드 메인 CTA

**측정 방식**:
```js
// 간단 클릭 카운터 (GA 없이도 가능)
document.querySelectorAll('.cta-primary').forEach(btn => {
  btn.addEventListener('click', () => {
    const data = {
      variant: localStorage.getItem('cta_variant') || 'A',
      page: window.location.pathname,
      ts: new Date().toISOString()
    };
    // localStorage에 클릭 이벤트 누적
    const log = JSON.parse(localStorage.getItem('cta_log') || '[]');
    log.push(data);
    localStorage.setItem('cta_log', JSON.stringify(log));
  });
});
```

---

## EXP-3: 영업 이메일 10건 발송

**목표**: 응답률 20% 이상 (10건 중 2건 응답)

**발송 스케줄**:
- D+0: 인테리어 사업자 5건 (템플릿 A)
- D+2: AI 자동화 수요처 5건 (템플릿 B)
- D+5: 무응답 건 후속 발송

**결과 기록 테이블** (Obsidian에 직접 기록):

| # | 발송처 | 발송일 | 오픈 | 응답 | 미팅 | 전환 |
|---|--------|--------|------|------|------|------|
| 1 | | | | | | |
| 2 | | | | | | |
| ... | | | | | | |

---

## EXP-4: 스나이퍼 가격 A/B

세부 내용은 `2026-06-11-cta-ab-test-execution.md` 참조.

**이번 주 할 것**:
- [ ] 대시보드 가격 섹션 HTML 추가 (Variant A/B 페이지)
- [ ] 세션 기반 배정 로직 삽입
- [ ] 14일 후 비교 알림 Bucky에 등록

---

## EXP-5: Wishket 제안서 자동화 매출

**가설**: AI 자동화된 제안서가 낙찰률을 높여 1건 이상 수주로 이어진다.

**실행**:
```
1. Wishket 신규 프로젝트 키워드 알림 설정 (AI/자동화/데이터 분석)
2. 프로젝트 발견 → Bucky 자동 제안서 초안 생성
3. 재하 검수 → 5분 내 제출
4. 결과: 낙찰 vs 미낙찰 기록
```

---

## 2주 목표 수치

| 지표 | 목표 |
|------|------|
| Express Mockup 매출 | ₩30,000 이상 |
| Wishket 수주 | 1건 이상 |
| 이메일 응답 | 2건 이상 |
| CTA 클릭률 데이터 | 50세션 이상 수집 |
| A/B 가격 데이터 | 14일 완주 |

---

## 일별 실행 체크

**1주차**
- [ ] D+1: EXP-1 고객 모집 공지 발송
- [ ] D+1: EXP-3 이메일 5건 발송 (템플릿 A)
- [ ] D+2: EXP-2 CTA sticky 구현 배포
- [ ] D+3: EXP-3 이메일 5건 발송 (템플릿 B)
- [ ] D+3: EXP-1 첫 고객 결과 기록
- [ ] D+5: 후속 이메일 발송

**2주차**
- [ ] D+8: EXP-1 5건 완료 집계
- [ ] D+10: EXP-3 미팅 결과 정리
- [ ] D+14: EXP-4 A/B 최종 비교 분석
- [ ] D+14: 전체 실험 결과 → `experiment-tracker-2026-06.md` 업데이트

---

## 관련 문서

- 실험 트래커: `00_UPGRADE/experiment-tracker-2026-06.md`
- 영업 이메일: `2026-06-11-outreach-email-template.md`
- A/B 테스트: `2026-06-11-cta-ab-test-execution.md`
- 수익 모델: `2026-06-11-revenue-model-framework.md`

## 관련 노트
- [[hubs/JH System]]
