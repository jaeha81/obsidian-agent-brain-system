# LLM Wiki — A Pattern for Building Personal Knowledge Bases Using LLMs

> 원본: 대화에서 직접 제공 (2026-04-19)
> 카테고리: article
> 원저자: 미상 (아이디어 문서)

---

## 원문

Most people's experience with LLMs and documents looks like RAG: you upload a collection of files, the LLM retrieves relevant chunks at query time, and generates an answer. This works, but the LLM is rediscovering knowledge from scratch on every question. There's no accumulation.

The idea here is different. Instead of just retrieving from raw documents at query time, the LLM incrementally builds and maintains a persistent wiki — a structured, interlinked collection of markdown files that sits between you and the raw sources.

The wiki is a persistent, compounding artifact. The cross-references are already there. The contradictions have already been flagged. The synthesis already reflects everything you've read.

### Architecture
Three layers:
1. **Raw sources** — immutable, LLM reads but never modifies
2. **The wiki** — LLM-generated markdown, LLM owns entirely
3. **The schema** — tells LLM how wiki is structured and what workflows to follow

### Operations
- **Ingest**: read source → discuss → write summary → update related pages → update index → log
- **Query**: search index → read relevant pages → synthesize → optionally file answer as new page → log
- **Lint**: find contradictions, stale claims, orphan pages, missing cross-refs, data gaps

### Key Insight
The tedious part of maintaining a knowledge base is not the reading or thinking — it's the bookkeeping. Humans abandon wikis because the maintenance burden grows faster than the value. LLMs don't get bored.

### Related Ideas
- Vannevar Bush's Memex (1945) — private, curated, associative trails
- Optional tooling: qmd (local search), Obsidian Web Clipper, Marp, Dataview

---

*원본 보존됨. 수정 금지.*

## 파생 위키 페이지
- [[wiki/concept-llm-wiki]] — 이 소스에서 추출된 핵심 개념
- [[wiki/source-llm-wiki-pattern]] — 이 소스의 위키 요약 페이지
- [[wiki/overview]] — 위키 전체 합성
