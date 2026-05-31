---
tags: [bucky, evolution, nlp, stt, stripe, pattern]
  - #area/research
created: 2026-05-25
type: knowledge
status: implemented
---

# Bucky 진화 — NLP 레이어 + 결제 + STT 고도화

## 구현 완료 (2026-05-25)

### Item 1 — NLP 전처리기 (`bucky_nlp_preprocessor.py`)
자연어 입력 → AI 최적 구조화 포맷 변환

- 액션 분류: BUILD / DEPLOY / ANALYZE / CAPTURE / SEARCH / FIX / EXPLAIN / UPGRADE / LIST
- 타겟 추출: URL, GitHub 레포, 파일명, 시스템 컴포넌트
- 에이전트 라우팅: claude_code / codex / bucky_knowledge / bucky_vercel / bucky
- Claude API 강화 (신뢰도 < 0.7 시 자동 호출)
- `discord_bot.py` `ask_bucky()` 연동 완료

### Item 2 — Stripe 결제 보일러플레이트 (`templates/stripe_payment/`)
- `server.py` — FastAPI + Stripe 구독/일회성 결제 + 웹훅
- `index.html` — Stripe.js + Toss Payments 통합 결제 페이지
- `.env.example` — 설정 템플릿
- Toss Payments 한국 결제 대안 포함

### Item 3 — 패턴 추출기 강화 (`bucky_pattern_extractor.py`)
- `detect_patterns_nlp()` 추가 — NLP 전처리기 기반 의미론적 클러스터링
- 액션:컴포넌트 기준 클러스터링 (기존: 단순 키워드 매칭)
- 신뢰도 가중 정렬, nlp_enhanced 플래그
- 기존 방식 폴백 유지

### Item 4 — STT 고도화 (`bucky_stt_enhancer.py`)
Typeless 벤치마킹 — 기존 Whisper STT 위의 의도 분류 레이어

- 의도 분류: COMMAND / QUESTION / INFORMATION / CHITCHAT
- Bucky 명령어 자동 감지 → !커맨드 변환 (배포/랜딩/저장/패턴 등)
- 엔티티 추출: URL, GitHub 레포, 파일명, 가격
- Claude API 강화 (COMMAND 의도 시 자동 호출)
- `discord_bot.py` `_postprocess_stt_claude()` 연동 완료

## 핵심 원칙

사용자 자연어 → STT 고도화 → NLP 전처리 → 에이전트 라우팅 → 실행

## 관련 링크
- [[vibe-coding-pipeline]] — 바이브코딩 참고 영상 전략
- [[typeless-voice-stt-analysis]] — Typeless STT 분석
