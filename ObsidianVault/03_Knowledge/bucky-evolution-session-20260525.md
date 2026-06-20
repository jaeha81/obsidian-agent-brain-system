---
title: Bucky 자가 진화 시스템 — 2026-05-25 세션
date: 2026-05-25
tags:
- bucky-evolution
- vibe-coding
- stt-upgrade
- landing-page
- self-reflection
status: active
summary: '- 버키는 서브 에이전트들과 함께 사용자 데이터를 흡수, 시스템 품질을 올릴 것'
category: research
next_action: review
graph_cluster: bucky-agent
---

# Bucky 자가 진화 시스템 — 2026-05-25 세션

## 세션 핵심 지시사항

사용자 지시:
- 버키는 서브 에이전트들과 함께 사용자 데이터를 흡수, 시스템 품질을 올릴 것
- Obsidian을 가장 진보된 에이전트로 자가 학습 루프를 통해 지속 진화
- 모든 링크·데이터 → Obsidian 지식베이스 자동 흡수 및 활용
- Claude Code / Codex에게 지시도 잘 할 것

## 바이브코딩 파이프라인 (Track A & B)

출처: https://youtu.be/nkYY_64Hu4o?si=QldBFD0_esJWQMIi

**핵심 흐름:** 기획 → 코딩 → 결제 → 배포 (24분 완성)

### Track A — 랜딩 페이지 자동 생성
- `scripts/bucky_landing_generator.py` — GitHub URL → 랜딩 HTML 자동 생성
- `templates/landing_page_template.html` — 다크 테마 프리미엄 템플릿
- Discord 명령: `!랜딩 <GitHub URL>` / `/landing <URL>`
- 슬래시 명령: `/pipeline <URL>` — 랜딩 + 배포 원스톱

### Track B — Vercel 자동 배포
- `scripts/bucky_vercel_deploy.py` — `vercel --prod` 자동 실행
- `scripts/bucky_commercialize.py` — 랜딩 + 결제 + 배포 통합
- Discord 명령: `!배포 <경로>` / `!상품화 <GitHub URL>`

## Typeless STT 벤치마킹

출처: https://www.typeless.com/affiliate/invite

**결론:** Discord 직접 연동 불가 → 자체 구현으로 대체

### 구현된 내용 (2026-05-25)
- `discord_bot.py` `_postprocess_stt_claude()` 추가
- Claude Haiku API 기반 고급 필러 제거 + 의도 명확화
- ANTHROPIC_API_KEY 있으면 자동 활성화, 없으면 regex 폴백
- 환경변수: `STT_AI_ENHANCE=1` (기본 활성화)

### 권장 설정
```env
WHISPER_MODEL=medium       # small → medium으로 30~40% 정확도 향상
STT_AI_ENHANCE=1           # Claude API 후처리 활성화
ANTHROPIC_API_KEY=<key>    # Claude Haiku 사용
```

## 자가 진화 루프 현황

### P0 — Knowledge Auto-Capture ✅
- `bucky_knowledge_capture.py` 완성
- Discord `!저장 <URL>` 명령 + 자동 URL 감지

### P1 — Pattern Extractor ✅ (경로 버그 수정됨)
- `bucky_pattern_extractor.py` 완성
- 수정: `VAULT / "AgentBus"` → `VAULT / "10_AgentBus" / "inbox"` 파싱
- 6시간마다 자동 실행 (discord_bot 백그라운드)

### P2 — Self-Reflection Engine ✅ (경로 버그 수정됨)
- `bucky_self_reflection.py` 완성
- 수정: inbox .md 파일 기반 대화 분석으로 변경
- 매일 1회 자동 실행 (discord_bot 백그라운드)
- Claude Haiku API로 약점 분석 → Obsidian 저장

### P3 — Multi-Agent Orchestrator (미완)
- `bucky_dispatcher.py` 기반 구현 예정

## 진화 원칙

```
사용할수록 똑똑해지는 시스템
  사용자 말 한마디 → Obsidian 지식 노드 생성
  같은 질문 2번 → 자동 스킬화
  버키가 틀리면 → 오류 학습 → 다음엔 안 틀림
```

## 관련 파일

- [[typeless-voice-stt-analysis]] — Typeless 분석
- [[vibe-coding-pipeline]] — 바이브코딩 파이프라인
- [[bucky-evolution-roadmap]] — 로드맵

## 다음 할 일

- [ ] WHISPER_MODEL=medium으로 .env 업데이트
- [ ] STT_AI_ENHANCE 실제 테스트 (Discord 음성 → 결과 비교)
- [ ] P3 Multi-Agent Orchestrator 설계
- [ ] 랜딩 페이지 템플릿 실제 생성 테스트 (`!랜딩` 명령)
