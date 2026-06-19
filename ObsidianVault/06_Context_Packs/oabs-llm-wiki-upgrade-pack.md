---
type: context-pack
status: draft
created: 2026-06-19
owner: user
scope: OABS Second Brain / LLM Wiki upgrade
links:
  - "[[../00_System/oabs-second-brain-charter|OABS Second Brain Charter]]"
  - "[[../00_System/user-evolution-model|User Evolution Model]]"
  - "[[../00_System/bucky-user-understanding-agent|Bucky User Understanding Agent]]"
---

# OABS LLM Wiki Upgrade Pack

Use this pack when work changes OABS knowledge structure, Bucky's user-understanding role, LLM Wiki retrieval, Graphify use, or the interpretation of older GitHub repos as latent-project assets.

## Core Thesis

OABS should become an ObsidianVault-based LLM Wiki and Second Brain operating system.

The durable advantage is user-context understanding:

- The vault preserves knowledge across model changes.
- Graphify exposes relationships between notes, repos, and concepts.
- Context Packs provide task-sized retrieval.
- Bucky uses those sources to understand the user before dispatching work.
- Human verification remains possible because answers point back to source notes.

## Read First

1. `ObsidianVault/00_System/oabs-second-brain-charter.md`
2. `ObsidianVault/00_System/bucky-user-understanding-agent.md`
3. `ObsidianVault/00_System/user-evolution-model.md`
4. `ObsidianVault/00_System/USER_OPERATING_INTENT.md`
5. `prompts/graphify_integration_prompt.md`
6. `ObsidianVault/03_Knowledge/oabs-latent-project-asset-sample.md`

## Operating Constraints

- Do not grow global instructions unless the user explicitly approves.
- Do not overwrite `ObsidianVault/03_Projects/agents/bucky.md` for this upgrade.
- Link Bucky to the new criteria first, then migrate behavior gradually.
- Use Graphify for specific project or note clusters, not uncontrolled full-vault scans.
- Keep Charlie in audit mode.
- Keep Codex review independent and Claude implementation scoped.

## Bucky Upgrade Direction

Bucky should evolve from "router of tasks" into "user understanding agent plus router."

This means Bucky should ask:

1. What user context matters here?
2. Which vault note, graph cluster, or repo history proves it?
3. Is this a direct execution task, a micro-plan task, or a Bucky-first task?
4. Which agent should act?
5. What exact verification will prove completion?

## Latent-Project Rule

All GitHub repositories should be treated as potential latent-project assets.

Do not label a repo as a failure just because it is dormant, incomplete, or superseded. First identify the preserved asset: product idea, workflow, technical module, data, design, lesson, or future seed.

## Evidence Standard

Outputs should cite one or more of:

- exact vault note path
- Context Pack path
- Graphify report or graph cluster
- source file path
- command output or runtime evidence
- user-provided instruction in the current request

If evidence is incomplete, state the gap instead of inventing continuity.

## Done When

- The new criteria exist as separate vault documents.
- Bucky references the new criteria without replacing `bucky.md`.
- Future OABS work can load this pack instead of expanding global instructions.
- The model preserves the distinction between execution speed and user-context understanding.

