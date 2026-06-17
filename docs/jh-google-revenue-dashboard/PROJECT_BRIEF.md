# JH-구글자동화수익대시보드 Project Brief

## Purpose

`JH-구글자동화수익대시보드`는 Blogger 기반 구글 블로그와 AdSense 수익화를 안전하게 운영하기 위한 별도 대시보드입니다. 초기 목표는 무료 또는 저비용으로 시작해 검색 유입, 콘텐츠 검수, 승인 준비, 수익 KPI, Make.com 연동, Discord 운영 보고를 하나의 운영 흐름으로 묶는 것입니다.

## Source Plan

- Source file: `google_blog_adsense_monetization_plan.docx`
- Core platforms: Blogger, Google AdSense, Google Search Console, Google Trends, Google Sheets, Looker Studio, Make.com, Discord
- Operating posture: low-cost first, policy-compliant, human-reviewed content, RPM and pageview based revenue tracking

## MVP Scope

- Static operator dashboard: `docs/jh-google-revenue-dashboard.html`
- Initial data contract: `data/jh_google_revenue_dashboard.json`
- AgentBus workflow helper: `scripts/jh_google_revenue_workflow.py`
- Tests: `tests/test_jh_google_revenue_workflow.py`
- Discord channel contract: `#jh-google-revenue-dashboard`

## Non-Negotiable Safety Rules

- No ad auto-clicking.
- No self-clicking or asking family/friends/users to click ads.
- No traffic manipulation or traffic buying.
- No mass auto-publishing.
- No low-value AI content generation.
- No publication without a human review packet.
- No secrets, tokens, cookies, webhook URLs, or OAuth credentials in code or notes.

## Phase 1 Goal

Build the content pipeline:

1. Keyword scoring from manual input, Google Trends, and Search Console exports.
2. SEO outline generation for AdSense basics, AI tools, digital templates, automation, and creator operations clusters.
3. Blogger draft packets that remain unpublished until user approval.
4. Policy review packets for AdSense, spam, invalid traffic, and generative AI quality.
5. Discord status messages for queue, review, and blocked actions.

## Done When

- The dashboard opens in the local `docs/` preview.
- Workflow requests can be normalized and queued into AgentBus.
- Forbidden actions are blocked by tests.
- Content generation always sets `human_review_required: true`.
- External sends and publication remain approval-gated.
