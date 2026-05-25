# Obsidian Brain System — 자기진화 아키텍처 계획

> 목표: Bucky가 GPT/Claude/Codex 대화를 자동 수집 → 지식베이스 정제 → 시스템 자기진화 오케스트레이션
> 작성일: 2026-05-25

---

## 비전

```
[LLM 서비스들]                [Obsidian 지식베이스]
GPT / Claude / Codex  ──→  ObsidianVault/ (구조화된 지식)
       ↑                         ↓
   대화/개발               Bucky 오케스트레이터
       ↑                         ↓
[Claude Code / Codex]  ←──  태스크 배분 + 진화 루프
```

**핵심 원칙:**
- 사용자가 어느 LLM 서비스에서 작업하든 → Obsidian에 자동 축적
- Bucky가 지식갭 감지 → 개발 태스크 자동 생성 → 시스템 스스로 진화
- Vault = 두뇌, AgentBus = 신경계, Bucky = 오케스트레이터

---

## Phase 1: LLM 대화 수집 자동화 (2주)

### 1-1. GPT 세션 수집 강화

**현황:** `chatgpt_daily_collector.py` — 특정 URL 하나만 수집

**목표:** 모든 GPT 대화 자동 수집

| 수집 방법 | 설명 | 난이도 |
|-----------|------|--------|
| ChatGPT 공식 내보내기 API | `GET /conversations` (비공식) + 세션 쿠키 | 중 |
| Playwright 자동화 | conversations 목록 크롤링 | 중 |
| ChatGPT 데이터 내보내기 | settings → export → ZIP 파일 | 낮음 (수동) |
| browser extension hook | 실시간 대화 캡처 | 높음 |

**선택 전략:** Playwright 기반 확장 (기존 스크립트 재활용)

```
scripts/gpt_session_collector.py (신규)
  - 모든 conversations 목록 조회
  - 신규/업데이트 대화만 차등 수집
  - ObsidianVault/01_RAW/gpt-sessions/YYYY-MM-DD/ 저장
  - 수집 메타데이터: title, created_at, message_count, topics
```

### 1-2. Claude 대화 수집

**현황:** 없음

**목표:** claude.ai 대화 → Vault 저장

```
scripts/claude_session_collector.py (신규)
  - claude.ai Playwright 자동화
  - 프로젝트별 대화 분류
  - 01_RAW/claude-sessions/ 저장
```

### 1-3. Codex 세션 수집

**현황:** `codex_session_handoff.py` 존재 (일부 구현)

**목표:** Codex 작업 로그 → Vault 자동 저장

```
scripts/codex_log_collector.py (강화)
  - Claude Code CLI output 캡처
  - 코드 변경 diff 포함 저장
  - 01_RAW/codex-sessions/ 저장
```

### 1-4. 통합 스케줄러

```
scripts/collection_scheduler.py (신규)
  - 매일 오전 6시: GPT 수집
  - 세션 종료 시 훅: Claude/Codex 수집
  - 실패 시 재시도 + Discord 알림
```

---

## Phase 2: 지식 정제 파이프라인 (2주)

### 2-1. 대화 → 지식 변환

수집된 원시 대화를 구조화된 지식으로 변환

```
scripts/knowledge_distiller.py (신규)

입력: 01_RAW/*/YYYY-MM-DD/*.md
출력: 03_Knowledge/distilled/YYYY-MM/

처리:
  1. Claude API로 핵심 인사이트 추출
  2. 토픽 클러스터링 (기존 Graphify 활용)
  3. 기존 지식과 중복 제거
  4. 메타데이터 태깅: #gpt-session #claude-session #dev #strategy
```

**출력 포맷:**
```markdown
---
source: gpt-session
date: 2026-05-25
topics: [architecture, agent-design, python]
confidence: 0.85
---

## 핵심 인사이트
...

## 연관 지식
- [[existing-note-1]]
- [[existing-note-2]]

## 실행 가능한 태스크
- [ ] ...
```

### 2-2. 지식 그래프 자동 업데이트

```
scripts/graphify_auto_update.sh (강화)
  - 신규 지식 노트 감지 (inotify/watchdog)
  - Graphify 증분 업데이트
  - 지식 클러스터 변화 감지 → Bucky 알림
```

### 2-3. 갭 분석기

```
scripts/knowledge_gap_analyzer.py (신규)
  - 지식 그래프 구조 분석
  - 약한 연결 노드 = 잠재적 지식 갭
  - 반복 언급되지만 문서화 안 된 개념 감지
  - 갭 리스트 → AgentBus에 태스크로 등록
```

---

## Phase 3: Bucky 오케스트레이터 (3주)

### 3-1. Bucky 진화 루프 엔진

```
scripts/bucky_evolution_engine.py (신규)

루프 사이클 (매일 자정):
  1. 지식갭 분석 실행
  2. 개발 아이디어 생성 (Claude API)
  3. 우선순위 정렬 (임팩트 × 실현가능성)
  4. 태스크 카드 생성 → AgentBus/inbox
  5. Claude Code / Codex에 배분
  6. 결과 → 02_Processed 저장
  7. 자기진화 로그 → 00_System/evolution-log.md
```

### 3-2. Bucky Discord 강화

**현황:** 기본 Q&A 봇

**추가 기능:**

```
/evolve status    → 현재 진화 루프 상태
/evolve tasks     → 자동 생성된 태스크 목록
/evolve run       → 즉시 진화 사이클 실행
/knowledge gap    → 현재 지식갭 리포트
/knowledge add    → 음성/텍스트 → 즉시 Vault 저장
```

### 3-3. 자기진화 태스크 라우팅

```
AgentBus 태스크 유형 확장:

기존:
  discord_intake, implementation_request, review_request

신규:
  knowledge_distillation  → bucky_distiller
  gap_analysis            → knowledge_gap_analyzer
  evolution_task          → harness_router → Claude Code / Codex
  self_improvement        → Bucky가 자신의 스크립트 개선 제안
```

### 3-4. 진화 메트릭 대시보드

```
ObsidianVault/00_System/evolution-metrics.md (자동 업데이트)

## 지식베이스 상태
- 총 노트: N개
- 이번 주 신규: N개
- 지식갭 감지: N개
- 해결된 갭: N개

## 시스템 진화
- 이번 달 자동 생성 스크립트: N개
- Claude Code 자동 태스크: N개
- 성공률: N%
```

---

## Phase 4: Obsidian 플러그인 연동 (1주)

### 4-1. 핵심 플러그인 설정

| 플러그인 | 용도 |
|----------|------|
| **Dataview** | 지식 그래프 쿼리, 대시보드 |
| **Templater** | 지식 노트 자동 생성 |
| **QuickAdd** | 빠른 지식 캡처 훅 |
| **Periodic Notes** | 일일/주간 지식 리포트 |
| **Nexus AI Chat Importer** | GPT/Claude 대화 임포트 |

### 4-2. Dataview 대시보드

```dataview
TABLE source, date, topics
FROM "03_Knowledge/distilled"
WHERE date >= date(today) - dur(7 days)
SORT date DESC
```

---

## 실행 로드맵

```
Week 1-2:  Phase 1 — 수집 파이프라인 구축
Week 3-4:  Phase 2 — 지식 정제 엔진
Week 5-7:  Phase 3 — Bucky 진화 루프
Week 8:    Phase 4 — Obsidian 플러그인 연동
```

## 즉시 시작 가능 작업

1. `gpt_session_collector.py` — 기존 daily_collector 확장
2. `knowledge_distiller.py` — Claude API 활용 핵심 추출
3. `knowledge_gap_analyzer.py` — Graphify 결과 파싱
4. Discord `/evolve` 명령어 추가

---

## 기술 스택

| 레이어 | 도구 |
|--------|------|
| 수집 | Playwright, Python watchdog |
| 정제 | Claude API (claude-sonnet-4-6) |
| 지식 그래프 | Graphify (Neo4j 기반) |
| 오케스트레이션 | AgentBus (파일 기반 큐) |
| UI | Discord 봇, Obsidian Dataview |
| 스케줄 | Windows Task Scheduler / cron |

---

## 성공 기준

- [ ] GPT 대화 자동 수집률 > 95%
- [ ] 대화 → 지식 변환 소요 시간 < 5분
- [ ] 주간 지식갭 자동 감지 > 5개
- [ ] Bucky 자동 태스크 생성 > 3개/주
- [ ] 시스템 자기진화 루프 완전 자동화
