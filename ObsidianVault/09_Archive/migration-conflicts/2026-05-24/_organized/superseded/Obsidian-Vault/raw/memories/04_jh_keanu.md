# 04 — JH-키아누 (jh-keanu)

> 멀티에이전트 오케스트레이션 시스템. OMO v3.11.0 대비 벤치마크.

---

## 📊 프로젝트 개요

| 항목 | 내용 |
|---|---|
| 레포명 | jh-keanu |
| 목적 | OMO 대비 자체 멀티에이전트 오케스트레이션 |
| 규모 | 64개 파일, 5,158 LOC |
| 상태 | 구현 완료, 핵심 버그 수정 진행 중 |

---

## 🏗️ 아키텍처

### 스택
- **Backend**: FastAPI (Python)
- **Frontend**: Next.js 14
- **Database**: Supabase
- **AI**: Claude API

### 5개 고정 에이전트
| 에이전트 | 역할 |
|---|---|
| RESEARCH | 정보 수집, 기술 조사 |
| PLAN | 아키텍처 설계, 계획 수립 |
| FRONTEND | Next.js 컴포넌트, UI 구현 |
| BACKEND | FastAPI 엔드포인트, 비즈니스 로직 |
| QA | 테스트, 검증, 버그 탐지 |

### 핵심 컴포넌트
- **3-tier hook engine**: 전처리 → 실행 → 후처리 레이어
- **Ralph Loop**: 에이전트 루프 제어 메커니즘
- **Intent Gate**: 요청 의도 분류 (Haiku 모델 사용)
- **Dynamic Prompt Builder**: 컨텍스트 기반 프롬프트 동적 생성
- **Wave Manager**: 병렬 실행 웨이브 관리

---

## 🐛 알려진 버그 (수정 필요)

### Critical: 비동기 클라이언트 문제
```python
# 현재 버그 코드
class ClaudeClient:
    async def send_message(self):
        client = Anthropic()  # ← sync client
        response = client.messages.create(...)  # ← FastAPI event loop 블로킹!
```

### 수정 시퀀스 (우선순위 순)
1. **async client 전환**: `AsyncAnthropic()` 사용
2. **IntentGate Haiku API 업그레이드**: 최신 모델로 교체
3. **슬래시 커맨드**: `/research`, `/plan` 등 커맨드 인터페이스
4. **Supabase Realtime**: 에이전트 상태 실시간 구독

---

## 🔀 JH-하네스와의 차이

| 항목 | JH-키아누 | JH-하네스 |
|---|---|---|
| 목적 | OMO 대비 오케스트레이션 | 멀티하네스 아키텍처 설계 |
| 에이전트 | 5개 고정 | 동적 하네스 구조 |
| 상태 | 구현 완료 | 아키텍처 설계 단계 |

> JH-키아누와 JH-하네스는 **별개 프로젝트**. 혼동 금지.

---

## 📈 OMO v3.11.0 벤치마크 비교

- OMO는 기존 멀티에이전트 오케스트레이션 시스템
- JH-키아누는 이를 대체/개선하기 위해 설계
- 벤치마크 항목: 응답 속도, 에이전트 협업 효율, 비용

---

## 🗓️ 히스토리

- 64개 파일, 5,158 LOC 빌드 완료
- 핵심 버그 (sync/async) 발견
- 수정 시퀀스 4단계 수립
- 현재: async client 전환 작업 중
