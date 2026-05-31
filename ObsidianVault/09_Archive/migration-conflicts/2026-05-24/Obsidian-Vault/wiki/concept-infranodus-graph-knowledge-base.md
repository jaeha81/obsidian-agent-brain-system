---
type: concept
updated: 2026-05-12
sources: [source-infranodus-llm-wiki-video]
tags: [infranodus, knowledge-graph, obsidian, llm-wiki, living-memory]
  - #status/archive
---

# InfraNodus Graph Knowledge Base

InfraNodus adds a graph intelligence layer on top of an LLM Wiki. The wiki stores concepts and source summaries, while InfraNodus shows how those concepts relate, where the strong clusters are, and where the knowledge base has gaps.

## Problem

Standard RAG retrieves chunks and answers the current question, but it does not evolve with the user. A plain LLM Wiki improves this by creating persistent concept pages, but the LLM can still produce generic answers because it lacks a structural view of the whole knowledge base.

## Graph Layer

InfraNodus represents notes, concepts, and documents as a network:

- Nodes are concepts, entities, questions, sources, or claims.
- Edges represent co-occurrence, semantic relation, or explicit wiki links.
- Clusters reveal topical groups.
- Gaps reveal topics that should be connected but are currently weakly related.
- Centrality reveals dominant ideas that may be overrepresented.
- Isolated nodes reveal knowledge that is not integrated.

## Visual Performance

The graph view is not just decorative. It gives a fast visual map of the knowledge base:

- Main clusters show the current research direction.
- Small clusters show underdeveloped but potentially valuable areas.
- Disconnected nodes show material that needs integration.
- Gap analysis suggests original questions that connect separate clusters.

This is stronger than a file tree or basic Obsidian graph because it focuses on topical structure and analytical gaps, not only backlinks.

## Operating Pattern

```text
1. Ingest raw material.
2. Generate wiki pages.
3. Visualize concepts, sources, or folders as an InfraNodus graph.
4. Identify central clusters, weak clusters, and gaps.
5. Generate AI questions from gaps.
6. Feed those questions back into Claude/Codex.
7. Save resulting ontology graphs and research tasks.
```

## JH Application

The JH ecosystem should use InfraNodus for four jobs:

- System mapping: visualize relationships among JH Brain, Harness, Agent Room, Claude, Codex, Obsidian, GitHub, and Google Drive.
- Review targeting: find isolated or weakly connected areas that Codex should inspect.
- Error pattern analysis: connect recurring Claude mistakes with affected files, agents, and protocols.
- Strategy generation: identify gaps between business goals, technical implementation, and operating protocols.

## Required Folders

```text
raw/
wiki/
infranodus/
output/
```

The existing `raw/` and `wiki/` folders are already present in the JH Obsidian Vault. The missing upgrade is the graph memory layer:

```text
infranodus/
  ontology/
  gap-analysis/
  graph-snapshots/
  mcp-logs/

output/
  research-questions/
  claude-instructions/
  codex-review-targets/
  todo/
```

## Guardrails

- Do not upload private operational data to external services without a data classification decision.
- Use redacted summaries for sensitive JH data first.
- Store API keys outside GitHub, Obsidian notes, and shared plain-text folders.
- Keep `raw/` immutable where possible; derived structure belongs in `wiki/`, `infranodus/`, and `output/`.

## Related Pages

- [[concept-llm-wiki]]
- [[source-infranodus-llm-wiki-video]]
- [[jh-infranodus-upgrade-analysis]]
