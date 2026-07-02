---
type: registry
title: Charlie Error Registry
status: active
created: 2026-07-03
---

# Charlie Error Registry

Repeat-error tracking. An entry goes here when the **same class of problem** has been found
more than once, so future audits (and future agents) don't re-diagnose it from scratch.
Charlie only reads this file to report freshness; humans/agents add entries after a finding is
confirmed and (if fixed) resolved.

## Format

```
### <short id> — <one-line title>
- first_seen: YYYY-MM-DD
- last_seen: YYYY-MM-DD
- severity: P1 | P2 | P3
- area: <area tag, see docs/charlie-system-audit.html areaLabel()>
- occurrences: N
- status: open | fixed | accepted-risk
- description: what the recurring problem is
- fix_applied: what was done, or "n/a" if accepted-risk
```

## Entries

### auto-git-push-hook — Uncontrolled git push from a file-watch hook
- first_seen: 2026-07-02
- last_seen: 2026-07-02
- severity: P1
- area: discord-runtime
- occurrences: 1 (confirmed via git reflog showing prior auto-push activity)
- status: fixed
- description: `scripts/sync_system_enhance.py` ran `git add`/`commit`/`stash`/`pull --rebase`/
  `push` automatically from a `PostToolUse` hook on every Write/Edit, with no user approval step —
  a direct violation of the commit/push-approval policy in `CLAUDE.md`.
- fix_applied: Removed `run_git()`/`git_push()` and the `PostToolUse` hook registration entirely
  (see commits `803cf3e`, and the runtime-folder mirror `56899ac`).

### stale-discord-channel-ids — .env channel IDs pointing at deleted/renamed channels
- first_seen: 2026-07-03
- last_seen: 2026-07-03
- severity: P2
- area: discord-runtime
- occurrences: 1 audit pass, 4 channel IDs affected
- status: fixed
- description: Direct Discord REST checks against all configured channel IDs found one ID
  pointing at the wrong (recreated) channel and three IDs pointing at channels that no longer
  exist at all (404 Unknown Channel).
- fix_applied: Corrected the mismatched ID (`jh-chsh-mining`); removed the three dead IDs from
  `.env` rather than guessing replacements, since channel deletion may have been intentional.
