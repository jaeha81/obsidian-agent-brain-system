---
type: pattern
updated: 2026-05-12
sources: [source-infranodus-llm-wiki-video]
tags: [pattern, graph-gap, research, llm-wiki, infranodus]
  - #status/archive
---

# Graph Gap Driven Research

## Pattern

Use a knowledge graph to find weakly connected clusters, then turn those gaps into research questions, Claude instructions, Codex review targets, or todo items.

## Flow

```text
1. Ingest raw material into raw/
2. Generate or update wiki pages
3. Visualize target folder or files with InfraNodus
4. Inspect main topics, smaller clusters, and disconnected nodes
5. Run gap analysis
6. Generate bridge questions
7. Save outputs to output/
8. Save graph memory to infranodus/
```

## When To Use

- A project has many notes but unclear priorities.
- Claude gives generic summaries.
- Codex needs a better review target list.
- Agent Room logs show activity but not system-level insight.
- JH strategy material spans business, code, operations, and agents.

## Output Types

| Gap Output | Save To |
|------------|---------|
| Research question | `output/research-questions/` |
| Claude implementation instruction | `output/claude-instructions/` |
| Codex review target | `output/codex-review-targets/` |
| Persistent graph relation | `infranodus/ontology/` |
| Visual snapshot | `infranodus/graph-snapshots/` |
| MCP tool output | `infranodus/mcp-logs/` |

## Quality Rule

A useful graph gap should produce a question that is specific enough to act on. Generic questions should be rejected or refined.

## Related Pages

- [[decision-adopt-infranodus-graph-layer]]
- [[concept-infranodus-graph-knowledge-base]]
