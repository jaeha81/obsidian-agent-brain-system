---
type: gap-analysis
updated: 2026-05-12
engine: jh-local-knowledge-graph
tags: [local-graph, gap-analysis, jh]
  - #status/archive
---

# Local Graph Gap Analysis - wiki

Files: `22` / Nodes: `183` / Edges: `1517`

## Diagnostics

- Status: `balanced`
- Density: `0.0911`
- Top weighted share: `0.0346`
- Advice: The discourse has a usable balance between focus and diversity. Continue by developing bridge candidates.

## Discourse Entrance Points

- `index` (link) - entrance score `5.958`, weighted degree `143`
- `log` (link) - entrance score `5.438`, weighted degree `87`
- `memory` (term) - entrance score `5.083`, weighted degree `61`
- `ingest` (term) - entrance score `4.571`, weighted degree `64`
- `brain` (term) - entrance score `4.5`, weighted degree `36`
- `entity-claude-ai-desktop-setup` (link) - entrance score `4.375`, weighted degree `70`
- `entity-jh-brain-system` (link) - entrance score `4.348`, weighted degree `100`
- `entity-mneme` (link) - entrance score `4`, weighted degree `100`
- `questions` (term) - entrance score `4`, weighted degree `64`
- `overview` (link) - entrance score `3.92`, weighted degree `98`

## Top Nodes

- `index` (link) - weighted degree 143
- `entity-mneme` (link) - weighted degree 100
- `entity-jh-brain-system` (link) - weighted degree 100
- `overview` (link) - weighted degree 98
- `log` (link) - weighted degree 87
- `concept-agent-philosophy` (page) - weighted degree 87
- `entity-agent-ecosystem` (link) - weighted degree 85
- `concept-llm-wiki` (link) - weighted degree 84
- `concept-dev-workflow` (link) - weighted degree 71
- `entity-claude-ai-desktop-setup` (link) - weighted degree 70
- `ingest` (term) - weighted degree 64
- `questions` (term) - weighted degree 64

## Isolated Or Weak Nodes

- `../INDEX` (link) - degree 1
- `05_Insights/jh-windows-launcher-dev-pattern` (link) - degree 1
- `../output/todo/2026-05-12-infranodus-adoption-todo` (link) - degree 1
- `pass` (term) - degree 1
- `../output/claude-instructions/2026-05-12-infranodus-briefing` (link) - degree 1
- `../output/research-questions/2026-05-12-023540-wiki-research-questions` (link) - degree 1
- `lint-quick` (page) - degree 1
- `../output/codex-review-targets/2026-05-12-infranodus-review-targets` (link) - degree 1

## Bridge Candidates

- [[source-infranodus-llm-wiki-video]] <-> [[source-llm-wiki-pattern]] / score `0.143` / shared: analysis, questions, documents
  - Shortest path: source-infranodus-llm-wiki-video -> documents -> source-llm-wiki-pattern
- [[pattern-graph-gap-driven-research]] <-> [[source-infranodus-llm-wiki-video]] / score `0.143` / shared: research, questions, clusters
  - Shortest path: pattern-graph-gap-driven-research -> concept-infranodus-graph-knowledge-base -> source-infranodus-llm-wiki-video
- [[concept-dev-workflow]] <-> [[entity-agent-ecosystem]] / score `0.143` / shared: concept-agent-philosophy, entity-jh-brain-system, entity-mneme
  - Shortest path: concept-dev-workflow -> entity-agent-ecosystem
- [[log]] <-> [[source-jh-windows-launcher-insight]] / score `0.091` / shared: insights, jh-windows-launcher-dev-pattern
  - Shortest path: log -> jh-windows-launcher-dev-pattern -> source-jh-windows-launcher-insight
- [[jh-infranodus-upgrade-analysis]] <-> [[pattern-graph-gap-driven-research]] / score `0.091` / shared: review, questions
  - Shortest path: jh-infranodus-upgrade-analysis -> log -> pattern-graph-gap-driven-research
- [[source-infranodus-llm-wiki-video]] <-> [[source-infranodus-visual-ai-text-analysis-video]] / score `0.091` / shared: gaps, concepts
  - Shortest path: source-infranodus-llm-wiki-video -> concept-infranodus-graph-knowledge-base -> source-infranodus-visual-ai-text-analysis-video
- [[entity-claude-ai-desktop-setup]] <-> [[source-llm-wiki-pattern]] / score `0.091` / shared: documents, concept-llm-wiki
  - Shortest path: entity-claude-ai-desktop-setup -> source-llm-wiki-pattern
- [[concept-obsidian-plugins]] <-> [[source-llm-wiki-pattern]] / score `0.091` / shared: overview, concept-llm-wiki
  - Shortest path: concept-obsidian-plugins -> concept-llm-wiki -> source-llm-wiki-pattern
- [[jh-infranodus-upgrade-analysis]] <-> [[source-llm-wiki-pattern]] / score `0.091` / shared: analysis, questions
  - Shortest path: jh-infranodus-upgrade-analysis -> concept-llm-wiki -> source-llm-wiki-pattern
- [[concept-obsidian-plugins]] <-> [[index]] / score `0.091` / shared: overview, index
  - Shortest path: concept-obsidian-plugins -> index

## Generated Research Questions

- How should [[source-infranodus-llm-wiki-video]] and [[source-llm-wiki-pattern]] be connected through analysis, questions, documents so the JH knowledge base becomes more coherent?
- How should [[pattern-graph-gap-driven-research]] and [[source-infranodus-llm-wiki-video]] be connected through research, questions, clusters so the JH knowledge base becomes more coherent?
- How should [[concept-dev-workflow]] and [[entity-agent-ecosystem]] be connected through concept-agent-philosophy, entity-jh-brain-system, entity-mneme so the JH knowledge base becomes more coherent?
- How should [[log]] and [[source-jh-windows-launcher-insight]] be connected through insights, jh-windows-launcher-dev-pattern so the JH knowledge base becomes more coherent?
- How should [[jh-infranodus-upgrade-analysis]] and [[pattern-graph-gap-driven-research]] be connected through review, questions so the JH knowledge base becomes more coherent?
- How should [[source-infranodus-llm-wiki-video]] and [[source-infranodus-visual-ai-text-analysis-video]] be connected through gaps, concepts so the JH knowledge base becomes more coherent?
- How should [[entity-claude-ai-desktop-setup]] and [[source-llm-wiki-pattern]] be connected through documents, concept-llm-wiki so the JH knowledge base becomes more coherent?
- How should [[concept-obsidian-plugins]] and [[source-llm-wiki-pattern]] be connected through overview, concept-llm-wiki so the JH knowledge base becomes more coherent?

## Artifacts

- Graph HTML: `C:\Users\user1\Documents\Obsidian Vault\infranodus\graph-snapshots\2026-05-12-024307-wiki-local-graph.html`
- Ontology JSON: `C:\Users\user1\Documents\Obsidian Vault\infranodus\ontology\2026-05-12-024307-wiki-local-graph.json`