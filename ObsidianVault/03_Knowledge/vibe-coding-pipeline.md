---
title: "Vibe Coding — AI 서비스 24분 완성 파이프라인"
source: "https://youtu.be/nkYY_64Hu4o?si=QldBFD0_esJWQMIi"
source_type: youtube
date: 2026-05-25
captured_at: 2026-05-25T00:00:00
tags:
  - vibe-coding
  - landing-page
  - deployment
  - template
status: processed
---

# Vibe Coding — AI 서비스 24분 완성 파이프라인

> YouTube 영상 학습 내용. AI 보조 개발로 기획부터 배포까지 24분 안에 완성하는 워크플로우.

## 핵심 파이프라인

```
기획 → 코딩 → 결제 → 배포
  ↓       ↓      ↓      ↓
아이디어  AI IDE  Stripe  Vercel
정의     (Cursor) 연동   자동배포
```

### 단계별 상세

1. **기획 (Idea → Spec)**
   - 목적·타겟·핵심 기능 1장 정리
   - AI에게 PRD 초안 생성 요청

2. **코딩 (AI-assisted Dev)**
   - Cursor / Claude Code로 보일러플레이트 즉시 생성
   - 랜딩페이지 + API 라우트 동시 작성
   - 수동 코딩 없이 요구사항 → 코드 직결

3. **결제 (Stripe 연동)**
   - Stripe Checkout 세션 서버리스 함수로 구현
   - 웹훅으로 결제 완료 이벤트 처리
   - 무료 티어 → 유료 전환 게이트 패턴

4. **배포 (Vercel 자동배포)**
   - GitHub push → Vercel CI/CD 자동 트리거
   - Preview URL → Production 승격 1클릭
   - 환경변수 Vercel Dashboard에서 관리

## 원본 링크

- [Vibe Coding — AI 서비스 24분 완성 파이프라인](https://youtu.be/nkYY_64Hu4o?si=QldBFD0_esJWQMIi)

## 우리 시스템 적용 항목

| 항목 | 현황 | 적용 방향 |
|------|------|----------|
| 랜딩페이지 템플릿 | 미구현 | `bucky_landing_generator.py` 확장 |
| Vercel 자동배포 | `bucky_vercel_deploy.py` 존재 | 파이프라인과 통합 |
| Stripe 결제 연동 | 미구현 | 보일러플레이트 생성 후 스킬화 |

### 즉시 활용 가능한 패턴
- **24분 챌린지**: 신규 아이디어 → 이 파이프라인 따라 배포까지
- **랜딩 보일러플레이트**: Next.js + Tailwind + Stripe Checkout 템플릿화
- **Vercel + GitHub Actions**: `bucky_vercel_deploy.py`를 워크플로에 연결

## 관련 개념

[[vibe-coding]] · [[landing-page]] · [[vercel-deploy]] · [[stripe-integration]] · [[bucky-landing-generator]]

## 다음 할 일

- [ ] Stripe 결제 보일러플레이트 스크립트 작성
- [ ] 랜딩페이지 템플릿 (`03_Knowledge/landing-page-template.md`) 생성
- [ ] `bucky_vercel_deploy.py`와 파이프라인 연동 테스트
