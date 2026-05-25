# Bucky 서브에이전트 아키텍처

## 역할 분담 원칙

- Bucky = 오케스트레이터만. 직접 구현하지 않음
- Claude Code = 코드 구현·파일 변경
- Codex = 독립 검수·분석·검색
- Sub-agents = 전문 태스크 자동화

## 에이전트 맵

```
[사용자 Discord/음성]
         ↓
    [Bucky 오케스트레이터]
    ├── 구현 태스크 → [Claude Code Agent] → AgentBus inbox/claude/
    ├── 검수 태스크 → [Codex Agent] → AgentBus inbox/codex/
    ├── 수집 태스크 → [Collector Sub-agent]
    ├── 정제 태스크 → [Distiller Sub-agent]
    ├── 갭 분석    → [Gap Analyzer Sub-agent]
    └── 리포트     → [Reporter Sub-agent]
             ↓
    [ObsidianVault 지식베이스]
             ↓
    [자기진화 루프]
```

## AgentBus 디렉토리 구조

```
ObsidianVault/AgentBus/
├── inbox/
│   ├── claude/    # Claude Code 태스크
│   └── codex/     # Codex 검수 태스크
├── outbox/
│   ├── completed/ # 완료된 태스크
│   └── failed/    # 실패 태스크
└── messages/
    └── agent-room-messages.jsonl  # 통합 메시지 로그
```

## Agent Room 마이그레이션

- G드라이브 JH-Agent-Room Express 서버 → 비활성화 (로컬 충돌 방지)
- 메시지 데이터 → ObsidianVault/AgentBus/messages/ 로 통합
- Claude Code/Codex는 G드라이브 Agent Room 경로 접근 금지
- 모든 에이전트 통신은 AgentBus JSONL 단일 진입점

## 금지 경로 (Claude Code / Codex)

- `G:/내 드라이브/JH-Agent-Room/` — 읽기/쓰기 금지
- `D:/ai프로젝트/JH-Agent-Room/` — 읽기/쓰기 금지
- 대신 `ObsidianVault/AgentBus/` 사용

## Sub-agent 파일 목록

| 파일 | 역할 | 트리거 |
|------|------|--------|
| `bucky_collector_agent.py` | GPT/Claude/Codex 대화 수집 | 매일 6시 자동 |
| `bucky_distiller_agent.py` | 수집 대화 → 구조화 지식 | 수집 완료 후 |
| `bucky_gap_agent.py` | 지식갭 감지 → 태스크 등록 | 매주 월요일 |
| `bucky_reporter_agent.py` | 데일리 리포트 생성 | 매일 22시 |
| `bucky_dispatcher.py` | 태스크 유형 분류 + 에이전트 배분 | Discord 명령 수신 시 |
