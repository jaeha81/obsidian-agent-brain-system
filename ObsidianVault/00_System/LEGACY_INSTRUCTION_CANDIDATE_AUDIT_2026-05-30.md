---
type: audit
status: active
created: 2026-05-30
owner: Bucky
tags:
  - #status/active
---

# Legacy Instruction Candidate Audit - 2026-05-30

## Purpose

Track legacy integration-system instruction sources that still need review, compression, or explicit archival decisions. This prevents old systems from silently remaining the operating source of truth.

## Promoted To Current System

| Legacy source | Current destination | Status |
|---|---|---|
| `OBSIDIAN-SECOND/claude-knowledge/preferences/context-usage-principle.md` | `ObsidianVault/06_Context_Packs/bucky-context-efficiency-goal-mode.md` | promoted |
| `OBSIDIAN-SECOND/claude-knowledge/errors/context-waste-patterns.md` | `ObsidianVault/06_Context_Packs/bucky-context-efficiency-goal-mode.md` | promoted |
| `Obsidian-Vault/Codex_Goal_Mode_Playbook.md` | `ObsidianVault/06_Context_Packs/bucky-context-efficiency-goal-mode.md` | promoted |
| `Obsidian-Vault/03_Prompts/ai-api/ai-api-routing-architect.md` | `ObsidianVault/06_Context_Packs/bucky-ai-api-routing-policy.md` | promoted |
| `Obsidian-Vault/03_Prompts/ai-api/ai-api-catalog.md` | `ObsidianVault/06_Context_Packs/bucky-ai-api-routing-policy.md` | promoted as stale-catalog warning, not as current price source |
| `OBSIDIAN-SECOND/CLAUDE.md` | `ObsidianVault/06_Context_Packs/bucky-vault-ingestion-record-policy.md` | promoted |
| `Obsidian-Vault/03_Prompts/templates/*.md` | `ObsidianVault/06_Context_Packs/bucky-vault-ingestion-record-policy.md` | promoted as record shapes |
| `Obsidian-Vault/raw/memories/03_tech_stack.md` | `ObsidianVault/06_Context_Packs/bucky-security-runtime-governance.md` | promoted selected runtime/code defaults |
| `Obsidian-Vault/raw/memories/06_jh_harness.md` | `ObsidianVault/06_Context_Packs/bucky-security-runtime-governance.md` | promoted selected control/logging rules |
| `Obsidian-Vault/raw/memories/12_ai_tools.md` | `ObsidianVault/06_Context_Packs/bucky-security-runtime-governance.md` | promoted selected AI tool safety rules |
| `Obsidian-Vault/raw/memories2/12_보안_법적기준.md` | `ObsidianVault/06_Context_Packs/bucky-security-runtime-governance.md` | promoted selected security/legal rules |
| `Obsidian-Vault/raw/memories/00_overview.md` | `ObsidianVault/06_Context_Packs/bucky-user-project-terrain.md` | promoted selected project map |
| `Obsidian-Vault/raw/memories/01_personal_career.md` | `ObsidianVault/06_Context_Packs/bucky-user-project-terrain.md` | promoted selected user/domain profile |
| `Obsidian-Vault/raw/memories/04_jh_keanu.md` | `ObsidianVault/06_Context_Packs/bucky-user-project-terrain.md` | promoted selected stale project terrain |
| `Obsidian-Vault/raw/memories/05_jh_estimate_ai.md` | `ObsidianVault/06_Context_Packs/bucky-user-project-terrain.md` | promoted selected domain/product terrain |
| `Obsidian-Vault/raw/memories/07_jh_brain.md` | `ObsidianVault/06_Context_Packs/bucky-user-project-terrain.md` | promoted selected second-brain terrain |
| `Obsidian-Vault/raw/memories/08_agent_hub_3d.md` | `ObsidianVault/06_Context_Packs/bucky-user-project-terrain.md` | promoted selected visualization terrain |
| `Obsidian-Vault/raw/memories/10_business_strategy.md` | `ObsidianVault/06_Context_Packs/bucky-user-project-terrain.md` | promoted selected business direction with stale-data warning |
| `OBSIDIAN-SECOND/raw/gpt/메모리.txt` inventory excerpt, `ObsidianVault/03_Projects/agents/mneme.md`, `ObsidianVault/03_Projects/agents/agent-dispatcher.md` | `ObsidianVault/06_Context_Packs/bucky-user-communication-output-policy.md` | promoted user-facing output and copyable prompt rules; quarantined source was not reopened |
| `OBSIDIAN-SECOND/agent-room-knowledge/2026-05-15--API-rate-limiting---.md` | `ObsidianVault/06_Context_Packs/bucky-context-efficiency-goal-mode.md` | already covered by Goal Mode packet rules; archive-only source |
| `OBSIDIAN-SECOND/agent-room-knowledge/2026-05-15---redacted-key---.md` | none | archive-only; secret-like test string and filename redacted |

## Remaining High-Value Candidates

| Candidate | Why it matters | Next handling |
|---|---|---|
| `Obsidian-Vault/raw/memories/09_past_projects.md` | `ObsidianVault/06_Context_Packs/bucky-user-project-terrain.md` | promoted only as stale pattern memory; source remains archive/reference-only |
| `Obsidian-Vault/raw/memories/11_client_projects.md` | `ObsidianVault/06_Context_Packs/bucky-user-project-terrain.md` | promoted only as sensitive client-work handling rule; source remains archive/reference-only |
| `Obsidian-Vault/raw/memories2/00_INDEX.md` | existing terrain/security/record packs | duplicate index; archive/reference-only |
| `Obsidian-Vault/raw/memories2/01_정체성_경력.md` | `ObsidianVault/06_Context_Packs/bucky-user-project-terrain.md` | covered by user/domain profile; archive/reference-only |
| `Obsidian-Vault/raw/memories2/02_JH_브랜드_생태계.md` | `ObsidianVault/06_Context_Packs/bucky-user-project-terrain.md` | covered by brand/project terrain; archive/reference-only |
| `Obsidian-Vault/raw/memories2/03_사업_철학_의사결정.md` | `ObsidianVault/06_Context_Packs/bucky-security-runtime-governance.md` and `bucky-context-efficiency-goal-mode.md` | covered by approval/risk/decision rules; archive/reference-only |
| `Obsidian-Vault/raw/memories2/04_목표_로드맵.md` | `ObsidianVault/06_Context_Packs/bucky-user-project-terrain.md` | covered only as stale direction; dates/funding require verification |
| `Obsidian-Vault/raw/memories2/05_인테리어_견적시스템.md` | `ObsidianVault/06_Context_Packs/bucky-user-project-terrain.md` and `bucky-security-runtime-governance.md` | covered by EstimateAI/domain/security rules |
| `Obsidian-Vault/raw/memories2/07_AI_하네스_에이전트_아키텍처.md` | `ObsidianVault/06_Context_Packs/bucky-security-runtime-governance.md` | covered by role separation/logging/runtime governance |
| `Obsidian-Vault/raw/memories2/09_완료_프로젝트_아카이브.md` | `ObsidianVault/06_Context_Packs/bucky-user-project-terrain.md` | pattern memory only; archive/reference-only |
| `Obsidian-Vault/raw/memories2/10_수익화_전략.md` | `ObsidianVault/06_Context_Packs/bucky-user-project-terrain.md` | stale strategic direction only; verify before use |
| `Obsidian-Vault/raw/memories2/11_Obsidian_세컨드브레인_체크포인트.md` | `ObsidianVault/06_Context_Packs/bucky-vault-ingestion-record-policy.md` | covered by record/checkpoint policy |
| `Obsidian-Vault/raw/memories2/12_보안_법적기준.md` | `ObsidianVault/06_Context_Packs/bucky-security-runtime-governance.md` | covered by security/legal handling |
| `Obsidian-Vault/raw/memories2/13_개발_프롬프트_템플릿.md` | `AGENTS.md`, `CLAUDE.md`, `bucky-context-efficiency-goal-mode.md`, `bucky-vault-ingestion-record-policy.md` | covered by packet/template rules |
| `ObsidianVault/09_Archive/migration-conflicts/2026-05-24/JH-Agent-Room/README.md` | Old sync/Agent Room UI operating behavior | promoted selected role separation, append-only log, admin-secret, sync-not-push, and Codex review gate rules into `ObsidianVault/05_Frameworks/AgentBus/agentbus_protocol.md`; old paths and auto-push wording remain archive-only |
| `ObsidianVault/03_Projects/agents/roles.md` and `ObsidianVault/05_Frameworks/guides/roles.md` | Active role guides still had mojibake and old Agent Room push assumptions | rewritten 2026-05-30 as Bucky-centered role boundary with explicit approval gates |
| `ObsidianVault/03_Projects/agents/sub-agents.md` | Active sub-agent guide still had mojibake and stale model-specific subagent language | rewritten 2026-05-30 as role-packet guidance tied to Bucky, AgentBus, and Context Packs |
| `ObsidianVault/09_Archive/migration-conflicts/2026-05-24/_organized/needs-merge/Obsidian-Vault/wiki/concept-dev-workflow.md` and `ObsidianVault/03_Knowledge/bridges/01_raw-memories-02_dev_workflow-md.md` | Plan-first, task sizing, implementation loop, and verification rules still useful for Bucky dispatch | promoted selected rules into `ObsidianVault/06_Context_Packs/bucky-development-workflow-policy.md`; mojibake/raw duplicates remain archive/reference-only |
| `ObsidianVault/09_Archive/migration-conflicts/2026-05-24/_organized/needs-merge/Obsidian-Vault/raw/memories/02_dev_workflow.md` and `ObsidianVault/09_Archive/migration-conflicts/2026-05-24/Obsidian-Vault/raw/memories/02_dev_workflow.md` | Duplicate raw development workflow imports | covered by `bucky-development-workflow-policy.md`; archive/reference-only |
| `ObsidianVault/03_Knowledge/bridges/01_raw-memories-08_agent_hub_3d-md.md` | Agent Hub / 3D visualization project memory bridge | covered by `bucky-user-project-terrain.md` as stale visualization terrain; archive/reference-only |
| `ObsidianVault/09_Archive/migration-conflicts/2026-05-24/*/Obsidian-Vault/sessions/2026-05-10-19-26-59-688-codex-agent-room-ui-20260510-codex.md` | Old Agent Room UI session evidence | useful workflow rules covered by `agentbus_protocol.md`; session logs remain archive/reference-only |
| `ObsidianVault/09_Archive/migration-conflicts/2026-05-24/*/Obsidian-Vault/sessions/2026-05-11-06-36-06-496-codex-agent-room-answer-flow-20260511-codex.md` | Old Agent Room answer-flow session evidence | useful workflow rules covered by `agentbus_protocol.md`; session logs remain archive/reference-only |
| `ObsidianVault/09_Archive/migration-conflicts/2026-05-24/*/Obsidian-Vault/sessions/2026-05-12-03-02-53-011-codex-infranodus-local-graph-20260512-codex.md` | Old graph verification session evidence | covered by Graphify/LegalizeKR scoped policies and Goal Mode verification rules; session logs remain archive/reference-only |
| `ObsidianVault/09_Archive/sessions/2026-05-10-19-26-59-688-codex-agent-room-ui-20260510-codex.md`, `2026-05-11-06-36-06-496-codex-agent-room-answer-flow-20260511-codex.md`, `2026-05-12-03-02-53-011-codex-infranodus-local-graph-20260512-codex.md`, `2026-05-17-06-40-35-904-today-plus-obsidian-archiver-20260517-codex.md` | Archived Codex session memories that match instruction-like patterns | archive/reference-only; reusable rules already covered by Context Packs and AgentBus protocol |
| `ObsidianVault/09_Archive/migration-conflicts/2026-05-24/*/Obsidian-Vault/01_Projects/agents/COMMON-PHILOSOPHY.md` | Old sub-agent philosophy document | compressed into `roles.md`, `sub-agents.md`, and `bucky-agent-os-legacy-rules.md`; archive/reference-only |
| `ObsidianVault/09_Archive/migration-conflicts/2026-05-24/*/Obsidian-Vault/01_Projects/agents/evolution.md` | Old agent evolution log rules | covered by `bucky-vault-ingestion-record-policy.md` and current evidence/report rules; archive/reference-only |
| `ObsidianVault/09_Archive/migration-conflicts/2026-05-24/*/Obsidian-Vault/01_Projects/agents/mneme.md` | Old memory-agent instructions | covered by `bucky-vault-ingestion-record-policy.md`; archive/reference-only |
| `ObsidianVault/03_Projects/agents/COMMON-PHILOSOPHY.md`, `mneme.md`, `rank-system.md`, `evolution.md` | Active-folder legacy Mneme/rank authority could confuse current Bucky OS routing | marked 2026-05-30 with superseded reference-only warnings; current authority is Bucky packets, roles, root `AGENTS.md`, and root `CLAUDE.md` |

## Secret-Like Archive Quarantine

These paths are instruction-like enough to appear in migration inventory, but are quarantined because the scanner found secret-like terms or patterns. Do not promote, quote, or broadly read them until a targeted redaction pass is explicitly requested.

| Candidate | Current handling |
|---|---|
| `ObsidianVault/09_Archive/legacy-import/legacy-import/Obsidian-Vault/raw/memories2/06_기술스택_개발원칙 (1).md` | quarantined; archive/reference-only pending targeted redaction review |
| `ObsidianVault/09_Archive/sessions/2026-05-16-23-40-44-544-codex-20260516-234040-codex.md` | quarantined; archive/reference-only pending targeted redaction review |
| `ObsidianVault/09_Archive/sessions/2026-05-20-09-03-03-126-codex-20260520-session-end-codex.md` | quarantined; archive/reference-only pending targeted redaction review |
| `ObsidianVault/09_Archive/sessions/2026-05-15-07-51-08.md` | quarantined; archive/reference-only pending targeted redaction review |
| `ObsidianVault/09_Archive/legacy-import/legacy-import/Obsidian-Vault/01_Projects/knowledge/gpt-memory/gpt-memory-tech-stack.md` | quarantined; archive/reference-only pending targeted redaction review |
| `ObsidianVault/09_Archive/migration-conflicts/2026-05-24/_organized/superseded/Obsidian-Vault/output/codex-review-targets/2026-05-12-infranodus-functional-verification.md` | quarantined; archive/reference-only pending targeted redaction review |
| `ObsidianVault/09_Archive/migration-conflicts/2026-05-24/Obsidian-Vault/output/codex-review-targets/2026-05-12-infranodus-functional-verification.md` | quarantined; archive/reference-only pending targeted redaction review |
| `ObsidianVault/09_Archive/sessions/2026-05-17-06-40-51-844-codex-20260517-064047-codex.md` | quarantined; archive/reference-only pending targeted redaction review |
| `ObsidianVault/09_Archive/sessions/2026-05-17-07-18-31-857-codex-20260517-071827-codex.md` | quarantined; archive/reference-only pending targeted redaction review |
| `ObsidianVault/09_Archive/legacy-import/legacy-import/OBSIDIAN-SECOND/raw/gpt/메모리.txt` | quarantined; archive/reference-only pending targeted redaction review |
| `ObsidianVault/09_Archive/legacy-import/legacy-import/Obsidian-Vault/01_Projects/knowledge/gpt-memory/gpt-memory-projects.md` | quarantined; archive/reference-only pending targeted redaction review |
| `ObsidianVault/09_Archive/migration-conflicts/2026-05-24/_organized/superseded/Obsidian-Vault/wiki/jh-infranodus-upgrade-analysis.md` | quarantined; archive/reference-only pending targeted redaction review |
| `ObsidianVault/09_Archive/migration-conflicts/2026-05-24/Obsidian-Vault/wiki/jh-infranodus-upgrade-analysis.md` | quarantined; archive/reference-only pending targeted redaction review |

## High-Score Non-Secret Candidate Triage

These paths scored high in inventory but do not need direct promotion as live authority. Useful rules are already covered by current Bucky packs; stale paths, auto-git habits, and old agent hierarchy remain archive-only.

| Candidate | Current handling |
|---|---|
| `ObsidianVault/03_Knowledge/bridges/01_raw-memories-12_ai_tools-md.md` | covered by `bucky-security-runtime-governance.md` and AI tool safety rules; bridge remains reference-only |
| `ObsidianVault/09_Archive/legacy-import/Obsidian-Vault/sessions/codex-goal-mode-20260517.md` | covered by `bucky-context-efficiency-goal-mode.md`; archive/reference-only |
| `ObsidianVault/09_Archive/migration-conflicts/2026-05-24/*/Obsidian-Vault/sessions/2026-05-06-01-27-45-288-codex-test-20260506-fallback-save-codex.md` | covered by current session-save and evidence policy; old fallback session remains archive/reference-only |
| `ObsidianVault/09_Archive/legacy-import/legacy-import/OBSIDIAN-SECOND/Claude Code 사용 가이드.md` | useful launch idea is superseded by root `CLAUDE.md` and Bucky packet selector; old Obsidian plugin and auto-git instructions are archive-only |
| `ObsidianVault/09_Archive/legacy-import/legacy-import/*/raw/memories2/05_인테리어_견적시스템 (1).md` | covered by `bucky-user-project-terrain.md` and security/runtime rules; archive/reference-only |
| `ObsidianVault/09_Archive/legacy-import/Obsidian-Vault/05_Logs/daily/2026-03-23.md` | daily/session evidence only; covered by record policy; archive/reference-only |
| `ObsidianVault/09_Archive/migration-conflicts/2026-05-24/*/Obsidian-Vault/01-daily/2026-04-25-retrospective.md` | retrospective workflow evidence; covered by development workflow and record policy; archive/reference-only |
| `ObsidianVault/09_Archive/migration-conflicts/2026-05-24/*/Obsidian-Vault/01-daily/2026-04-26-retrospective.md` | retrospective workflow evidence; covered by development workflow and record policy; archive/reference-only |
| `ObsidianVault/09_Archive/migration-conflicts/2026-05-24/*/Obsidian-Vault/01_Projects/agents/rank-system.md` | old gamified rank/permission model is not current authority; context-budget idea covered by compact Bucky packets; archive-only |
| `ObsidianVault/09_Archive/migration-conflicts/2026-05-24/*/Obsidian-Vault/07_Archive/sessions/2026-04-25-session-log.md` | session evidence only; covered by record policy; archive/reference-only |
| `ObsidianVault/09_Archive/migration-conflicts/2026-05-24/*/Obsidian-Vault/sessions/2026-05-11-03-08-11.md` | session evidence only; covered by record policy; archive/reference-only |
| `ObsidianVault/09_Archive/migration-conflicts/2026-05-24/*/Obsidian-Vault/sessions/2026-05-11-04-01-13.md` | session evidence only; covered by record policy; archive/reference-only |
| `ObsidianVault/09_Archive/migration-conflicts/2026-05-24/*/Obsidian-Vault/wiki/concept-agent-philosophy.md` | compressed into current `roles.md`, `sub-agents.md`, and Bucky Agent OS rules; archive/reference-only |
| `ObsidianVault/09_Archive/migration-conflicts/2026-05-24/*/Obsidian-Vault/wiki/entity-agent-ecosystem.md` | compressed into current role and AgentBus protocols; archive/reference-only |
| `ObsidianVault/09_Archive/sessions/2026-05-06-01-27-45-288-codex-test-20260506-fallback-save-codex.md` | session-save evidence only; covered by record policy; archive/reference-only |
| `ObsidianVault/03_Knowledge/bridges/01_raw-inbox-2026-04-*-claude-code-md.md` | old inbox bridge evidence; current authority is `CLAUDE.md`, `AGENTS.md`, and Bucky packets |
| `ObsidianVault/03_Knowledge/bridges/01_raw-memories-*.md` | raw memory bridge evidence; reusable terrain/security/workflow rules already compressed into Context Packs |
| `ObsidianVault/03_Knowledge/bridges/01_raw-memories2-*.md` | raw memory bridge evidence; reusable terrain/security/workflow rules already compressed into Context Packs |
| `ObsidianVault/09_Archive/daily/2026-04-*-retrospective.md` | old retrospective evidence; covered by record and development workflow policies |
| `ObsidianVault/09_Archive/logs/daily/2026-03-23.md` | old daily evidence; covered by record policy |
| `ObsidianVault/09_Archive/legacy-import/legacy-import/Obsidian-Vault/JH 하네스 대시보드/2026-04-25-일정계획표.md` | old planning artifact; useful task-sizing behavior covered by `bucky-development-workflow-policy.md` |
| `ObsidianVault/09_Archive/migration-conflicts/2026-05-24/*/Obsidian-Vault/03_Prompts/templates/agent-skill.md` | old template; current template behavior covered by vault ingestion/record policy |
| `ObsidianVault/09_Archive/migration-conflicts/2026-05-24/*/Obsidian-Vault/03_Prompts/templates/session-summary.md` | old template; current session evidence behavior covered by vault ingestion/record policy |
| `ObsidianVault/09_Archive/migration-conflicts/2026-05-24/*/Obsidian-Vault/output/claude-instructions/index.md` | old generated index; current authority is root `CLAUDE.md` plus Bucky-selected packets |
| `ObsidianVault/09_Archive/migration-conflicts/2026-05-24/*/Obsidian-Vault/sessions/2026-05-06-01-29-02-840-codex-test-20260506-fallback-ascii-codex.md` | session-save evidence only; covered by record policy |
| `ObsidianVault/09_Archive/sessions/2026-05-11-03-08-11.md` | session evidence only; covered by record policy |
| `ObsidianVault/09_Archive/sessions/2026-05-11-04-01-13.md` | session evidence only; covered by record policy |
| `ObsidianVault/09_Archive/sessions/legacy/2026-04-25-session-log.md` | session evidence only; covered by record policy |

## Low-Score Candidate Sweep

These wildcard groups cover the remaining low-score inventory candidates. They are not promoted as live instructions; current authority stays in Bucky Context Packs, framework docs, `AGENTS.md`, and `CLAUDE.md`.

| Candidate group | Current handling |
|---|---|
| `ObsidianVault/03_Knowledge/hubs/*.md` | active knowledge orientation only; not an instruction source unless a Bucky packet cites a current framework/context pack |
| `ObsidianVault/03_Projects/github-repos/*.md` | repository catalog metadata only; not project operating instructions |
| `ObsidianVault/03_Knowledge/bridges/01_raw-*.md` | raw bridge evidence only; reusable rules must be compressed into Context Packs before use |
| `ObsidianVault/09_Archive/legal-cleanup-backup/*legal_pack.md` | legal archive backup only; current legal work must use `ObsidianVault/05_Frameworks/LegalizeKR/legalize_update_policy.md` and verified current sources |
| `ObsidianVault/09_Archive/logs/github-scans/github-scan-*.md` | old GitHub scan evidence only; verify repositories live before using any finding |
| `ObsidianVault/09_Archive/legacy-import/Obsidian-Vault/05_Logs/github-scan-*.md` | old GitHub scan evidence only; verify repositories live before using any finding |
| `ObsidianVault/09_Archive/legacy-import/Obsidian-Vault/05_Logs/daily/*.md` | old daily evidence only; current record authority is `bucky-vault-ingestion-record-policy.md` |
| `ObsidianVault/09_Archive/logs/daily/*.md` | old daily evidence only; current record authority is `bucky-vault-ingestion-record-policy.md` |
| `ObsidianVault/09_Archive/daily/*.md` | old retrospective evidence only; current workflow authority is `bucky-development-workflow-policy.md` |
| `ObsidianVault/09_Archive/sessions/*.md` | archived session evidence only; reusable rules must be explicitly promoted into Context Packs |
| `ObsidianVault/09_Archive/sessions/legacy/*.md` | archived session evidence only; reusable rules must be explicitly promoted into Context Packs |
| `ObsidianVault/09_Archive/legacy-import/legacy-import/OBSIDIAN-SECOND/_templates/*.md` | old LLM wiki templates; current record templates are governed by `bucky-vault-ingestion-record-policy.md` |
| `ObsidianVault/09_Archive/legacy-import/legacy-import/OBSIDIAN-SECOND/raw/jh-mobile-second-brain/**` | mobile second-brain raw data/logs; archive/reference-only unless a Bucky packet requests targeted ingestion |
| `ObsidianVault/09_Archive/legacy-import/legacy-import/*/_graph-index.md` | old graph indexes; current graph work is governed by Graphify framework docs |
| `ObsidianVault/09_Archive/legacy-import/legacy-import/*/.smart-env/*.json` | old plugin environment data; not current runtime authority |
| `ObsidianVault/09_Archive/legacy-import/legacy-import/OBSIDIAN-SECOND/raw/articles/*.md` | source articles; reference-only unless distilled into a Context Pack |
| `ObsidianVault/09_Archive/legacy-import/legacy-import/Obsidian-Vault/01_Projects/knowledge/gpt-memory/*.md` | old GPT memory exports; reusable user/project terrain already belongs in Bucky Context Packs |
| `ObsidianVault/09_Archive/legacy-import/legacy-import/OBSIDIAN-SECOND/agent-room-knowledge/handoffs/*.md` | old Agent Room handoff evidence; current handoff flow uses AgentBus protocol and record policy |
| `ObsidianVault/09_Archive/legacy-import/legacy-import/OBSIDIAN-SECOND/claude-knowledge/patterns/*.md` | old Claude pattern notes; reusable patterns must be compressed into Bucky packs before use |
| `ObsidianVault/09_Archive/legacy-import/legacy-import/Obsidian-wrapper/**` | wrapper import evidence only; not current authority |
| `ObsidianVault/09_Archive/migration-conflicts/2026-05-24/*/Obsidian-Vault/00_Inbox/*.md` | old inbox evidence; current intake authority is Bucky packet selection and record policy |
| `ObsidianVault/09_Archive/migration-conflicts/2026-05-24/*/Obsidian-Vault/01-daily/*.md` | old daily evidence; current workflow/record authority is Bucky Context Packs |
| `ObsidianVault/09_Archive/migration-conflicts/2026-05-24/*/Obsidian-Vault/01_Projects/brain/*.md` | old brain/profile docs; current user terrain and preferences must live in Bucky packs |
| `ObsidianVault/09_Archive/migration-conflicts/2026-05-24/*/Obsidian-Vault/01_Projects/jh-estimate-system-guide.md` | old EstimateAI guide; current domain terrain is `bucky-user-project-terrain.md` |
| `ObsidianVault/09_Archive/migration-conflicts/2026-05-24/*/Obsidian-Vault/03_Prompts/templates/*.md` | old prompt templates; current template/record behavior is governed by Bucky record policy |
| `ObsidianVault/09_Archive/migration-conflicts/2026-05-24/*/Obsidian-Vault/05_Insights/*.md` | old insight notes; reference-only unless compressed into a Context Pack |
| `ObsidianVault/09_Archive/migration-conflicts/2026-05-24/*/Obsidian-Vault/05_Logs/daily/*.md` | old daily evidence; current record authority is Bucky record policy |
| `ObsidianVault/09_Archive/migration-conflicts/2026-05-24/*/Obsidian-Vault/07_Archive/sessions/*.md` | old session evidence; current session authority is Bucky record policy |
| `ObsidianVault/09_Archive/migration-conflicts/2026-05-24/*/Obsidian-Vault/infranodus/gap-analysis/*.md` | old graph gap-analysis evidence; current graph work is governed by Graphify framework docs |
| `ObsidianVault/09_Archive/migration-conflicts/2026-05-24/*/Obsidian-Vault/output/**/*.md` | old generated outputs; reference-only unless selected by a current Bucky packet |
| `ObsidianVault/09_Archive/migration-conflicts/2026-05-24/*/Obsidian-Vault/sessions/*.md` | old session memories; current authority is Bucky record policy and Context Packs |
| `ObsidianVault/09_Archive/migration-conflicts/2026-05-24/*/Obsidian-Vault/wiki/*.md` | old wiki pages; reference-only unless distilled into current framework docs or Context Packs |
| `ObsidianVault/09_Archive/migration-conflicts/2026-05-24/*/OBSIDIAN-SECOND/wiki/*.md` | old second-brain wiki pages; reference-only unless distilled into current framework docs or Context Packs |
| `ObsidianVault/09_Archive/migration-conflicts/2026-05-24/*/OBSIDIAN-SECOND/환영합니다!.md` | old welcome page; archive-only |
| `ObsidianVault/09_Archive/migration-conflicts/2026-05-24/*/OBSIDIAN-SECOND/raw/jh-mobile-second-brain/**` | old mobile second-brain data; archive/reference-only unless targeted ingestion is requested |
| `ObsidianVault/09_Archive/migration-conflicts/2026-05-24/Obsidian-Vault/00_Inbox/*.md` | old direct inbox evidence; current intake authority is Bucky packet selection and record policy |
| `ObsidianVault/09_Archive/migration-conflicts/2026-05-24/Obsidian-Vault/01-daily/*.md` | old direct daily evidence; current workflow/record authority is Bucky Context Packs |
| `ObsidianVault/09_Archive/migration-conflicts/2026-05-24/Obsidian-Vault/01_Projects/brain/*.md` | old direct brain/profile docs; current user terrain and preferences must live in Bucky packs |
| `ObsidianVault/09_Archive/migration-conflicts/2026-05-24/Obsidian-Vault/03_Prompts/templates/*.md` | old direct prompt templates; current template/record behavior is governed by Bucky record policy |
| `ObsidianVault/09_Archive/migration-conflicts/2026-05-24/Obsidian-Vault/05_Insights/*.md` | old direct insight notes; reference-only unless compressed into a Context Pack |
| `ObsidianVault/09_Archive/migration-conflicts/2026-05-24/Obsidian-Vault/05_Logs/daily/*.md` | old direct daily evidence; current record authority is Bucky record policy |
| `ObsidianVault/09_Archive/migration-conflicts/2026-05-24/Obsidian-Vault/07_Archive/sessions/*.md` | old direct session evidence; current session authority is Bucky record policy |
| `ObsidianVault/09_Archive/migration-conflicts/2026-05-24/Obsidian-Vault/infranodus/gap-analysis/*.md` | old direct graph gap-analysis evidence; current graph work is governed by Graphify framework docs |
| `ObsidianVault/09_Archive/migration-conflicts/2026-05-24/Obsidian-Vault/sessions/*.md` | old direct session memories; current authority is Bucky record policy and Context Packs |
| `ObsidianVault/09_Archive/migration-conflicts/2026-05-24/Obsidian-Vault/wiki/*.md` | old direct wiki pages; reference-only unless distilled into current framework docs or Context Packs |
| `ObsidianVault/09_Archive/migration-conflicts/2026-05-24/OBSIDIAN-SECOND/raw/jh-mobile-second-brain/**` | old direct mobile second-brain data; archive/reference-only unless targeted ingestion is requested |
| `ObsidianVault/09_Archive/migration-check-2026-05-25.md` | migration evidence only; current status is this audit plus inventory/residue reports |
| `ObsidianVault/09_Archive/gdrive-archive/**` | imported from shared Google Drive legacy system (00_SYSTEM_2026-05-23, daily-reports-legacy, root-* files); archive-only, not current instruction authority; all gdrive-archive files are historical evidence only |
| `ObsidianVault/09_Archive/bucky-context-archive/**` | auto-memory snapshots and session archives; archive-only, not current instruction authority; content superseded by current Vault memory and session records |
| `ObsidianVault/09_Archive/migration-conflicts/2026-05-24/Obsidian-Vault/infranodus/**` | old InfraNodus graph snapshots; archive/reference-only unless targeted graph analysis is requested |
| `ObsidianVault/09_Archive/migration-conflicts/2026-05-24/_organized/superseded/Obsidian-Vault/infranodus/**` | old InfraNodus graph snapshots; archive/reference-only |
| `ObsidianVault/09_Archive/migration-conflicts/2026-05-24/Obsidian-Vault/output/research-questions/**` | old research question outputs; archive/reference-only, covered by current InfraNodus and knowledge graph workflow |

## Runtime Default Path Remediation

| Candidate | Why it matters | Handling |
|---|---|---|
| Runtime scripts with default `JH-SHARED` reads | Could silently keep legacy folders as active context | patched 2026-05-30: dispatcher/reviewer/daily/preflight/global-Claude-sync now default to ObsidianVault/Bucky paths; legacy reads require explicit `BUCKY_ENABLE_LEGACY_CONTEXT=1` |
| Legacy migration scripts with hardcoded old roots | Could copy/scan old systems outside a current Bucky packet | patched 2026-05-30: migration writes require `BUCKY_ALLOW_LEGACY_MIGRATION=1`; crosscheck writes require `BUCKY_ALLOW_LEGACY_SCAN=1` or `--dry-run` |

## Automated Residue Scan

| Tool | Report | Current result | Next handling |
|---|---|---|---|
| `scripts/legacy_residue_scanner.py` | `ObsidianVault/00_System/LEGACY_RESIDUE_SCAN_2026-05-30.md` | 0 review candidates, 657 allowed archive/superseded mentions | current operating docs/runtime scope has no active legacy-authority findings; keep using this report as the Bucky cleanup gate |
| `scripts/legacy_instruction_inventory.py` | `ObsidianVault/00_System/LEGACY_INSTRUCTION_INVENTORY_2026-05-30.md` | 347 instruction-like candidates, 316 audit-mentioned candidates, 0 candidate-review candidates, 0 high-priority review candidates, 0 secret-review-before-read candidates, 31 secret-audit-mentioned candidates | every instruction-like candidate found by the inventory is now tracked by audit; secret-like candidates remain quarantined until targeted redaction review |
| secret review policy | `ObsidianVault/00_System/LEGACY_SECRET_REVIEW_POLICY_2026-05-30.md` | active | Bucky/Claude Code/Codex must use targeted redaction review before promoting any secret-like archive material |
| `scripts/legacy_secret_manifest.py` | `ObsidianVault/00_System/LEGACY_SECRET_MANIFEST_2026-05-30.md` | 31 secret-like candidates, 0 secret-review-before-read, 31 secret-audit-mentioned | value-free manifest records only path, pattern class, and line numbers; no secret values or matched line text are written |
| `scripts/legacy_secret_decision_register.py` | `ObsidianVault/00_System/LEGACY_SECRET_DECISION_REGISTER_2026-05-30.md` | 31 candidates accounted: 9 archive-only, 20 covered-quarantined, 2 partial-promoted-quarantined, 0 pending-targeted-redaction | value-free register records handling decisions without secret values, line text, or excerpts |

## Rules For Future Migration Passes

1. Do not make legacy folders authoritative again.
2. Promote only compressed, current-system rules into `06_Context_Packs`, `00_System`, or `05_Frameworks`.
3. Preserve source paths in each promoted pack for traceability.
4. Run a targeted secret scan on any source path before copying examples; follow `ObsidianVault/00_System/LEGACY_SECRET_REVIEW_POLICY_2026-05-30.md` for secret-like archive candidates.
5. Treat API pricing/free-tier catalogs as candidate lists only; verify with official docs at decision time.
6. If a file is mojibake or duplicated, do not repair by guessing. Find a readable duplicate or record it as archive-only until verified.
7. Re-run `python -X utf8 scripts/legacy_residue_scanner.py --report ObsidianVault/00_System/LEGACY_RESIDUE_SCAN_2026-05-30.md` after each cleanup pass.

[[bucky-system-hub]]
