---
type: knowledge-note
date: 2026-06-09
source: daily-plus
category: voice-pipeline
tags:
  - "#area/ai_automation"
  - "#status/active"
summary: JH 완성 패키지 매니페스트 — 비개발자 대상 Beginner/Intermediate/Advanced 3종 상품화 스키마
status: applied
applied_at: 2026-06-11
---

# JH 완성 패키지 매니페스트

비개발자도 즉시 상품페이지 + 결제 연결 가능한 3종 패키지 매니페스트.
각 패키지는 SKU 메타데이터, 결제 게이트웨이, 랜딩 페이지 템플릿, STT 설정, 설치 가이드를 포함한다.

---

## Package A — Beginner

```json
{
  "sku": "JH-PKG-A-001",
  "name": "JH Starter Voice Kit",
  "tier": "beginner",
  "price_krw": 199000,
  "price_usd": 149,
  "subscription_monthly_krw": 49000,
  "payment_gateways": ["toss", "stripe"],
  "landing_template": "templates/landing-beginner.html",
  "stt_config": {
    "provider": "whisper-local",
    "model": "small",
    "language": "ko",
    "offline_first": true
  },
  "includes": ["voice-capture", "basic-note-gen", "discord-notify"],
  "install_guide": "docs/install-beginner.md",
  "support_tier": "community"
}
```

---

## Package B — Intermediate

```json
{
  "sku": "JH-PKG-B-001",
  "name": "JH Pro Automation Bundle",
  "tier": "intermediate",
  "price_krw": 490000,
  "price_usd": 369,
  "subscription_monthly_krw": 99000,
  "payment_gateways": ["toss", "stripe"],
  "landing_template": "templates/landing-intermediate.html",
  "stt_config": {
    "provider": "whisper-local",
    "model": "medium",
    "language": "ko",
    "offline_first": true,
    "sensitive_masking": true
  },
  "includes": ["voice-pipeline", "obsidian-sync", "trigger-jobs", "discord-bot"],
  "install_guide": "docs/install-intermediate.md",
  "support_tier": "email-48h"
}
```

---

## Package C — Advanced

```json
{
  "sku": "JH-PKG-C-001",
  "name": "JH Agent OS Full Stack",
  "tier": "advanced",
  "price_krw": 990000,
  "price_usd": 749,
  "subscription_monthly_krw": 199000,
  "payment_gateways": ["toss", "stripe"],
  "landing_template": "templates/landing-advanced.html",
  "stt_config": {
    "provider": "whisper-local",
    "model": "large-v3",
    "language": "ko",
    "offline_first": true,
    "sensitive_masking": true,
    "auto_classify": true
  },
  "includes": [
    "full-voice-pipeline",
    "bucky-orchestrator",
    "obsidian-vault-sync",
    "trigger-jobs",
    "discord-bot",
    "agent-telemetry",
    "custom-onboarding"
  ],
  "install_guide": "docs/install-advanced.md",
  "support_tier": "dedicated-slack"
}
```

---

## 결제 게이트웨이 설정 메모

| 게이트웨이 | 한국 결제 | 해외 결제 | 구독 지원 | 수수료 |
|---|---|---|---|---|
| Toss Payments | O | X | O | 3.3% |
| Stripe | O | O | O | 2.9% + $0.30 |

- 기본값: KR 고객 → Toss, 해외 고객 → Stripe
- 구독 웹훅: `/webhooks/toss` / `/webhooks/stripe` 엔드포인트 필수

## 다음 액션

- [ ] 랜딩 페이지 템플릿 3종 HTML 생성
- [ ] Toss 웹훅 핸들러 연결
- [ ] 설치 가이드 docs/ 경로에 마크다운 작성
