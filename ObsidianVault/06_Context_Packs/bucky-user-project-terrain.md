---
type: context-pack
status: active
owner: Bucky
created: 2026-05-30
freshness: legacy-derived; verify project status before treating dates, versions, funding data, or repo state as current
source:
  - ObsidianVault/09_Archive/migration-conflicts/2026-05-24/Obsidian-Vault/raw/memories/00_overview.md
  - ObsidianVault/09_Archive/migration-conflicts/2026-05-24/Obsidian-Vault/raw/memories/01_personal_career.md
  - ObsidianVault/09_Archive/migration-conflicts/2026-05-24/Obsidian-Vault/raw/memories/04_jh_keanu.md
  - ObsidianVault/09_Archive/migration-conflicts/2026-05-24/Obsidian-Vault/raw/memories/05_jh_estimate_ai.md
  - ObsidianVault/09_Archive/migration-conflicts/2026-05-24/Obsidian-Vault/raw/memories/07_jh_brain.md
  - ObsidianVault/09_Archive/migration-conflicts/2026-05-24/Obsidian-Vault/raw/memories/08_agent_hub_3d.md
  - ObsidianVault/09_Archive/migration-conflicts/2026-05-24/Obsidian-Vault/raw/memories/10_business_strategy.md
tags:
  - #area/ai_automation
  - #status/active
---

# Bucky User and Project Terrain

## Purpose

This pack gives Bucky a compact map of the user's domain, project family, and product direction. It is legacy-derived, so Bucky must verify current repo state, URLs, dates, funding programs, and implementation status before acting on them.

## User Operating Profile

- User identity in this system: JH / jaeha.
- GitHub handle historically used: `jaeha81`.
- Core domain advantage: interior design/construction estimating and site-management experience combined with AI automation building.
- Preferred control model: user controls direction and approval; AI executes inside the approved structure.
- Preferred communication: direct facts, risks, next actions, no unnecessary flattery, no repeated explanation of already-known context.
- Preferred development flow: research -> plan -> user approval -> implementation -> verification -> record.
- Preferred agent model: role-separated agents with clear boundaries, not free-form autonomous execution.

## Domain Knowledge To Preserve

- Interior/construction estimating requires trade classification, quantity takeoff, unit-price normalization, region/market price updates, validation, and exportable reports.
- Spreadsheet and estimate formats vary by company; normalization is a product problem, not a simple parsing detail.
- Site-management experience should inform agent decomposition: scanner, estimator, pricer, validator, reporter, QA.

## Project Terrain

### Obsidian Agent Brain System

Current main operating system for JH agent work. Bucky should treat this Vault as the primary instruction and memory plane.

### JH Brain / Obsidian Second Brain

Legacy concept: a second-brain system that records decisions, project progress, problems/solutions, and user preferences into Obsidian. Current rule: do not revive old `OBSIDIAN-SECOND` paths as active roots; promote useful rules into the current Vault.

### JH-Keanu

Legacy-described meta-agent/orchestrator project with research, plan, frontend, backend, and QA roles. Treat status, version, and bug lists as stale unless verified in the live repo. Reusable pattern: fixed role lanes and async-safe API usage.

### JH-EstimateAI

Interior construction estimating AI concept with a five-agent pipeline:

```text
scanner -> estimator -> pricer -> validator -> reporter
```

Reusable principles:

- domain-specific workflow beats generic chatbot framing;
- quantity, unit price, validation, and report generation should remain separate concerns;
- expert interior/construction knowledge is a differentiator;
- market price updates and template packaging need explicit maintenance paths.

### JH Agent Hub 3D

Legacy visualization concept for agent groups and message/data flows. Reusable principle: visual agent maps are useful only when tied to real task status, routing, and evidence.

### Business Direction

Legacy direction: construction/interior vertical AI products, estimate automation, agent marketplace/exchange, and domain-specific consulting plus AI bundles. Treat funding program names, dates, and amounts as stale until checked against official sources.

### Past And Client Project Memory

Legacy project lists include estimate normalization, vision/inspection systems, pre-construction simulation, SketchFlow, logistics automation, Agent Factory, Agent Exchange, Playwright agents, EONID dashboards, and client deliverables. Bucky should use these as pattern memory only:

- separate JH-owned products from client-owned work;
- do not expose client names, private strategy, or deliverables unless the user explicitly asks and the output is safe;
- reuse proven patterns such as estimate normalization, domain-specific pipelines, visual QA, and deployment packaging;
- verify repo ownership, status, and delivery constraints before referencing any project as current.

## Storage Boundary Rules (HARD RULE)

JH 환경의 허용 저장 루트는 두 곳뿐이다:

- **시스템 루트**: `G:\내 드라이브\obsidian-agent-brain-system\` — Bucky OS, Vault, AgentBus, Context Packs, 대시보드
- **개발 루트**: `D:\AI프로젝트\` — 코드, repo, 프로젝트 파일, 빌드 산출물

이 두 루트 외의 경로(예: `G:\내 드라이브\Obsidian Vault\`, `G:\내 드라이브\AI개발계획\`, `G:\내 드라이브\이재하부장\` 등)는 archive-only / not current operating authority이며, 사용자 명시 승인 없이 신규 파일을 작성하거나 기존 파일을 수정하지 않는다.

**예외**: 사용자가 특정 폴더를 직접 지정하거나 확인을 요청한 경우, 해당 작업 전에 승인을 받은 후 진행한다.

## Bucky Use Rules

1. Use this pack for project orientation and language, not as proof of current status.
2. Verify current repo, deployment, funding, and deadline facts before reporting them as current.
3. When the user asks for new product/project work, map it to the project terrain first, then request or issue a project-specific instruction packet.
4. Preserve the user's domain advantage in implementation plans: do not flatten interior/construction workflows into generic AI chat.
5. If a project-specific instruction conflicts with this terrain pack, the project-specific packet wins unless it weakens security or approval rules.
6. Treat client-project material as sensitive by default. Summarize patterns; do not copy client data into prompts or public notes.
