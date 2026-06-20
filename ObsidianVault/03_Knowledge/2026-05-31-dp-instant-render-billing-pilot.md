---
title: 즉시 렌더 과금 파일럿
date: 2026-05-31
source: daily-plus/2026-05-31.md (Card 8)
priority: P3
category: knowledge
status: distilled
tags:
- render
- billing
- interior
- mockup
- pilot
- daily-plus
- knowledge
- source/today_plus
- type/reference
graph_cluster: daily-practice
---

# 즉시 렌더 과금 파일럿

> ChatGPT Pulse 2026-05-31 Card 8 증류 (P3 · knowledge-candidate)

## 목적

소상공인 대상 즉시 마케팅 비주얼 파일 판매 초간단 파일럿. 미리보기→유료 전환, 소액 업셀, 건당 높은 마진. Express Mockup(의뢰 이미지→24시간 2K 렌더).

## 상품 구조

```
Express Mockup 서비스
├─ 무료 미리보기: 저해상도 워터마크 렌더 (즉시)
├─ 기본 패키지: 2K 렌더 1장 — 15,000원
├─ 스탠다드: 2K 렌더 3장 + 편집용 PSD — 35,000원
└─ 프리미엄: 2K 렌더 5장 + 수정 1회 + 24h 납기 — 65,000원
```

## 가격 모델

| 구분 | 가격 | 마진율 | 제작 시간 |
|------|------|--------|---------|
| 무료 미리보기 | 0원 | - | ~30초 (자동) |
| 기본 (2K 1장) | 15,000원 | ~80% | 2~4시간 |
| 스탠다드 (3장+PSD) | 35,000원 | ~75% | 4~8시간 |
| 프리미엄 (5장+수정) | 65,000원 | ~70% | 24시간 내 |

초기 단계에서는 AI 렌더링(Stable Diffusion, Midjourney)으로 마진율 유지.

## 전환 퍼널 설계

```
1. 고객 이미지 업로드 (의뢰 공간 사진)
   ↓
2. AI 미리보기 생성 (저해상도, 워터마크, 무료)
   → 이메일 없이 즉시 확인 가능
   ↓
3. "고화질로 받기" CTA → 결제 페이지
   → Stripe 카드/카카오페이
   ↓
4. 결제 완료 → 24시간 내 2K 파일 이메일 전송
```

## 기술 스택

```yaml
frontend:
  - Next.js (이미지 업로드 + 미리보기)
  - Cloudflare Images (저장 및 CDN)

ai_render:
  - Stable Diffusion API (ComfyUI 또는 Replicate)
  - Midjourney API (선택적 업그레이드)

billing:
  - Stripe Checkout (카드)
  - 카카오페이 (토스페이먼츠 통해)

delivery:
  - Resend (이메일 파일 전송)
  - Presigned URL (S3/R2)
```

## 초기 검증 체크리스트

- [ ] 이미지 업로드 → 미리보기 생성 1분 이내
- [ ] 결제 완료 → 파일 전송 자동화
- [ ] 주 3건 이상 완료 → CVR 측정 시작
- [ ] 환불 요청 대응 프로세스 수립

## 관련 컨텍스트

- [[2026-05-30-dp-measure-events-sql-checklist]] — 결제 이벤트 계측
- [[2026-05-30-dp-bucky-launch-gate]] — 런치 게이트 연동
