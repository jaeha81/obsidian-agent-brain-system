# Docker 3-PC Workflow

Purpose: keep Bucky support scripts predictable across home PC, office PC, and laptop while leaving Obsidian, Claude Code, and Codex login sessions on the host.

## Recommended Split

- Host PC: Obsidian desktop, Claude Code CLI, Codex CLI, login/session files.
- Docker: Python runtime, dependency versions, read-only startup checks, long-running watcher services.
- Google Drive/Git: shared repo, vault, AgentBus files, handoff/status files.

## Daily Start

```powershell
docker compose run --rm preflight
```

`preflight` checks:

- `.env` exists.
- repo branch and dirty state.
- upstream ahead/behind state when Git is available.
- `VAULT_PATH`, `JH_SHARED_PATH`, `JH_AGENT_ROOM_PATH`.
- `CLAUDE.md` sync state.
- `CLAUDE_COMMAND` and `CODEX_COMMAND` availability.

## Host CLI Profile

`agent-dispatcher.py` and `codex_review_runner.py` call Claude/Codex CLIs. Those CLIs usually depend on host login/session state, so do not move them into Docker blindly.

Use this profile only after the selected PC has CLI binaries and auth paths available inside the container:

```powershell
docker compose --profile host-cli up -d
```

If CLI auth is not mounted, keep these two scripts running on host through Obsidian `bucky-agent` instead.

## Runtime Ownership

Pick one owner per PC:

- Obsidian-owned: `bucky-agent` starts `raw_import_watcher.py`, `codex_review_runner.py`, and `agent_dispatcher.py`. Use Docker only for `preflight`.
- Docker-owned: stop the host copies first, then start Docker services.

Docker-owned RAW watcher:

```powershell
docker compose up -d raw-import-watcher
```

Do not run the same watcher on host and Docker at the same time.

## Bucky PC Bootstrap And Recovery

Home PC, office PC, and laptop may differ. Docker might be missing, Docker Desktop might be installed but stopped, WSL2 might be broken, or `docker compose` might not be available.

Bucky should treat Docker as an optional accelerator, not a hard dependency. Before starting a Docker-owned service, Bucky should check:

- `docker --version`
- `docker compose version`
- Docker Desktop or Docker engine running state
- repo sync state with `preflight`
- `.env`, `VAULT_PATH`, `JH_SHARED_PATH`, `JH_AGENT_ROOM_PATH`
- Claude/Codex CLI availability on the host

If Docker is missing or broken:

- Keep runtime ownership as Obsidian-owned.
- Keep `raw_import_watcher.py`, `codex_review_runner.py`, and `agent_dispatcher.py` on the host through `bucky-agent`.
- Record the Docker issue in Bucky status or the daily handoff.
- Create a Claude Code setup task only when the user wants Docker repaired on that PC.

Bucky is allowed to request local setup fixes through AgentBus/Claude Code for:

- Docker Desktop install or repair guidance.
- WSL2/virtualization check instructions.
- `.env` and path correction.
- `CLAUDE.md` sync repair.
- Task Scheduler repair for `ClaudeInstructionSync`.
- Python dependency install or virtual environment repair.
- Switching runtime ownership between Obsidian-owned and Docker-owned.

Bucky must not silently install Docker, change auth files, stop host processes, or switch ownership without an explicit user approval. Codex should review any resulting setup change when it affects shared workflow files.

## Status Commands

```powershell
docker compose ps
docker compose logs -f raw-import-watcher
docker compose run --rm preflight
```

## Stop

```powershell
docker compose down
```

## Rule

Run `preflight` before serious work on any PC. If it reports git sync, `CLAUDE.md`, or path warnings, fix those first before talking to Bucky, Codex, or Claude Code.
