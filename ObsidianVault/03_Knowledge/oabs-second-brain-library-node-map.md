---
type: knowledge-node
status: active
created: 2026-06-20
owner: user
domain: agent_os
asset_type: knowledge
growth_stage: second_brain
source: graphify
confidence: verified
keywords:
  - second-brain
  - llm-wiki
  - graphify
  - library-taxonomy
  - user-understanding
  - latent-project
links:
  - "[[../00_System/oabs-second-brain-charter|OABS Second Brain Charter]]"
  - "[[../00_System/oabs-library-taxonomy-standard|OABS Library Taxonomy Standard]]"
  - "[[../00_System/bucky-user-understanding-agent|Bucky User Understanding Agent]]"
  - "[[oabs-latent-project-asset-sample]]"
  - "[[../06_Context_Packs/Graphify/OABS_second_brain_graphify_pack|OABS Second Brain Graphify Pack]]"
evidence:
  - external_data/graphify_selected/OABS_second_brain_source/graphify-out/GRAPH_REPORT.md
  - external_data/graphify_selected/OABS_second_brain_source/graphify-out/graph.json
  - ObsidianVault/06_Context_Packs/Graphify/OABS_second_brain_graphify_pack.md
---

# OABS Second Brain Library Node Map

This node connects the human Obsidian graph and the Graphify-selected source graph for the OABS Second Brain upgrade.

## Library Cluster

- [[../00_System/oabs-second-brain-charter|OABS Second Brain Charter]] defines the top-level mission.
- [[../00_System/oabs-library-taxonomy-standard|OABS Library Taxonomy Standard]] defines shelves, node types, keywords, and catalog fields.
- [[../00_System/user-evolution-model|User Evolution Model]] classifies past projects as growth-stage assets.
- [[../00_System/bucky-user-understanding-agent|Bucky User Understanding Agent]] defines Bucky's user-context role.
- [[../06_Context_Packs/oabs-llm-wiki-upgrade-pack|OABS LLM Wiki Upgrade Pack]] is the AI retrieval pack.
- [[oabs-latent-project-asset-sample]] is the first applied latent-project asset sample.

## Graphify Evidence

Selected-source Graphify build:

```text
source: external_data/graphify_selected/OABS_second_brain_source
output: external_data/graphify_selected/OABS_second_brain_source/graphify-out
nodes: 189
edges: 319
hygiene: PASS
```

## Use

When Bucky receives an OABS Second Brain, LLM Wiki, library taxonomy, or latent-project request, it should use this map to move from the user's words to the correct charter, taxonomy, sample, Graphify pack, and implementation evidence.

This node is not a mandatory always-read hub. It is a graph bridge for this specific knowledge cluster.
