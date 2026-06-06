---
title: "Bucky 진화 로드맵"
source: "user-directive-20260525"
source_type: directive
date: 2026-05-25
captured_at: 2026-05-25T00:00:00
tags:
  - bucky
  - evolution
  - roadmap
  - architecture
  - #area/research
  - #status/active
status: active
summary: "핵심 원칙: **"사용할수록 똑똑해지는 시스템"**"
category: research
next_action: review
---

# Bucky 진화 로드맵

> 핵심 원칙: **"사용할수록 똑똑해지는 시스템"**
> 각 단계는 이전 단계의 출력을 입력으로 사용하는 자가 강화 루프를 형성한다.

## 전체 구조

```
사용자 대화
    ↓
[P0] Knowledge Auto-Capture   ← 현재 구축 중
    ↓
[P1] Pattern Extractor
    ↓
[P2] Self-Reflection Loop
    ↓
[P3] Multi-Agent Orchestrator
    ↑_________________________|
         (피드백 루프)
```

---

## P0: Knowledge Auto-Capture

**목표**: 대화 → Obsidian 자동 기록

- **구현체**: `scripts/bucky_knowledge_capture.py`
- **저장 위치**: `ObsidianVault/01_RAW/YYYY-MM-DD-{slug}.md`
- **트리거**: Discord 메시지, URL 공유, 텍스트 직접 입력
- **출력**: frontmatter 포함 Obsidian 노트 + HANDOFF_LOG 갱신

**완료 기준**:
- [ ] CLI (`--url`, `--text`, `--discord-msg`) 정상 작동
- [ ] Discord 봇 연동 시 자동 호출
- [ ] 01_RAW 저장 + HANDOFF_LOG 업데이트 확인

---

## P1: Pattern Extractor

**목표**: 반복 요청 → 스킬 자동 생성

- **동작**: 01_RAW 노트를 주기적으로 분석, 동일 패턴 3회 이상 감지 시 스킬 초안 생성
- **출력**: `.claude/skills/jh-auto-{name}.md` 초안
- **구현 예정**: `scripts/bucky_pattern_extractor.py`

**핵심 로직**:
```
01_RAW/*.md 스캔
→ 태그·키워드 클러스터링
→ 빈도 임계값 초과 패턴 감지
→ 스킬 템플릿 자동 생성
→ 사용자 검토 요청 (Discord 알림)
```

---

## P2: Self-Reflection Loop

**목표**: 자기 진단 → 약점 개선

- **동작**: 세션 종료 시 오류 로그·미검증 항목 분석 → 개선 제안 생성
- **입력**: `memory/error-log-*.md`, `session-state.md`
- **출력**: `00_System/reflection-report-YYYYMMDD.md`
- **구현 예정**: `scripts/bucky_self_reflection.py`

**반성 항목**:
1. 오늘 발생한 오류와 원인
2. 반복된 실수 패턴
3. 검증 없이 완료 처리된 항목
4. 다음 세션 개선 제안

---

## P3: Multi-Agent Orchestrator

**목표**: 복잡한 작업을 복수 에이전트로 병렬 처리

- **동작**: 작업 의도 분류 → 최적 에이전트 조합 선택 → 결과 통합
- **에이전트 풀**: Bucky(메인), Codex(코드), Research(검색), Archive(기록)
- **구현 예정**: `scripts/bucky_orchestrator.py` (기존 `bucky_sub_agent_manager.py` 확장)

**오케스트레이션 패턴**:
```
사용자 요청
→ 의도 분류 (코드/지식/배포/분석)
→ 에이전트 할당
→ 병렬 실행
→ 결과 통합 → Obsidian 저장 (P0)
→ 패턴 감지 (P1)
```

---

## 진화 타임라인

| 단계 | 상태 | 완료 기준 |
|------|------|----------|
| P0 Knowledge Capture | **진행 중** | CLI + Discord 연동 |
| P1 Pattern Extractor | 대기 | P0 노트 30개 이상 축적 후 |
| P2 Self-Reflection | 대기 | P1 스킬 3개 이상 생성 후 |
| P3 Multi-Agent | 대기 | P2 반성 루프 안정화 후 |

## 관련 개념

[[bucky-awareness]] · [[agent-dispatcher]] · [[knowledge-auto-capture]] · [[session-state]] · [[pattern-extractor]] · [[jh-system]] · [[bucky-evolution-pipeline]] · [[vibe-coding-pipeline]] · [[webhook-vault-write-pattern]] · [[bucky-evolution-session-20260525]] · [[vault-galaxy-graph-bridge]] · [[typeless-voice-stt-analysis]] · [[AgentBus]] · [[ROUTING_RULES]] · [[hubs/Claude Code]]

## 다음 할 일

- [ ] P0: Discord 봇(`discord_bot.py`)에서 `bucky_knowledge_capture.py` 호출 연동
- [ ] P0: `--url` 모드로 YouTube 링크 자동 저장 테스트
- [ ] P1: 패턴 감지 알고리즘 설계 (`pattern_extractor.py` 초안)
