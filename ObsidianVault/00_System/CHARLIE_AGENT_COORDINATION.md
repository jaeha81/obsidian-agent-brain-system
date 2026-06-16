---
type: charlie-agent-coordination
status: active
created: 2026-06-15
---

# Charlie Agent Coordination Protocol

This protocol prevents wasteful agent ping-pong and context overuse while Charlie enters the Obsidian Brain System gradually.

## Core Rule

Do not route every decision through Claude Code, Codex, and Bucky in sequence. Assign work once, keep boundaries clear, and report only meaningful state changes to the user.

## Role Split

| Agent | Primary Work | Must Not Do |
|---|---|---|
| Bucky | Work operations orchestration, task routing, practical execution flow | Become the system auditor or single fragile source of all instructions |
| Charlie | Independent audit, drift detection, error registry, instruction packet checks, restore guidance | Auto-fix, route normal work, replace Bucky, consume tokens continuously |
| Codex | Independent review, deterministic checks, explicit implementation when asked | Treat a small task as the whole user mission, silently rely on stale Bucky context |
| Claude Code | Implementation inside approved scope | Modify Charlie files or system authority files without explicit user approval |
| User | Final authority, approval for restore/rollback/authority changes | Carry hidden operational state that agents should have recorded |

Charlie specialist roles live in `ObsidianVault/00_System/CHARLIE_EXPERT_AGENT_ROSTER.md`. Use that roster when the work is too broad for one agent to handle reliably, especially dirty worktree classification, knowledge-loop auditing, runtime evidence, permission diagnosis, and handoff curation.

## Efficient Operation

1. Charlie keeps static registries and deterministic checks.
2. Codex handles Charlie implementation and verification in the current session.
3. Claude Code remains paused unless the user assigns a separate implementation task.
4. Bucky continues normal work orchestration only after Charlie baseline is stable.
5. No agent asks another agent for confirmation unless the task crosses its authority boundary.
6. Agents use Obsidian as a library: LLM Wiki, Graphify, Context Packs, and targeted references before broad file reading.
7. Agents create a session handoff before context bloat causes loss of user feedback or repeated mistakes.
8. Charlie uses specialist agents for independent broad analysis, but the main agent keeps the active request queue and final report.

## Turn Closure Rule

Before Codex or Charlie ends a report in this project, the agent must explicitly close the user's active request queue.

Every non-trivial report must include:

1. What was requested.
2. What was completed.
3. What is still open.
4. The next work directive.
5. What must not be done without user approval.

If the user has corrected the agent twice in the same session for forgetting requested follow-up work, stop the current task, record the recurrence rule, and resume only after the next work directive is stated.

## New Session Guard

When any new Codex or Claude Code session starts in this project:

1. Read root `OPERATING_INTENT.md`.
2. Read `ObsidianVault/00_System/USER_OPERATING_INTENT.md`.
3. Read role-specific local instructions: `AGENTS.md` for Codex, `CLAUDE.md` for Claude Code.
4. If Bucky context conflicts with user operating intent, report the conflict before continuing.
5. If the user asks for Charlie/system audit work, do not route it through Bucky first.

## Vaccine Mode

Charlie enters the system gradually:

1. Observe and record.
2. Report drift.
3. Suggest prevention rules.
4. Ask for user approval before any correction.
5. Only after stability improves, add automation around the proven checks.

## Stop Conditions

Pause and report if:

- More than one agent is rewriting authority files at the same time.
- A task starts without a local instruction packet.
- A dashboard or runtime loop repeats without proof.
- User top-level intent is replaced by a smaller subtask.
- Token use grows because agents are relaying instructions instead of doing assigned work.
- Agents ignore the user's Daily Plus/GPT to Obsidian feedback loop and behave like the knowledge base is disposable context.
- Session-end reasons, next-session reading order, and preserved lessons are not recorded before a context-heavy session ends.
- A report ends without stating the next work directive when unresolved work remains.
