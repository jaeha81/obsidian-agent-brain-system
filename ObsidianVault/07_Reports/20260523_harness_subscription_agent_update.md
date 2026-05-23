# 2026-05-23 Hermes-style Subscription Agent + Harness Router Update

## Summary

현재 Obsidian Agent Brain System은 Hermes 이름과 AgentBus 구조를 유지하면서, 실제 모델 실행은 Claude Code CLI 구독 경로를 사용하도록 전환되었다. 또한 JH Harness Dashboard의 Superpowers, GSD, gstack 기준을 Obsidian 지식베이스에 저장하고, 개발 요청을 자동 분석해 Claude Code와 Codex에 나눠 지시하는 구조를 도입했다.

## Completed

- Claude Code CLI 구독 기반 실행 레인 구성
- Codex CLI 독립 검수 레인 구성
- JH-SHARED/JH-Agent-Room 역할 규칙 반영
- Harness Framework 지식베이스 생성
- Harness Router 생성
- Agent Dispatcher에 하네스 기반 개발 지시 패키지 연결
- Codex Review Runner에 하네스 검수 컨텍스트 연결
- Claude 전달 고지문 업데이트

## Harness Flow

1. 사용자가 개발 요청을 보낸다.
2. Agent Dispatcher가 구현 요청을 감지한다.
3. Harness Router가 요청을 분석한다.
4. Superpowers, GSD, gstack 또는 조합을 선택한다.
5. Claude Code는 선택된 하네스 기준으로 구현한다.
6. 구현 결과는 Hermes outbox에 기록된다.
7. Codex 검수 요청이 자동 생성된다.
8. Codex는 선택된 하네스 기준으로 독립 검수한다.

## Key Files

- `scripts/hermes_client.py`
- `scripts/agent_dispatcher.py`
- `scripts/codex_review_runner.py`
- `scripts/harness_router.py`
- `ObsidianVault/05_Frameworks/Harness/README.md`
- `ObsidianVault/05_Frameworks/Harness/Superpowers.md`
- `ObsidianVault/05_Frameworks/Harness/GSD.md`
- `ObsidianVault/05_Frameworks/Harness/gstack.md`
- `ObsidianVault/05_Frameworks/Harness/framework_router.md`
- `docs/claude_handoff_notice.md`
- `docs/harness_framework_integration.md`
- `docs/hermes_agent_guide.md`

## Verification

- `python -m py_compile scripts\harness_router.py scripts\agent_dispatcher.py scripts\codex_review_runner.py scripts\hermes_client.py scripts\codex_request.py scripts\discord_bot.py scripts\session_end.py`
- Harness smoke test: authentication/permission/phase/test request routed to `gstack+GSD+Superpowers`
- `python scripts\codex_review_runner.py --once --dry-run`
- `git diff --check`

## Current Runtime

- `AGENT_RUNTIME=claude_cli`
- `CLAUDE_USE_API_KEY=0`
- `CODEX_REVIEW_ENABLED=1`
- `HARNESS_ROUTER_ENABLED=1`
- `AGENTBUS_WORKER_NAME=Hermes`

## Next Entry Point

Start the system with:

```bat
start_dispatcher.bat
```

Then place a pending `implementation_request` or `harness_development_request` in `ObsidianVault/10_AgentBus/inbox/`.

## Notes

- GitHub token was not required for reading `jaeha81/jh-harnessFramework-dashboard`.
- GitHub token or login will be needed only for pushing to GitHub or reading private repositories.
- Existing unrelated worktree changes were not reverted.

## Bucky Obsidian Plugin Update

- Hermes-style subscription agent display name changed to `버키`.
- `bucky-agent` Obsidian community plugin installed in both active repo-root vault config and `ObsidianVault` config.
- Obsidian desktop launch now auto-starts:
  - `scripts/raw_import_watcher.py`
  - `scripts/codex_review_runner.py`
  - `scripts/agent_dispatcher.py`
- Plugin detects local PC, hostname, username, root path, and vault path.
- Status note writes to `ObsidianVault/00_System/BUCKY_STATUS.md`.
- Runtime verification on 2026-05-23: all three Bucky scripts were running, one process each, with duplicate prevention confirmed after Obsidian restart.
