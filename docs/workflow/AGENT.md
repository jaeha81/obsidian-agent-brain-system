---
agent: WorkflowAgent
channel: jh-워크플로우
dashboard: docs/workflow/index.html
bucky_inheritance: true
status: active
---

## Role

옵시디언 브레인시스템의 워크플로우 가시화 전용 페이지.
11개 채널 에이전트의 역할, 라우팅 경로, Bucky 상속 구조, 옵시디언 브레인 연결을
한 화면에서 볼 수 있도록 시각화한다.

## Bucky 상속 기반

- Memory Stack: 11개 AGENT.md frontmatter 자동 파싱 스냅샷
- Routing: 정적 시각화 (직접 라우팅 수신 없음)
- Evolution Loop: AGENT.md 변경 → `scripts/build_workflow_data.py` 재실행 → agents.json/health.json 갱신 → 클라이언트 30s 폴링 → 즉시 반영

## Channel Contract

- 수신: 없음 (시각화 전용 페이지)
- 발신: 각 채널 대시보드 링크
- 데이터 소스:
  - `docs/*/AGENT.md` (11개) → `docs/workflow/agents.json`
  - `data/user_checklist.json` · `logs/discord_bot.pid` · `logs/chat_server.log` → `docs/workflow/health.json`

## Domain Skills

- 11개 에이전트 역할·범위·라우팅 자동 시각화
- Bucky 상속 구조 다이어그램 (Mermaid)
- 옵시디언 브레인 연결도 (6 폴더 매핑)
- 채널별 도메인 그룹핑 (오케스트레이션·실행·조율·도메인·개인·감사)
- 실시간 오류 감지: 카드 헬스 뱃지 (녹/노/빨), 런타임 신호 패널, P0 pending/blocked 알람
- 30초 자동 폴링 + STALE 감지 (5분 초과 시 빨간 STALE 뱃지)

## Scope

처리: 워크플로우 시각화, 에이전트 매트릭스, 실시간 헬스 표시
제외: 라우팅 수신, 작업 실행, 직접 수정 (시각화 전용)

## Routing Rules

- AGENT.md 변경 → 사용자/Bucky가 `python -X utf8 scripts/build_workflow_data.py` 재실행 (자동 hook은 Phase 3에서 등록)
- health.json은 빌드 시점 합성 — 진짜 실시간 푸시는 Phase 3 (SSE/WebSocket) 예정
- error/warn 신호 감지 시: Bucky가 Discord 알람 발송 (Phase 3 hook)
- AGENT.md 신규 추가 시 → 빌드 스크립트가 자동 감지 (수동 코드 수정 불필요)

## Build & Verify

```bash
python -X utf8 scripts/build_workflow_data.py
# → docs/workflow/agents.json (N agents)
# → docs/workflow/health.json (runtime snapshot)
```

Vercel 배포 시 `/workflow/*` 경로는 `Cache-Control: no-store` 적용 (vercel.json).
