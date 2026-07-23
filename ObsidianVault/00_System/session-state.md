---
updated: 2026-05-31
verified_stale: 2026-07-23
status: stale-historical
session: Bucky Agent OS — C drive cleanup incident recovery and runtime recheck
---

# Session State

> ⚠️ **2026-07-23 확인: 이 파일은 2026-05-31 시점 스냅샷에서 갱신되지 않았다.** 아래 "Current Focus"/incident 내용은 이미 종료된 과거 사건이며 현재 상태가 아니다. 현재 상태는 `BUCKY_CONTEXT.md`, `ROUTING_RULES.md`, `AGENT_STATE.md`, 최신 `HANDOFF_LOG.md`, `ObsidianVault/06_Context_Packs/index.md`에서 확인한다.

이 파일은 현재 세션의 빠른 재개 정보다. canonical 운영 지침은 `BUCKY_CONTEXT.md`, `ROUTING_RULES.md`, `AGENT_STATE.md`, `ObsidianVault/06_Context_Packs/index.md`를 우선한다.

## Current Focus

C: drive cleanup 이후 Bucky Agent OS 런타임과 세션 운영 규칙을 재점검하는 상태다. AgentBus incident notice가 생성되었고, 다음 세션은 아래 incident 파일과 런타임 재점검 노트를 먼저 읽어야 한다.

## Active Incident / Recovery Context (2026-05-31)

1. **C: cleanup incident notice 저장 완료**
   - `ObsidianVault/10_AgentBus/handoffs/20260531_162046_c_drive_cleanup_incident_notice.md`
   - `ObsidianVault/10_AgentBus/outbox/Codex/20260531_162046_c_drive_cleanup_incident_notice.md`
   - `ObsidianVault/10_AgentBus/outbox/ClaudeCode/20260531_162046_c_drive_cleanup_incident_notice.md`
2. **정리된 영향**
   - C: 캐시 정리로 약 16.84 GB 회수.
   - `G:\내 드라이브\obsidian-agent-brain-system` 내부 파일을 의도적으로 삭제한 증거는 없음.
   - `ms-playwright` 삭제로 Codex Playwright 런타임이 깨졌다가 재설치/복구됨.
   - Bucky Discord bot은 stale PID 상태가 관찰되었고, incident 작성 시점에는 PID `71788` 재연결로 기록됨.
   - 2026-05-31 Codex 재점검 시 실제 실행 중인 bot PID는 `50004`였고, stale `bucky_bot.pid`를 `50004`로 정리함.
3. **현재 위험**
   - 독립 Claude Code/Codex 앱 세션에서 컨텍스트 압축 금지와 새 세션 전환이 자동 강제되는지 불확실함.
   - `scripts/context_warning.py`와 `scripts/codex_session_handoff.py`는 존재하지만, 앱 설정 hook 연결 여부는 별도 확인 필요.
   - `scripts/bucky_bot_supervisor.py` restart path의 `_restart_count` 스코프 버그는 2026-05-31 Codex가 수정함.
4. **금지**
   - 추가 캐시 정리, Docker/WSL/Claude VM/Android 정리 금지.
   - `.env` 비밀값 출력 금지.
   - commit/push 금지, 사용자 명시 승인 전 보류.

## Runtime Recheck Note

- 최신 재점검 노트: `ObsidianVault/00_System/BUCKY_RUNTIME_RECHECK_2026-05-31.md`
- canonical runbook: `ObsidianVault/00_System/BUCKY_OS_RUNBOOK.md`
- 빠른 gate: `python -X utf8 scripts/bucky_os_gate.py --fast --fail-on-error`
- 전체 preflight: `python -X utf8 scripts/preflight_check.py`
- 전체 gate는 기본 report 파일 쓰기에서 Google Drive 잠금/권한 마찰 가능성이 있으므로, 실패 시 오류 메시지를 그대로 보고한다.

## Completed This Pass (2026-05-30)

1. **Gate 1 registry repair** — bucky_tasks.db에 165개 누락 태스크 등록 (총 166개, done:151/failed:15)
2. **JH-SHARED → 99_ARCHIVE** — archive-only / not current operating authority. 00_SYSTEM, 01_AGENT_ROOM, 02_HANDOFF, 03_LOGS, 04_DAILY_REPORTS, 05_TASK_LOCKS, 06_TASK_LOGS, scripts 8개 폴더 JH-SHARED/99_ARCHIVE/로 이동 (날짜: 2026-05-30)
3. **Codex AGENTS.md** — 루트 AGENTS.md 완전성 확인 (역할/규칙/검수우선순위/AI-Slop/보고형식/경로 전부 포함)
4. **JH-MultiAgent 설치** — D:\ai프로젝트\JH-MultiAgent\ 설치, ObsidianVault 귀속 등록
5. **review_checklist_runner.py IMPL-RA-01~06** — P2 버그 수정 완료, Codex WARNING 2건 비블로킹
6. **스나이퍼 구매대행 플랫폼** — ObsidianVault/03_Projects/tools/에 프로젝트 등록

## Current Operating Rule

When a new repo or folder is used:

1. Treat it as having no project-specific instruction packet unless one exists in that project.
2. Do not import another repo's instructions automatically.
3. Ask Bucky or run `scripts/context_pack_selector.py "<요청문>"` to identify the right packet.
4. Use only the packet Bucky provides or confirms for that project scope.
5. For large migration, global instruction changes, or new project packet rollout, run `python -X utf8 scripts/bucky_os_gate.py --fail-on-error`.

## AgentBus Gate Status

| 게이트 | 상태 |
|--------|------|
| Gate 1 registry repair | ✅ 완료 2026-05-30 (165개 수리) |
| Gate 2 cleanup 564 | ✅ 완료 2026-05-28 |
| Gate 3 external blockers 9 | ✅ 완료 2026-05-28 |
| Gate 4 Sniper v0.2 | ✅ 완료 2026-05-29 |
| Gate 5 Discord Voice E2E | ⚠️ 사용자 직접 테스트 필요 |
| Gate 6 Hermes cleanup | ✅ 완료 2026-05-28 |
| Gate 7 T013/T020 | ✅ 완료 2026-05-28 |

## Next Start

1. Read `ObsidianVault/00_System/BUCKY_RUNTIME_RECHECK_2026-05-31.md`.
2. Read `ObsidianVault/10_AgentBus/handoffs/20260531_162046_c_drive_cleanup_incident_notice.md`.
3. Read `ObsidianVault/00_System/BUCKY_OS_RUNBOOK.md`.
4. Run `python -X utf8 scripts/bucky_os_gate.py --fast --fail-on-error`.
5. Run `python -X utf8 scripts/preflight_check.py` when instruction authority or sync confidence matters.
6. For a new repo/folder or unclear task, run `python -X utf8 scripts/context_pack_selector.py --packet --project "<repo-or-folder>" "<요청문>"` before broad exploration.
7. If context grows heavy, do not rely on app compression. Write an AgentBus/session handoff and start a new session.

## Known Boundaries

- No commit/push unless the user explicitly asks.
- Agent sessions must not continue by silent compression when handoff is required.
- Results and decisions should be saved to AgentBus/Vault files and referenced by path, not pasted as long context.
- JH-SHARED 폴더는 이제 99_ARCHIVE로 이동됨 — 레거시 참조 전용.
- JH-MultiAgent는 D:\ai프로젝트\JH-MultiAgent\ — codex login + gemini 인증 필요.
- Daily report generator는 ObsidianVault 경로 기준 (BUCKY_LEGACY_DAILY_MIRROR=0 기본).
