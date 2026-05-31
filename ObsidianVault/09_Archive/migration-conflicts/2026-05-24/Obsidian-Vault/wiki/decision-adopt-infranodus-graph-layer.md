---
type: decision
updated: 2026-05-12
sources: [source-infranodus-llm-wiki-video, jh-infranodus-upgrade-analysis]
tags: [decision, infranodus, graph-layer, obsidian, mcp]
  - #status/archive
---

# Adopt InfraNodus Graph Layer

## Decision

Adopt InfraNodus as the graph intelligence layer for the JH Obsidian LLM Wiki.

The JH Vault already has a working `raw/` and `wiki/` structure. InfraNodus adds visual graph analysis, content gap detection, research question generation, ontology graph memory, and Claude Code MCP access.

## Implemented

- Installed Obsidian plugin: `infranodus-graph-view`
- Enabled the plugin in `.obsidian/community-plugins.json`
- Registered Claude Code MCP server: `infranodus`
- Added graph memory folders under `infranodus/`
- Added action output folders under `output/`
- Added source, concept, and upgrade analysis wiki pages

## MCP Mode

Claude Code now has this MCP server registered:

```text
infranodus: npx -y infranodus-mcp-server
```

No API key was stored. This uses the official limited no-key mode until an InfraNodus API key is explicitly provided by the user.

## Operating Rule

Do not send sensitive JH raw data to external analysis by default. Start with redacted summaries or non-sensitive corpora, then escalate only after the user approves the data class.

## Related Pages

- [[source-infranodus-llm-wiki-video]]
- [[concept-infranodus-graph-knowledge-base]]
- [[jh-infranodus-upgrade-analysis]]
- [[pattern-graph-gap-driven-research]]
