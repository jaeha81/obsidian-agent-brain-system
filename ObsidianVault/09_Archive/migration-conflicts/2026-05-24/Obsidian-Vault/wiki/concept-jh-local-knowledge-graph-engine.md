---
type: concept
updated: 2026-05-12
sources: [concept-infranodus-graph-knowledge-base, decision-adopt-infranodus-graph-layer]
tags: [local-graph, knowledge-graph, gap-analysis, codex]
  - #status/archive
---

# JH Local Knowledge Graph Engine

## Purpose

The JH local knowledge graph engine is a Codex-built local alternative to the most important InfraNodus-style functions needed by the JH system.

It does not replace the InfraNodus cloud product, account system, hosted AI models, or official Obsidian plugin. It provides a local-first baseline that works without API keys:

- Markdown corpus parsing
- Obsidian wikilink extraction
- keyword node extraction
- co-occurrence graph generation
- central node ranking
- isolated node detection
- bridge candidate detection
- biased / dispersed / balanced structure diagnostics
- discourse entrance point ranking
- shortest path explanation for bridge candidates
- research question generation
- interactive HTML graph visualization
- ontology JSON export

## Script

```text
G:\내 드라이브\JH-SHARED\scripts\jh-local-knowledge-graph.ps1
```

Example:

```powershell
powershell -ExecutionPolicy Bypass -File "G:\내 드라이브\JH-SHARED\scripts\jh-local-knowledge-graph.ps1" -Source wiki -Open
```

## Output

The engine writes derived artifacts into the existing graph memory structure:

```text
infranodus/graph-snapshots/
infranodus/gap-analysis/
infranodus/ontology/
output/research-questions/
```

## Current Verified Run

Run: `2026-05-12-022632`

- Source: `wiki/`
- Files: `20`
- Nodes: `160`
- Edges: `1340`
- Gap candidates: `10`

Enhanced run after the second InfraNodus video: `2026-05-12-023540`

- Source: `wiki/`
- Files: `21`
- Nodes: `176`
- Edges: `1433`
- Gap candidates: `11`
- Diagnostics: `balanced`
- Density: `0.0931`

Artifacts:

- [[../infranodus/graph-snapshots/2026-05-12-022632-wiki-local-graph]]
- [[../infranodus/gap-analysis/2026-05-12-022632-wiki-gap-analysis]]
- [[../output/research-questions/2026-05-12-022632-wiki-research-questions]]
- [[../infranodus/graph-snapshots/2026-05-12-023540-wiki-local-graph]]
- [[../infranodus/gap-analysis/2026-05-12-023540-wiki-gap-analysis]]
- [[../output/research-questions/2026-05-12-023540-wiki-research-questions]]

## Design Constraint

The local engine intentionally excludes cloud AI generation and external API calls. It is suitable for private JH material and can be used before deciding whether a dataset should be sent to external InfraNodus APIs.

## Related Pages

- [[concept-infranodus-graph-knowledge-base]]
- [[pattern-graph-gap-driven-research]]
- [[decision-adopt-infranodus-graph-layer]]
- [[source-infranodus-visual-ai-text-analysis-video]]
