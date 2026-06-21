---
type: agent-role
agent: pulse_evolution
status: active
created: 2026-05-27
tags:
  - #area/business_model
  - #status/active
summary: "Pulse Evolution Agent는 매일 ChatGPT Pulse(오늘의 플러스)를 전담한다."
category: business_model
next_action: review
---

# Pulse Evolution Agent

## Role

Pulse Evolution Agent는 매일 ChatGPT Pulse(오늘의 플러스)를 전담한다.

## Daily Contract

1. `scripts/chatgpt_daily_collector.py --collect`가 Pulse 원문을 `04_Wiki/daily-plus/YYYY-MM-DD.md`에 저장한다.
2. `scripts/pulse_evolution_agent.py`가 원문 노트를 읽고 모든 카드 상세를 업그레이드 후보로 분류한다.
3. 결과는 `00_UPGRADE/pulse-evolution/YYYY-MM-DD.md`에 저장한다.
4. 실행 작업은 `10_AgentBus/inbox/YYYYMMDD_pulse_evolution_agent.md`에 생성한다.
5. 핵심 지침, 프롬프트, 스케줄, 자동화 변경은 바로 덮어쓰지 않고 검토 큐로 보낸다.

## Outputs

- Raw capture: `04_Wiki/daily-plus/`
- Upgrade report: `00_UPGRADE/pulse-evolution/`
- Run index: `00_UPGRADE/PULSE_EVOLUTION_INDEX.md`
- AgentBus task: `10_AgentBus/inbox/`

## Owners

- `collector`: Pulse 수집과 원문 보존
- `pulse_evolution`: 카드 상세 분석과 업그레이드 후보 분류
- `distiller`: append-only 지식화
- `codex`: 검증 체크리스트, 위험 변경 검수
- `bucky`: 적용 우선순위 결정과 사용자 승인 요청

*Related: [[agents-hub]]*

