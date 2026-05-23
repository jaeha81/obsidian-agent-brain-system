# Harness Framework Integration

이 시스템은 `jaeha81/jh-harnessFramework-dashboard`의 룰 기반 하네스 구조를 Obsidian Agent Brain에 통합한다.

## What Changed

- Obsidian Vault에 `05_Frameworks/Harness/` 지식베이스를 추가했다.
- `scripts/harness_router.py`가 사용자 개발 요구를 분석한다.
- `scripts/agent_dispatcher.py`가 구현 요청을 Claude Code로 넘기기 전에 Harness Development Brief를 붙인다.
- 구현 결과가 나오면 Codex 검수 요청 파일을 자동 생성한다.

## Supported Harnesses

| Harness | Primary Use |
|---|---|
| Superpowers | TDD, subagent implementation, execution quality |
| GSD | Large phased work, persistent planning state |
| gstack | Product direction, architecture, UX/security governance |

## Runtime

```env
HARNESS_ROUTER_ENABLED=1
CODEX_REVIEW_ENABLED=1
```

## AgentBus Flow

1. User request enters `ObsidianVault/10_AgentBus/inbox/`.
2. Dispatcher detects `implementation_request`, `harness_development_request`, or implementation-like Discord intake.
3. Harness Router scores the request.
4. Claude Code receives:
   - JH role rules
   - Harness routing result
   - selected workflow
   - extracted development tasks
   - Codex review checklist
5. Dispatcher writes the implementation result to `outbox/Hermes/`.
6. Dispatcher writes a Codex review request to `outbox/Hermes/`.
7. `scripts/codex_review_runner.py` picks up the review request and writes a review to `outbox/Codex/`.

## Notes

- The router is deterministic and does not require API keys.
- The Vault remains the human-readable source of framework knowledge.
- If Claude Code does not have a framework plugin installed, it should apply the methodology first and ask/report before network installation.
