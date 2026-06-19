---
type: user-model
status: draft
created: 2026-06-19
owner: user
links:
  - "[[oabs-second-brain-charter]]"
  - "[[bucky-user-understanding-agent]]"
---

# User Evolution Model

The user's GitHub repositories, vault notes, Daily Plus records, and experiments are a staged record of growth. OABS should treat them as a latent-project portfolio, not as a pass/fail archive.

## Interpretation Rule

Every project can contain at least one reusable asset:

- product intuition
- workflow pattern
- technical component
- market signal
- design direction
- user preference
- failure lesson
- future project seed

Bucky should identify the asset before judging the repo.

## Growth Stages

| Stage | Signal | Bucky Interpretation |
|---|---|---|
| Exploration | many ideas, rough prototypes, changing names | map interests and repeated problem spaces |
| System Building | dashboards, agents, scripts, automation | extract reusable operating patterns |
| Productization | payments, auth, deployment, customer flows | identify market-facing assets and risks |
| Knowledge Consolidation | Obsidian notes, LLM Wiki, Context Packs | preserve reasoning and user-specific context |
| Second Brain Operation | Graphify, Daily Plus, Bucky, Charlie | use linked memory to improve future decisions |

## Latent-Project Asset Model

For each repo or major note cluster, classify:

```yaml
asset_type: product | workflow | data | design | automation | knowledge | lesson
growth_stage: exploration | system_building | productization | consolidation | second_brain
current_status: active | dormant | archived | reference_only
latent_value: high | medium | low | unknown
next_possible_use: concise future use case
evidence:
  - exact file, note, graph cluster, or commit reference
```

This model is for retrieval and sense-making. It is not a demand to rewrite every old repo.

## User Understanding Signals

Bucky should prioritize signals that reveal durable user context:

1. Repeated goals across projects.
2. Frustrations that recur across sessions.
3. Reusable workflows the user keeps rebuilding.
4. Project ideas that return after dormancy.
5. Corrections the user gives to agents.
6. Places where execution speed harmed context quality.
7. Notes that connect multiple repos or life stages.

## Practical Rule

When the user asks about a project, Bucky should answer from this order:

1. What stage of the user's evolution does this belong to?
2. What latent asset does it preserve?
3. What current task is actually being requested?
4. What minimal context is needed to act correctly?
5. What source note, graph path, or file proves the answer?
