---
type: knowledge
source: tiktok/@luke.builds.ai
agent: Claude Code
status: done
created: 2026-06-07
tags:
- '#area/ai_automation'
- '#topic/multi-agent'
- '#topic/agent-architecture'
- '#status/active'
summary: '@luke.builds.ai TikTok 7개 영상 전수 분석 — Jarvis 멀티에이전트 시스템 아키텍처, 운영 패턴, JH 브레인시스템
  적용 갭 분석'
category: ai_automation
next_action: apply-gap-analysis
graph_cluster: misc
---

# @luke.builds.ai Jarvis System — 기술 분석 및 JH 적용 가이드

> 분석 대상: TikTok @luke.builds.ai 전체 영상 7개 (2026-06-07 기준)  
> 분석 방법: yt-dlp 다운로드 → ffmpeg 프레임 추출 → Whisper 음성 전사 → 프레임 시각 분석

---

## 1. 영상별 핵심 내용 요약

| # | 제목 | 길이 | 핵심 주제 |
|---|------|------|----------|
| V1 | The future of work is here | 66s | Slack 기반 멀티에이전트 워크스페이스 |
| V2 | Jarvis is the MVP | 71s | 일일 비즈니스 브리핑 + 자율 실행 패턴 |
| V3 | Why you can't install Jarvis | 66s | 전체 아키텍처 다이어그램 설명 |
| V4 | 99.9% aren't using it fully | 72s | V2 확장판 — 에이전트 자율 결정 사례 |
| V5 | Building a $30k MRR app | 47s | 수익 목표 자동 추적 + 적응형 목표 설정 |
| V6 | Business owners aren't using AI | 66s | 콘텐츠 전략 자동 최적화 |
| V7 | The future is here | 40s | Sarah 고객지원 에이전트 + 메모리 학습 루프 |

---

## 2. Jarvis 시스템 아키텍처

### 2.1 전체 구조 (V3 다이어그램 기반)

```
┌─────────────────────────────────────────────────────────┐
│                    REASONING CORE                        │
│              LLMs: Claude + ChatGPT                      │
└───────────────────────┬─────────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────────┐
│              J.A.R.V.I.S. (Main Hub)                    │
│                                                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────┐  │
│  │   Tom    │  │  Sarah   │  │   Eva    │  │ Scout  │  │
│  │Developer │  │Customer  │  │ Content  │  │Content │  │
│  │          │  │Support   │  │ Manager  │  │Research│  │
│  └──────────┘  └──────────┘  └──────────┘  └────────┘  │
│  ┌──────────┐                                            │
│  │  Bobby   │                                            │
│  │   Ads    │                                            │
│  └──────────┘                                            │
└──────────┬──────────────────────────┬────────────────────┘
           │                          │
┌──────────▼──────────┐  ┌───────────▼───────────────────┐
│   CHANNELS           │  │   CONNECTORS (Tools)           │
│  • Slack (primary)  │  │  • Gmail      • Instagram      │
│  • iMessage         │  │  • TikTok     • YouTube        │
│  • Voice            │  │  • Meta Ads   • Google Ads     │
└─────────────────────┘  │  • Calendar   • Google Drive   │
                          │  • Stripe     • External Tools │
                          └───────────────────────────────┘
```

### 2.2 에이전트 역할 분담

| 에이전트 | 역할 | 담당 도메인 |
|---------|------|------------|
| **Jarvis** | 메인 오케스트레이터 | 전체 조율, 일일 브리핑, 의사결정 |
| **Sarah** | 고객지원 | 이메일 처리, 고객 응답 초안, 리뷰 모니터링 |
| **Tom** | 개발자 | 버그 조사, 코드 구현, PR 생성 |
| **Eva** | 콘텐츠 매니저 | 콘텐츠 편집, 포스팅 관리 |
| **Scout** | 콘텐츠 리서처 | 광고 각도 조사, 콘텐츠 아이디어 |
| **Bobby** | 광고 | 광고 성과 모니터링, 예산 조정 |

---

## 3. 핵심 운영 패턴

### 3.1 일일 CEO 브리핑 패턴 (V2, V4, V5, V6)

매일 Jarvis가 전달하는 표준 브리핑 구조:

```
[일일 브리핑 형식]
1. 앱 지표: 신규 다운로드 수, 수익
2. 광고 성과: 지출액, ROAS, 크리에이티브별 성과
3. 유기 콘텐츠: 총 조회수, 포스팅 현황, 트렌드
4. 고객 이메일: 수신량, 자동처리 수, 에스컬레이션
5. 완료된 자율 작업 보고
6. 오늘의 추천 액션 (3가지)
7. "What would you like me to handle first, sir?"
```

실제 출력 예시 (V2):
> "Over the last 7 days we had 2,459 new downloads and generated $4,289 in revenue.
> On ads you spent $475 at a 1.5 ROAS. The street interview creative is still doing well.
> I resolved 13 customer emails automatically... Since you approved that direction, I handed it to Tom.
> My recommendation today: review the backend PR, keep leaning into the street interview ad angle,
> and have Scout research the next set of organic content angles."

### 3.2 자율 완료 + 보고 패턴

에이전트는 **사용자가 이전에 승인한 방향**이면 자율적으로 완료한 뒤 보고한다:

```
사용자 사전 승인 → 에이전트 자율 실행 → 완료 보고 → 검토 요청
```

예: "Since you had already approved that direction, I handed it to Tom, the developer agent.
We built the backend implementation and it's now ready for your review."

### 3.3 에이전트 간 에스컬레이션 프로토콜 (V1)

```
#customer-emails 채널
  Sarah: 고객 이메일 수신 → 응답 초안 작성
    │
    ├─ 일반 문의 → 직접 처리 (자율)
    │
    └─ 버그 감지 → #dev 채널 에스컬레이션
         │         메시지: "Customer engineering review"
         │         + 원본 이메일 발췌
         │         + @Tom 멘션
         ▼
       Tom: 조사 완료 → 보고서 작성 → "Luke, do you want me to implement this?"
         │
         ├─ Luke: "Yes, go ahead" (Human-in-the-loop)
         │
         └─ Tom: 구현 → PR 생성 → GitHub 링크 → "Done: PR#15"
```

### 3.4 Human-in-the-loop 게이트

사용자 승인이 필요한 지점:

| 게이트 | 트리거 | 에이전트 행동 |
|--------|--------|--------------|
| PR 검토 | 개발 완료 | Tom이 PR 링크 공유 후 대기 |
| 환불 승인 | 환불 요청 수신 | Sarah가 승인 요청 후 대기 |
| 예산 변경 | 광고 성과 저조 | Bobby가 제안 후 대기 |
| 버그 구현 | 조사 완료 | Tom이 "구현할까요?" 질문 |

### 3.5 에이전트 메모리/학습 루프 (V7)

```
Luke가 Sarah 이메일 초안에 피드백 입력
  → Sarah가 수정 반영 → 발송
  → "every time I give her a suggestion, she remembers it"
  → 이후 이메일은 자동으로 개선된 스타일 적용
```

인터페이스: Slack 스레드에 Luke가 댓글 → Sarah가 초안 업데이트 → 재승인 → 발송

### 3.6 적응형 목표 추적 (V5)

```
목표: $15,000 MRR
  ↓
달성: "Congratulations sir, you've hit our goal"
  ↓
자동 조정: "I'm now adjusting our target to $30,000"
```

시스템이 목표를 자동으로 상향 조정하고 다음 전략을 제시한다.

### 3.7 콘텐츠 전략 자동 최적화 (V6)

```
콘텐츠 성과 분석 → 패턴 발견
  "strongest performers are opening with more curiosity"
    ↓
자율 전략 수정
  "I'm shifting the next batch in that direction"
```

사용자 승인 없이 콘텐츠 방향을 자동으로 조정한다.

---

## 4. 핵심 인사이트

### 4.1 "UI보다 Slack이 진짜 일터" (V1)

> "The Jarvis UI is cool and all, but Slack is where work actually gets done."

커스텀 UI는 시각적 접점일 뿐, 실제 에이전트 협업은 메시징 플랫폼(Slack/Discord)에서 이루어진다.

### 4.2 "설치가 아닌 빌드" (V3)

> "Jarvis is not something you can just install. It's something you build and train around your business."

에이전트 OS는 비즈니스 맥락과 함께 점진적으로 구축되는 시스템이다. 도구 연결 → 에이전트 학습 → 패턴 축적 → 자율화 증가.

### 4.3 에이전트는 "AI 팀"

> "That's what makes AI feel like a real team working inside your business."

각 에이전트는 독립된 역할과 책임을 가진 팀원이다. Orchestrator가 조율, 전문 에이전트가 실행.

---

## 5. JH 브레인시스템 갭 분석

### 5.1 현재 우리 시스템과의 매핑

| Luke의 Jarvis | JH 브레인시스템 | 상태 |
|--------------|----------------|------|
| Slack 워크스페이스 | Discord (#jh-chat/tasks/status/results) | ✅ 구현됨 |
| Jarvis (오케스트레이터) | Bucky | ✅ 구현됨 |
| Tom (개발자) | Claude Code | ✅ 구현됨 |
| Codex 검수 | Codex | ✅ 구현됨 |
| 다중 LLM (Claude + GPT) | Sonnet + Haiku 라우팅 | ✅ 구현됨 |
| 일일 브리핑 (자동) | daily-plus.html (수동 업데이트) | ⚠️ 수동 |
| Sarah (고객지원 에이전트) | 없음 | ❌ 미구현 |
| Eva (콘텐츠 매니저) | 없음 | ❌ 미구현 |
| Scout (리서치) | 없음 | ❌ 미구현 |
| 에이전트 메모리/학습 | 없음 | ❌ 미구현 |
| Gmail 연결 | 없음 | ❌ 미구현 |
| 콘텐츠 자동 포스팅 | 없음 | ❌ 미구현 |
| 수익 KPI 자동 추적 | 없음 | ❌ 미구현 |
| 음성 인터페이스 | 없음 | ❌ 미구현 |
| 적응형 목표 추적 | 없음 | ❌ 미구현 |

### 5.2 우선 적용 가능 항목 (임팩트 순)

#### P0: 일일 Discord 브리핑 자동화

Luke의 일일 브리핑을 Bucky Discord로 이식. 현재 daily-plus.html은 수동 갱신이라 실시간성 부족.

**구현 방향:**
```python
# scripts/daily_briefing.py
# 매일 오전 9시 Discord #jh-status 채널에 자동 브리핑
# 포함 내용:
#   - Wishket 견적 현황 (오늘 수신/응답/낙찰)
#   - AgentBus 태스크 현황 (완료/진행중/대기)
#   - 수익 KPI (이번주 수주액/목표 대비)
#   - 추천 오늘의 액션 3가지
```

#### P1: Wishket 클라이언트 이메일 핸들러 (Sarah 역할)

Wishket 문의/낙찰 알림 → 자동 초안 작성 → Discord #jh-tasks로 확인 요청

**구현 방향:**
```
Wishket 이메일 수신 (Gmail 폴링)
  → Sarah-equivalent 에이전트가 초안 작성
  → Discord 스레드로 Luke에게 전달
  → 승인/수정 → 발송
  → 피드백 학습
```

#### P2: 에이전트 간 에스컬레이션 채널 구조화

현재 #jh-tasks 단일 채널 → 역할별 채널 분리

```
#jh-tasks → #jh-dev (코드 작업)
           → #jh-client (클라이언트 관리)
           → #jh-content (콘텐츠 작업)
           → #jh-research (리서치)
```

#### P3: 에이전트 메모리/학습 루프

Discord 스레드 피드백 → 에이전트 context 업데이트

```python
# 구현 패턴
# 1. 에이전트 출력을 Discord 스레드로 전달
# 2. 사용자가 스레드에 수정 지시
# 3. 수정 내용을 ObsidianVault/agent-memory/{agent}.md에 기록
# 4. 다음 실행 시 memory 파일 로드
```

---

## 6. 즉시 적용 가능한 설계 원칙

### 원칙 1: 에이전트는 "보고 후 대기"가 아닌 "완료 후 보고"

현재: Claude Code → 작업 완료 → 사용자에게 보고  
Luke 방식: 에이전트 → 자율 완료 → 검토 대기 상태로 전환

사전 승인된 작업 범주(예: "Wishket 기술 스택 분석", "비용 계산")는 자율 완료 후 결과물만 전달.

### 원칙 2: 일일 브리핑은 의사결정 지원, 단순 현황 보고가 아님

현재 daily-plus는 현황 표시. Luke의 Jarvis는 **3가지 추천 액션**과 **우선순위 질문**을 포함.

### 원칙 3: 메시징 플랫폼이 에이전트의 1차 인터페이스

커스텀 대시보드는 시각화 보조. 실제 지시/승인/피드백은 Discord 채널에서.

### 원칙 4: 에이전트 이름과 페르소나

이름이 있는 에이전트(Sarah, Tom)는 역할 경계가 명확하고 사용자가 책임 소재를 직관적으로 인식.  
JH에도 역할별 에이전트 페르소나를 부여하면 협업 투명성 향상.

---

## 7. 참고 링크

- TikTok 채널: https://www.tiktok.com/@luke.builds.ai
- V3 아키텍처 다이어그램: Obsidian-Agent-Brain-System의 Agentic AI 구조와 동일한 레이어 구성
- 관련 Vault 파일: `ObsidianVault/03_Projects/agents/bucky.md`, `ObsidianVault/06_Context_Packs/bucky-context-efficiency-goal-mode.md`
