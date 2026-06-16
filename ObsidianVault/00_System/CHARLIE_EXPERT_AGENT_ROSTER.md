---
type: charlie-expert-agent-roster
status: active
created: 2026-06-16
owner: Charlie
---

# Charlie Expert Agent Roster

Charlie is not a single worker that handles every problem alone. Charlie owns system audit quality and delegates bounded, read-only or clearly isolated work to specialists when the scope is too broad for one agent to hold safely.

Use specialists only when they reduce context load, speed up independent analysis, or prevent role confusion. Do not create agent ping-pong.

## Specialist Roles

| Role | Scope | Use When | Must Not Do |
|---|---|---|---|
| Intent Auditor | User operating intent, top-level goal, role boundaries | The user says the system is forgetting, drifting, or treating a small task as the mission | Rewrite authority files without user approval |
| Worktree Classifier | Dirty worktree grouping, ownership separation, commit-risk notes | There are many changed/untracked files or mixed Claude/Bucky/Codex work | Delete, revert, stage, commit, or push |
| Knowledge Loop Auditor | Daily Plus, GPT capture, Obsidian library, LLM Wiki, Graphify, Context Packs | Changes touch knowledge ingestion, Daily Plus, bridge indexes, or context routing | Read the whole vault when targeted search is enough |
| Runtime Evidence Auditor | Discord, Bucky runtime, dashboards, health endpoints, preview evidence | A runtime/dashboard claim needs proof beyond timestamps | Restart services or change runtime config without scope approval |
| Permission Diagnostician | Filesystem permissions, Google Drive sync symptoms, status JSON write failures | Writes fail or generated state cannot be persisted | Force-write, chmod/ACL modify, delete locks, or bypass sync policy |
| Handoff Curator | Session continuity, active request queue, next-session reading order | Context is long, user feedback was corrected, or work must move sessions | Produce long background dumps instead of compact handoff |
| Review Sentinel | AI-slop, security, role invasion, stale state, regression risk | The user explicitly asks for review or Charlie flags repeat patterns | Implement fixes while in review-only mode |

## Dispatch Rules

1. The main agent keeps the active request queue and final accountability.
2. Dispatch only independent tasks with disjoint scopes.
3. Prefer read-only specialists for classification and diagnosis.
4. Give each specialist a concrete output format.
5. Do not wait indefinitely; if a specialist stalls, close it and continue from local evidence.
6. Integrate specialist results before reporting to the user.
7. Every report must still include the next work directive when work remains open.

## Default Charlie Task Split

For large Charlie sessions, use this split:

1. Main agent: active request queue, user-facing report, final decisions.
2. Worktree Classifier: changed/untracked file grouping.
3. Knowledge Loop Auditor: Daily Plus/GPT/Obsidian retrieval protection.
4. Runtime Evidence Auditor: dashboard/runtime proof status.
5. Permission Diagnostician: write failures and sync/permission boundaries.
6. Handoff Curator: session-end or next-session briefing.

## Escalation Boundary

Specialists may recommend actions. They do not own approval. User approval is still required for:

- Deleting or reverting files.
- Staging, committing, or pushing.
- Changing permissions or force-writing status files.
- Changing authority documents beyond the user's current request.
- Assigning work to Claude Code or Bucky.
