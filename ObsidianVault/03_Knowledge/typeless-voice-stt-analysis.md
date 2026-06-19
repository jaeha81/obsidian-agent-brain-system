---
graph_cluster: typeless-voice
---

# Typeless — AI 음성받아쓰기 서비스 분석

> "Speak, don't type" — 음성을 자연스러운 텍스트로 변환하는 AI 도구.
> 우리 시스템의 Discord 음성 인식 업그레이드를 위해 벤치마킹.

## 서비스 개요

| 항목 | 내용 |
|------|------|
| **핵심 기능** | 음성 → 정제된 텍스트 자동 변환 |
| **속도** | 타이핑 대비 4배 빠름 |
| **AI 편집** | 필러 제거("음", "어"), 반복 제거, 자동 형식화 |
| **개인화** | 사용자 말투·어휘 학습 |
| **다국어** | 100+ 언어 자동 감지 |
| **번역** | 실시간 음성 번역 |
| **프라이버시** | 클라우드 저장 없음 |
| **가격** | 무료 다운로드 + $5 크레딧 (세부 플랜 미공개) |
| **Discord 연동** | 공식 미지원 |

## Discord 직접 활용 가능성

**결론: 직접 사용 불가 (Discord 플러그인 없음)**

Typeless는 macOS/Windows 시스템 레벨 받아쓰기 앱으로,
Discord 봇 API와 직접 연동되지 않는다.

## 우리 시스템 적용 전략

### 옵션 1: Typeless 벤치마킹 → 자체 구현

현재 우리 봇에 이미 Whisper STT가 있음 (`discord_bot.py`).
Typeless의 **AI 후처리 레이어**를 추가 구현:

```python
# 추가할 파이프라인
음성 수신 (discord-ext-voice-recv)
    ↓
Whisper STT (현재 있음)
    ↓
[NEW] AI 후처리 (Claude API)
  - 필러 제거 ("음", "어", "그", "저")
  - 반복 문장 정리
  - 의도 명확화
    ↓
Bucky 처리
```

### 옵션 2: 현재 Whisper 개선 (즉시 가능)

Whisper 모델을 `small` → `medium` 또는 `large-v3`로 교체하면
한국어 인식 정확도 30~40% 향상.

```env
WHISPER_MODEL=medium  # 현재: small
```

### 옵션 3: OpenAI Whisper API 연동

로컬 모델 대신 OpenAI API Whisper로 교체 → 속도 개선 + 정확도 향상.

## 구현 우선순위

| 우선순위 | 작업 | 예상 시간 |
|---------|------|---------|
| P0 즉시 | Whisper 모델 `medium`으로 교체 | 5분 |
| P1 | AI 후처리 레이어 추가 (필러 제거) | 2시간 |
| P2 | 개인화 학습 (사용자 어휘 사전) | 1일 |
| P3 | 실시간 번역 기능 | 2일 |

## 관련 개념

[[voice-stt]] · [[whisper-model]] · [[discord-bot]] · [[bucky-voice]] · [[ai-postprocessing]]

## 시스템 연결

- [[bucky-evolution-pipeline]] — STT가 Bucky 진화 파이프라인의 입력 레이어
- [[bucky-evolution-roadmap]] — P0 단계: 음성 → Knowledge Auto-Capture로 연결
- [[vault-galaxy-graph-bridge]] — 전체 지식 허브 MOC (음성 캡처 → Vault 기록)
- [[webhook-vault-write-pattern]] — 음성 STT 결과를 Vault에 기록하는 패턴
- [[ROUTING_RULES]] — 음성 입력 → 라우팅 규칙 → Claude Code / Codex 실행
- [[hubs/Claude Code]] — STT 입력이 최종적으로 Claude Code 태스크로 전환됨

## 다음 할 일

- [ ] `.env`에서 `WHISPER_MODEL=medium` 으로 변경
- [ ] `scripts/bucky_voice.py`에 AI 후처리 레이어 추가
- [ ] Typeless 스타일 필러 제거 프롬프트 작성
