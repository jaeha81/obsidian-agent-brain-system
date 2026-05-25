# Wiki Activity Log — JH 개발 볼트

> 형식: `## [YYYY-MM-DD] [타입] | [제목]`
> 파싱: `grep "^## \[" log.md | tail -10`

---

## [2026-04-27] setup | 위키 시스템 초기화

- 액션: LLM Wiki 패턴을 JH 개발 볼트에 적용
- 생성: CLAUDE.md (스키마), wiki/index.md, wiki/log.md, wiki/overview.md
- 생성: 시드 페이지 5개 (entity-mneme, entity-jh-brain-system, concept-agent-philosophy, concept-dev-workflow, entity-agent-ecosystem)
- 비고: OBSIDIAN-SECOND wiki 패턴을 개발 볼트에 이식. 기존 00~07 폴더가 RAW sources 레이어 역할. Vannevar Bush Memex 개념 적용 — LLM이 유지 비용 제거

## 관련 페이지
- [[index]] — 위키 카탈로그
- [[overview]] — 위키 전체 합성

## [2026-05-05] ingest | jh-windows-launcher-dev-pattern.md
- 추가: [[../05_Insights/jh-windows-launcher-dev-pattern]]

## [2026-05-05] ingest | monthly-2026-04.md
- 추가: [[../05_Insights/monthly-2026-04]]

## [2026-05-05] ingest | parallel-architect-boris-cherny.md
- 추가: [[../05_Insights/parallel-architect-boris-cherny]]

## [2026-05-12] integration | InfraNodus Graph LLM Wiki
- Source: user-provided YouTube transcript and InfraNodus official GitHub/docs
- Created: [[source-infranodus-llm-wiki-video]], [[concept-infranodus-graph-knowledge-base]], [[jh-infranodus-upgrade-analysis]]
- Created: [[decision-adopt-infranodus-graph-layer]], [[pattern-graph-gap-driven-research]]
- Implemented: Obsidian plugin `infranodus-graph-view`, Claude Code MCP `infranodus`
- Output: [[../output/claude-instructions/2026-05-12-infranodus-briefing]], [[../output/codex-review-targets/2026-05-12-infranodus-review-targets]], [[../output/todo/2026-05-12-infranodus-adoption-todo]]

## [2026-05-12] local-engine | JH Local Knowledge Graph
- Script: `G:\내 드라이브\JH-SHARED\scripts\jh-local-knowledge-graph.ps1`
- Source: `wiki/`
- Result: 20 files, 160 nodes, 1340 edges, 10 gap candidates
- Created: [[concept-jh-local-knowledge-graph-engine]]
- Created: [[../infranodus/graph-snapshots/2026-05-12-022632-wiki-local-graph]], [[../infranodus/gap-analysis/2026-05-12-022632-wiki-gap-analysis]], [[../output/research-questions/2026-05-12-022632-wiki-research-questions]]

## [2026-05-12] enhancement | InfraNodus visual AI text analysis video
- Source: [[source-infranodus-visual-ai-text-analysis-video]]
- Updated local engine: diagnostics, biased/dispersed/balanced status, discourse entrance points, shortest path for bridge candidates
- New run: [[../infranodus/graph-snapshots/2026-05-12-023540-wiki-local-graph]], [[../infranodus/gap-analysis/2026-05-12-023540-wiki-gap-analysis]]
- Result: 21 files, 176 nodes, 1433 edges, 11 gap candidates, status balanced

## [2026-05-12] fix | Obsidian local graph execution
- Problem: Markdown HTML link/iframe was unreliable inside Obsidian.
- Fix: Added local Obsidian plugin `jh-local-graph-view` that reads latest ontology JSON and renders the graph directly on canvas inside Obsidian.
- Open: left ribbon network icon or Command Palette -> `Open JH Local Graph`.
- Verified: plugin enabled, workspace contains `jh-local-graph-view`, no plugin load errors in Obsidian log.

## [2026-05-12] fix | Obsidian plugin permission control
- Problem: `.obsidian/community-plugins.json` had a malformed nested object, so plugin activation could be unreliable.
- Fix: Rewrote it as a flat plugin id string array and kept `safeMode=false`.
- Verified: `jh-local-graph-view=True`, `infranodus-graph-view=True`, workspace contains `JH Local Graph`, no plugin load errors in Obsidian log.

## [2026-05-12] fix | Local graph viewport and sphere layout
- Problem: graph view was clipped and did not show the whole sphere-like structure.
- Fix: changed initial layout to spherical golden-angle distribution, added automatic fit-to-view, added `fit` button, removed fixed minimum canvas height, and added anchor force to preserve global form.
- Verified: Obsidian restarted with no plugin load errors.

## [2026-05-20] sync-check
- [2026-05-20] 신규 페이지 (index 미등록): [[concept-windows-launcher-pattern]]
- [2026-05-20] 신규 페이지 (index 미등록): [[concept-llm-wiki]]
- [2026-05-20] 신규 페이지 (index 미등록): [[concept-obsidian-plugins]]
- [2026-05-20] 신규 페이지 (index 미등록): [[lint-quick]]
- [2026-05-20] 신규 페이지 (index 미등록): [[entity-claude-ai-desktop-setup]]
- [2026-05-20] 신규 페이지 (index 미등록): [[source-jh-windows-launcher-insight]]
- [2026-05-20] 신규 페이지 (index 미등록): [[source-llm-wiki-pattern]]
