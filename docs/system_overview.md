# System Overview
> Created: 2026-05-22

## Purpose

Obsidian Agent Brain System은 개인 지식 관리와 AI 에이전트 협업을 통합한 시스템이다.
Obsidian이 중심 두뇌 역할을 하고, Claude Code와 Codex가 실행 에이전트로 작동한다.

## Core Principle

> "Agent가 Obsidian을 사용하는 것이 아니라, Obsidian이 Agent를 조율한다."

## System Layers

### Layer 1 — Storage (Google Drive)
- `ObsidianVault/`: 실제 노트, 위키, 컨텍스트 팩
- `RAW_IMPORT/`: 음성, 미팅, 클라이언트 원본
- `external_data/`: 외부 데이터 (legalize-kr, graphify_selected)
- `backups/`: 주기적 백업

### Layer 2 — Version Control (GitHub)
- 스크립트, 템플릿, 프롬프트, vault_scaffold
- ObsidianVault 데이터는 포함하지 않음

### Layer 3 — Brain (ObsidianVault)
- `00_System/`: 시스템 제어 파일 (AGENT_STATE, ROUTING_RULES 등)
- `01_RAW/` ~ `09_Archive/`: 지식 레이어
- `10_AgentBus/`: 에이전트 파일 기반 통신

### Layer 4 — Agents
- Claude Code: 구현, 운영
- Codex: 독립 검토
- InfraNodus: 개념 그래프 분석
- Graphify: 코드/문서 관계 그래프
- legalize-kr: 한국 법률 지식

## Data Flow

```
음성/미팅 입력
    ↓
RAW_IMPORT/ (Google Drive)
    ↓
AgentBus inbox (10_AgentBus/inbox/)
    ↓
Claude Code 처리
    ↓
01_RAW/ 또는 02_Processed/ 저장
    ↓
03_Projects/ 또는 04_Wiki/ 업데이트
    ↓
Context Pack 생성 (06_Context_Packs/)
    ↓
다음 작업에 활용
```

## Key Files

| 파일 | 역할 |
|------|------|
| `00_System/AGENT_STATE.md` | 현재 에이전트 상태, 활성 잠금 |
| `00_System/ROUTING_RULES.md` | 작업 라우팅 규칙 |
| `00_System/MASTER_PLAN.md` | 전체 시스템 계획 |
| `00_System/TASKS.md` | 현재 작업 목록 |
| `00_System/HANDOFF_LOG.md` | 세션 인수인계 기록 |
| `10_AgentBus/inbox/` | 에이전트 수신함 |
