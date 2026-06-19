---
type: operating-charter
status: draft
created: 2026-06-19
owner: user
links:
  - "[[user-evolution-model]]"
  - "[[bucky-user-understanding-agent]]"
  - "[[../06_Context_Packs/oabs-llm-wiki-upgrade-pack|OABS LLM Wiki Upgrade Pack]]"
---

# OABS Second Brain Charter

OABS is the user's ObsidianVault-based LLM Wiki and Second Brain operating system.

Its advantage is not that it dispatches agents faster than every other system. Its advantage is that it preserves, connects, and retrieves the user's real context better than a stateless model can.

## Core Standard

Do not grow the instruction stack. Grow the knowledge graph.

Bucky should use ObsidianVault, LLM Wiki notes, Graphify outputs, Context Packs, Daily Plus, and exact source references as a durable brain. The system should help agents understand why the user asks something, not merely route who should execute it.

## Operating Principles

1. The vault is the memory layer; prompts are only the current access layer.
2. The graph is a navigation tool, not a reason to read everything.
3. Context Packs should compress linked knowledge into task-sized packets.
4. User corrections, preferences, and project history become retrievable knowledge.
5. GitHub repositories are not failure records. They are latent-project assets from different user growth stages.
6. Every agent answer that depends on stored knowledge should be traceable to source notes or graph-linked references.
7. Bucky must optimize for user-context understanding before agent dispatch speed.

## Non-Goals

- Do not replace `bucky.md` with a larger instruction file.
- Do not make every task Bucky-first.
- Do not scan the full vault when targeted search, Graphify, or a Context Pack is enough.
- Do not treat old repos, partial prototypes, or abandoned branches as waste.
- Do not turn Charlie into another orchestrator; Charlie remains the audit layer.

## Durable Knowledge Loop

```text
User work and reflection
  -> Daily Plus / GPT capture / project notes
  -> ObsidianVault LLM Wiki curation
  -> Graphify relationship map
  -> Context Pack retrieval
  -> Bucky user-understanding packet
  -> Claude/Codex execution or review
  -> verified result and user correction
  -> vault update
```

## Success Criteria

- A new model can understand the user's operating context by reading compact vault references.
- Bucky can explain which notes or graph paths shaped a recommendation.
- Repos and past projects are classified by user-growth stage and latent value, not by whether they are currently shipped.
- The system uses fewer repeated instructions while increasing practical user understanding.
- Execution remains scoped, evidence-backed, and reversible.
