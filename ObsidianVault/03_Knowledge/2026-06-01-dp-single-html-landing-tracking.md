---
title: 단일 HTML 랜딩과 추적 연결
date: 2026-06-01
source: daily-plus/2026-06-01.md (Card 2)
priority: P2
category: knowledge
status: distilled
tags:
- html
- landing-page
- stripe
- telemetry
- tracking
- daily-plus
- knowledge
graph_cluster: daily-practice
---

# 단일 HTML 랜딩과 추적 연결

> Daily Plus Pulse 2026-06-01 Card 2 증류 (P2 · knowledge-candidate)

## 목적

하루 만에 결제까지 가는 최소 랜딩/텔레메트리 세팅. CDN에 HTML 하나 올리고 Stripe Payment Link 붙이면 방문·프리뷰·체크아웃 완료 이벤트 자동 기록.

## 최소 HTML 구조

```html
<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Express Mockup — 즉시 시작</title>
  <style>
    /* 인라인 미니멀 CSS — 외부 의존 없음 */
    body { font-family: sans-serif; max-width: 600px; margin: 4rem auto; padding: 1rem; }
    .cta { display:inline-block; padding: 1rem 2rem; background:#635bff; color:#fff;
           border-radius:6px; text-decoration:none; font-size:1.1rem; }
    .preview { width:100%; border-radius:8px; cursor:pointer; }
  </style>
</head>
<body>
  <h1>Express Mockup</h1>
  <p>48시간 안에 현장 모크업을 실행합니다.</p>

  <img class="preview" src="mockup-preview.jpg" alt="미리보기"
       onclick="track('mockup_preview_click', { mockup_type: 'interior' })">

  <br><br>
  <a class="cta" href="https://buy.stripe.com/<LINK_ID>"
     onclick="track('mockup_checkout_start', { pilot_id: 'EP-001', amount: 49000 })">
    지금 시작하기 — ₩49,000
  </a>

  <script>
    // 텔레메트리 헬퍼
    function track(event, props) {
      const payload = { event, ts: Date.now(), url: location.href, ...props };
      navigator.sendBeacon('/api/telemetry', JSON.stringify(payload));
    }
    // 방문 이벤트 자동 발화
    track('mockup_page_view', { referrer: document.referrer });
  </script>
</body>
</html>
```

## Stripe 링크 연결

1. Stripe Dashboard → Payment Links → Create Link
2. 상품: Express Mockup Pilot / ₩49,000 (1회성)
3. 성공 리디렉션: `https://<domain>/success.html`
4. 메타데이터: `pilot_id=EP-001`
5. 웹훅: `checkout.session.completed` → `/webhook/stripe`

## 텔레메트리 이벤트 3종

| 이벤트 | 발생 조건 | 핵심 필드 |
|--------|--------|---------|
| `mockup_page_view` | 페이지 로드 | `ts`, `referrer`, `url` |
| `mockup_preview_click` | 미리보기 이미지 클릭 | `ts`, `mockup_type` |
| `mockup_checkout_start` | CTA 버튼 클릭 | `ts`, `pilot_id`, `amount` |

결제 완료 이벤트(`mockup_payment_success`)는 Stripe 웹훅에서 서버 사이드 발화.

## 즉시 배포 방법

```bash
# Cloudflare Pages — 가장 빠름 (무료)
npx wrangler pages deploy . --project-name express-mockup

# GitHub Pages — 리포 없으면 생성
git init && git add index.html && git commit -m "init"
gh repo create express-mockup-landing --public --push

# Vercel — 터미널 1줄
vercel --prod
```

## 구현 우선순위

- [ ] `index.html` 작성 (위 템플릿 기반)
- [ ] Stripe Payment Link 발급 및 URL 삽입
- [ ] `/api/telemetry` 엔드포인트 배포
- [ ] CDN/Vercel 배포
- [ ] 이벤트 수신 확인

## 관련 컨텍스트

- Express Mockup 파일럿 착수 첫 단계
- [[익스프레스-모크업-즉시-실행-매니페스트]], [[텔레메트리-롤백-감사-운영서]]
