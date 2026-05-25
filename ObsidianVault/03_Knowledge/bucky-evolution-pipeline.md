---
tags:
  - bucky
  - evolution
  - pipeline
  - vibe-coding
created: 2026-05-25
---

# Bucky 자가 진화 파이프라인

## 핵심 아키텍처

```
사용자 입력 (음성/텍스트/링크)
         ↓
[STT 고도화] stt_enhanced.py
  - Whisper STT
  - 필러 제거
  - 컨텍스트 인식 교정
  - 구두점 자동 삽입
         ↓
[NLP 전처리기] nlp_preprocessor.py
  - 자연어 → 구조화 포맷
  - STT 오류 교정 사전
  - 액션/컴포넌트/타겟 분류
  - Claude Code/Codex 최적 프롬프트 생성
         ↓
[Claude Code / Codex 실행]
         ↓
[패턴 추출기] pattern_extractor.py
  - 반복 요청 패턴 누적
  - 임계값(2~3회) 초과 시 스킬 생성 권고
  - pattern_db.json에 누적 저장
```

## 구현 파일 목록

| 파일 | 역할 | 상태 |
|------|------|------|
| `scripts/nlp_preprocessor.py` | 자연어 → AI 포맷 변환 | ✅ 완료 |
| `scripts/stt_enhanced.py` | STT 후처리 고도화 | ✅ 완료 |
| `scripts/pattern_extractor.py` | 반복 패턴 감지 + 스킬 권고 | ✅ 완료 |
| `scripts/stripe_payment_server.py` | Stripe 결제 백엔드 (FastAPI) | ✅ 완료 |
| `templates/stripe_payment_template.html` | 결제 UI 템플릿 | ✅ 완료 |

## STT 교정 사전 (주요 항목)

| 오류 | 교정 |
|------|------|
| 타임리스 | Typeless |
| 드래플루 | 그래프 |
| OCD 화면 | Obsidian 화면 |
| 그래플비 | Graphify |
| 캡셔/캡셀 | 캡처/캡슐 |
| 명명 푸넘포트 | well-formed prompt |
| 코덱스 | Codex |

## Typeless 벤치마킹 결과

Typeless (typeless.com) 핵심 기능:
1. 실시간 스트리밍 STT
2. 컨텍스트 인식 교정
3. 커스텀 어휘 사전
4. 명령어 감지

우리 시스템 구현 방식:
- Whisper STT (로컬) + 후처리 파이프라인
- STT_CORRECTIONS 사전 (도메인 특화)
- COMMANDS 딕셔너리 (명령어 감지)
- DiscordSTTSession (채널별 컨텍스트 유지)

## 결제 보일러플레이트

환경변수 (.env):
```
STRIPE_SECRET_KEY=sk_test_...
STRIPE_PUBLISHABLE_KEY=pk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
PRICE_MONTHLY_ID=price_...
PRICE_YEARLY_ID=price_...
```

엔드포인트:
- `GET /` — 랜딩 페이지
- `GET /pay` — 결제 페이지
- `POST /api/create-payment-intent` — 일회성 결제
- `POST /api/create-subscription` — 구독
- `POST /webhook/stripe` — Webhook 처리

## 바이브코딩 파이프라인 (YouTube 분석)

출처: https://youtu.be/nkYY_64Hu4o

핵심 학습:
1. 기획 → 코딩 → 결제 → 배포를 24분 안에
2. Bucky가 레포 정보 읽어 랜딩 페이지 자동 생성
3. Vercel 자동 배포 연결
4. Stripe/Toss 결제 버튼 삽입

## 패턴 추출기 규칙

반복 횟수 임계값:
- 배포 요청 → 2회 → `jh-deploy` 스킬
- 랜딩 생성 → 2회 → `bucky-landing-generator` 스킬
- 코드 리뷰 → 2회 → `jh-code-review` 스킬
- 지식 저장 → 3회 → `jh-capture` 스킬

패턴 DB: `ObsidianVault/00_System/pattern_db.json`

## 다음 단계

- [ ] Stripe 실계정 연동 테스트
- [ ] 패턴 추출기 스케줄 등록 (매일 자정)
- [ ] Discord `/analyze` 명령어 → pattern_extractor 실행
- [ ] NLP 전처리기 → Discord 슬래시 명령어 실시간 연동
