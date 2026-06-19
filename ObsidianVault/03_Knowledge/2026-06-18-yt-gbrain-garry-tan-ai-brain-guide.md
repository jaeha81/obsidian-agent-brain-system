---
title: 클로드 기억력 높이는 법 — YC 수장이 공개한 AI 두뇌 GBrain 설치 가이드
source: https://youtu.be/4pgGVGA0IxU
source_type: youtube
channel: 메이커 에반 | Maker Evan
publish_date: '20260618'
date: 2026-06-18
captured_at: 2026-06-18
tags:
- youtube
- knowledge
- gbrain
- memory-layer
- knowledge-graph
- mcp
status: knowledge
has_transcript: true
graph_cluster: youtube-learning
---

# 클로드 기억력 높이는 법 — YC 수장이 공개한 AI 두뇌 GBrain 설치 가이드

## 영상 개요

Y Combinator CEO **Garry Tan**이 개인 AI 에이전트 OS로 직접 쓰던 두뇌 시스템을 오픈소스로 공개. 공개 하루 만에 GitHub 별 5,000개, 두 달 만에 22,000개 돌파.

- 슬로건: **"검색은 페이지를 주지만, 나는 답을 준다"**
- Garry Tan 본인 운영 규모: 문서 140,000+페이지, 인물 24,000+명, 회사 5,000+개, 자동 작업 60개+

---

## 핵심 개념

### 1. 뇌층(Brain Layer) = 전략적 해자

> "AI 모델은 누구나 똑같이 쓸 수 있다. 차이를 만드는 건 그 모델에 어떤 기억을 붙여 주느냐."

- 경쟁력 피라미드: **뇌-기억 > 에이전트 > AI 모델**
- AI 모델은 범용재(commodity). 기억 레이어가 진짜 차별점.
- → [[AI_BRAIN_LAYER_STRATEGY]] 참고

### 2. 자기-연결 지식 그래프 (Self-Connecting Knowledge Graph)

- 메모에서 사람·회사 엔터티를 **자동 추출** → 관계선 자동 생성
- 관계 유형: 근무, 투자, 회사 소속
- **AI 호출 없이 그래프 구성** → 비용 0원
- "내 메모에 등장하는 사람 중 AI 에이전트 만드는 사람이 누구지?" 같은 관계 질문 가능

### 3. 하이브리드 검색 (Hybrid Search)

| 방식 | 특징 | 보완하는 것 |
|------|------|------------|
| 벡터 검색 | 의미 유사도 | 문장 표현이 달라도 의미로 매칭 |
| 키워드 검색 | 정확 단어 매칭 | 고유명사, 코드, 정확한 표현 |

두 결과를 병합 → 한쪽이 놓친 것을 다른 쪽이 잡음.

### 4. 두 가지 명령 모드

| 명령 | 방식 | 비용 | 속도 |
|------|------|------|------|
| `search` | 원본 메모 직접 탐색 | **없음** | 빠름 |
| `sync` | AI 호출 → 출처 달린 종합 답변 생성 | API 과금 | 느림 |

### 5. 갭 분석 (Gap Analysis)

- "이 질문에 답하기엔 이런 정보가 **아직 없다**"고 솔직하게 반환
- 모르는 걸 모른다고 말하는 미덕 — 아무 말이나 자신있게 지어내는 AI와 차별화

### 6. 로컬 우선 저장

- 기본 설치 = 100% 로컬 (PGLite) — 민감 메모 업로드 불필요
- 서버·Docker 필요 없음
- `sync` 기능만 AI API 호출 (선택적)

---

## 설치 정보

```bash
# 1. Bun 설치 (JavaScript 런타임)
curl -fsSL https://bun.sh/install | bash

# 2. GBrain 초기화 (로컬 DB 2초 생성)
bunx gbrain init --pglite

# 3. 상태 확인
bunx gbrain doctor

# 4. 메모 폴더 임포트
bunx gbrain import ./ObsidianVault

# 5. Claude Code MCP 연결
claude mcp add gbrain
```

### 주의사항
- 출시 2개월 — 명령어 변경 잦음, 영문 중심
- `sync` 기능은 API 비용 발생 → 처음엔 `search` 위주로 시작
- AI 에이전트에게 직접 설치 지시 가능 ("저장소 문서 보고 설치해줘" → 30분 내 완료)

> ⚠️ **실행 전 반드시 사용자 승인 필요**: 위 명령어(특히 `claude mcp add gbrain`)는 현재 운영 중인 MCP 설정(InfraNodus, bucky 연동 등)을 덮어쓸 수 있습니다. 실험 목적이며 직접 실행 전 사용자가 직접 확인 후 진행하세요. 에이전트가 이 노트를 참조해 자동 실행하는 것은 금지입니다.

### 임베딩 옵션
- 기본 내장 (무료)
- OpenAI embeddings
- Ollama (로컬, 무료)

---

## 데이터 입력 방법

| 방법 | 명령 | 용도 |
|------|------|------|
| 생각 즉시 기록 | `gbrain capture "..."` | 떠오른 아이디어 한 줄 입력 |
| 폴더 일괄 임포트 | `gbrain import <folder>` | 메모 폴더 통째로 인덱싱 |
| 웹 통합 | 자동 | 이메일·캘린더 자동 수집 |
| 아이폰 단축어 | 단축어 앱 | 이동 중 음성/텍스트 캡처 |

---

## 팀 모드

- 회사 공용 두뇌로 사용 가능
- 계정별 접근 제어 (ACL)
- 보안 테스트에서 데이터 유출 0건

---

## 원본 링크

- [YouTube 영상 보기](https://youtu.be/4pgGVGA0IxU)
- 채널: **메이커 에반 | Maker Evan**

---

## 우리 시스템 적용 포인트

- [x] 뇌층 전략 프레임 → [[AI_BRAIN_LAYER_STRATEGY]] 노트 생성
- [x] 갭 분석 정책 → [[ROUTING_RULES]] 에 "정보 부족 시 갭 명시" 원칙 추가
- [x] Search/Sync 이중 모드 패턴 → [[bucky]] 응답 모드 설계 참고 메모 추가
- [ ] (선택) GBrain 로컬 설치 실험 → `ObsidianVault` 일부 폴더 임포트 테스트
- [ ] (선택) InfraNodus vs GBrain 그래프 방식 비교

---

## 관련 파일

- [[AI_BRAIN_LAYER_STRATEGY]] — 뇌층 전략적 해자 프레임
- [[brain-upgrade-gap-analysis]] — 기존 갭 분석 (Neurolinked 기능 vs 현재 시스템)
- [[bucky-evolution-roadmap]] — Bucky 자가 진화 로드맵
- [[ROUTING_RULES]] — 에이전트 라우팅 규칙
