---
type: synthesis
updated: 2026-05-12
sources: [source-infranodus-llm-wiki-video, concept-llm-wiki]
tags: [jh-system, infranodus, obsidian, graph-view, upgrade-analysis]
  - #status/archive
---

# JH InfraNodus Upgrade Analysis

## Summary

The JH Obsidian Vault already has the beginning of an LLM Wiki: `raw/` stores source material and `wiki/` stores synthesized knowledge pages. InfraNodus should be adopted as an active graph layer on top of this structure. This upgrades the system from a searchable knowledge base into a living knowledge base that can reveal structure, gaps, and next actions.

## Before

```text
raw material
-> wiki pages
-> human or LLM reads files
-> answer or summary
```

Strengths:

- Persistent notes.
- Obsidian-readable Markdown.
- Good base for Claude/Codex context.

Limits:

- Weak visual overview.
- Hard to detect isolated knowledge.
- Hard to find missing connections.
- LLM output can become generic synthesis.
- No persistent graph memory of concept relations.

## After

```text
raw material
-> wiki pages
-> InfraNodus graph view
-> content gap analysis
-> AI-generated questions
-> ontology graph memory
-> next Claude/Codex session uses the improved structure
```

Expected upgrades:

| Area | Current | With InfraNodus |
|------|---------|-----------------|
| Search | File and link based | Cluster and gap based |
| Visual overview | Basic Obsidian graph | Topic graph with structural metrics |
| AI reasoning | RAG-like synthesis | Graph-guided reasoning |
| Memory | Notes accumulate | Relations and ontology accumulate |
| Review | Manual file inspection | Graph-targeted review priorities |
| New ideas | Probable LLM answer | Gap-bridging questions |
| Operations | Session-by-session context | Living map of JH system knowledge |

## High-Value JH Use Cases

### 1. Claude Implementation Review

Codex can inspect graph outputs to find which components are isolated, overconnected, or missing review links. This improves review targeting before reading every file manually.

### 2. Agent Room Knowledge Map

Agent messages, session summaries, `synapse.md`, and handoff notes can be ingested into `raw/`. InfraNodus can then show which agents, tasks, and protocols are actually connected in practice.

### 3. Repeated Error Pattern Detection

Claude error patterns can be represented as graph nodes connected to affected files, workflows, and protocols. Repeated clusters should become candidates for `CLAUDE.md` rule upgrades.

### 4. Strategic Research

Business ideas, product notes, market research, and technical constraints can be analyzed together. Gap analysis can generate concrete research questions instead of generic summaries.

## Recommended JH Folder Model

```text
C:\Users\user1\Documents\Obsidian Vault\
  raw\
    jh-system\
    agent-room\
    claude-sessions\
    youtube-notes\

  wiki\
    concepts\
    connections\
    entities\
    sources\
    questions\

  infranodus\
    ontology\
    gap-analysis\
    graph-snapshots\
    mcp-logs\

  output\
    research-questions\
    claude-instructions\
    codex-review-targets\
    todo\
```

## Adoption Sequence

1. Keep the existing `raw/` and `wiki/` folders.
2. Add `infranodus/` and `output/` as derived analysis layers.
3. Install and test InfraNodus graph view in Obsidian or IDE first with non-sensitive data.
4. Use one pilot corpus: JH system documents plus the InfraNodus video transcript.
5. Run graph visualization and gap analysis.
6. Save graph outputs and generated questions.
7. Only then connect the MCP server for automated Claude/Codex use.

## Risk Controls

- Treat external graph analysis as non-private unless confirmed otherwise.
- Do not send raw secrets, private customer data, or unpublished business-sensitive notes to external APIs.
- Use summaries or redacted extracts for the first pilot.
- Keep `.env` and API keys out of GitHub, Obsidian, and JH-SHARED.

## Decision

Adopt InfraNodus actively, but in stages. The first stage should prove visual graph value on a controlled corpus. The second stage should add ontology graph storage. The third stage should connect MCP so Claude/Codex can run graph and gap analysis directly.

## Related Pages

- [[source-infranodus-llm-wiki-video]]
- [[concept-infranodus-graph-knowledge-base]]
- [[concept-llm-wiki]]
