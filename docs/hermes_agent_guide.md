# Bucky Subscription Agent Guide
> Created: 2026-05-23

This Obsidian Agent Brain System uses Bucky as the Obsidian main orchestrator while keeping model execution on subscription CLIs.

## Default Runtime

Default mode uses Claude Code CLI for implementation and operation work:

```env
AGENT_RUNTIME=claude_cli
CLAUDE_COMMAND=claude.cmd
CLAUDE_OUTPUT_FORMAT=text
CLAUDE_USE_API_KEY=0
AGENTBUS_WORKER_NAME=Bucky
```

`CLAUDE_USE_API_KEY=0` deliberately removes `ANTHROPIC_API_KEY` and `CLAUDE_API_KEY` from the subprocess environment, so the worker uses the logged-in Claude Code subscription flow instead of API billing.

## Codex Review Lane

Codex runs as an independent subscription review lane:

```env
CODEX_REVIEW_ENABLED=1
CODEX_COMMAND=codex.cmd
CODEX_SANDBOX=read-only
CODEX_REVIEW_INTERVAL=10
CODEX_TIMEOUT=900
```

Review requests are read from:

```text
ObsidianVault/10_AgentBus/outbox/Bucky/
```

Codex writes review results to:

```text
ObsidianVault/10_AgentBus/outbox/Codex/
```

## Harness Framework Router

Development requests are analyzed before they reach Claude Code:

```env
HARNESS_ROUTER_ENABLED=1
```

The router stores and reads human-facing framework knowledge from:

```text
ObsidianVault/05_Frameworks/Harness/
```

Supported harnesses:

- Superpowers: execution quality, TDD, subagent-driven development.
- GSD: large phased work and persistent planning state.
- gstack: product direction, architecture, UX/security governance.

For `implementation_request`, `harness_development_request`, and implementation-like Discord intake, Bucky adds a Harness Development Brief to the Claude Code prompt. Successful implementation results also create a Codex review request.

## Role Governance

The system loads role/governance context from:

```env
JH_SHARED_PATH=G:\내 드라이브\JH-SHARED
JH_AGENT_ROOM_PATH=G:\내 드라이브\JH-Agent-Room
```

Applied rules:

- User decides direction, priority, and final approval.
- Bucky receives requests, classifies work, and routes tasks.
- Claude Code subscription lane handles implementation and operations when Bucky assigns it.
- Codex subscription lane handles independent review when Bucky assigns it and may report directly to the user.
- Codex does not automatically modify Claude output.
- Claude does not finalize implementation reports without Codex review.
- Claude and Codex do not directly edit the same daily Markdown report; append-only JSONL/source logs are preferred.
- Parallel work should use task locks when target paths overlap.

## Knowledge Graph Evolution

Bucky is responsible for keeping the Obsidian knowledge graph useful, not merely populated.

- Before vault organization or system-evolution work, check the Obsidian Graph View and the latest `ObsidianVault/graphify-out/GRAPH_REPORT.md`.
- Use Graphify to find noisy source paths, disconnected clusters, duplicate derived outputs, and missing bridge notes.
- Keep graph noise hidden by default: `.obsidian/`, `01_RAW/`, `09_Archive/`, `10_AgentBus/`, `00_UPGRADE/`, `graphify-out/`, and `Inbox/DiscordCaptures/`.
- After Graphify rebuilds, run `python scripts/graphify_hygiene_check.py ObsidianVault/graphify-out/graph.json`.
- Improve the graph with meaningful bridge/index/routing notes. Do not add fake links only to make the graph visually dense.

## Optional Hermes API Mode

Hermes CLI remains available as an alternative API/provider runtime:

```env
AGENT_RUNTIME=hermes
HERMES_COMMAND=hermes
HERMES_MODE=oneshot
HERMES_PROVIDER=anthropic
HERMES_MODEL=anthropic/claude-sonnet-4.6
```

This mode uses provider/API billing, not the Claude Code subscription quota.

## Start

```bash
start_dispatcher.bat
```

or run components separately:

```bash
python scripts/agent_dispatcher.py
python scripts/codex_review_runner.py
```

## Verification

```bash
python -m py_compile scripts/hermes_client.py scripts/agent_dispatcher.py scripts/codex_review_runner.py scripts/discord_bot.py
python scripts/codex_review_runner.py --once --dry-run
```
