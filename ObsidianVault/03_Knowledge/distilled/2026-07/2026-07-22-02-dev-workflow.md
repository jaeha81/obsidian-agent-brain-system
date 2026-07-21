---
source: 02_dev_workflow.md
source_type: unknown
date: 2026-07-22
original_file: "D:\ai프로젝트\obsidian-agent-brain-system\ObsidianVault\01_RAW\memories\02_dev_workflow.md"
source_conversation_id: 
source_file: "D:\ai프로젝트\obsidian-agent-brain-system\ObsidianVault\01_RAW\memories\02_dev_workflow.md"
topics: [개발-워크플로우, claude-code, tmux, 승인-프로세스, 보안원칙]
related: ["[[03_tech_stack]]", "[[03_사업_철학_의사결정]]"]
confidence: 0.9
priority: 6.5
category_tags: [category/개발, category/AI-에이전트]
distilled_at: 2026-07-22 01:35
supersedes: 
valid_until: 
last_verified: 
tags: [ai-distilled, source/unknown, category/개발, category/AI-에이전트, 개발-워크플로우, claude-code, tmux, 승인-프로세스, 보안원칙]
---

> 재하의 표준 개발 워크플로우 — research.md → plan.md → 명시적 승인("구현해") → 구현. 승인 게이트, tmux 5분할 에이전트 레이아웃, 보안 원칙을 정리.

## 핵심 인사이트

- 표준 프로세스: research.md → plan.md(설계·의사코드·트레이드오프) → 재하의 명시적 승인("구현해") → 구현. **승인 전 실코드 생성 금지**(설계·의사코드·스니펫은 승인 없이 제공 가능).
- 작업 규모별 처리: 소=즉시 실행, 중=계획→승인, 대=리서치→계획→승인. **보안·결제·인증은 규모 무관 항상 계획→승인**.
- 계획 문서 형식(중·대규모): 구현 방식 / 수정 파일 / Before·After 스니펫 / 트레이드오프 / Todo + 마지막에 "아직 코드를 수정하지 않았습니다" 명시.
- tmux 5분할 에이전트 레이아웃: RESEARCH(조사) / PLAN(설계) / FRONTEND / BACKEND / QA — 복잡한 구현은 병렬 실행.
- 보안 원칙: 시크릿·API키·PII 감지 시 즉시 중단, **.env 파일 채팅 업로드 금지**(과거 실제 보안 인시던트로 키 로테이션 경험 있음), 자동결제엔 사용자 확인 필수.
- Codex Goal Mode: 긴 작업을 "목표→실행→검증→기록→개선" 루프로 관리. 목표는 측정 가능한 기준·종료 조건·검증 방법 포함, 기록은 `sessions/codex-goal-mode-YYYYMMDD.md`.
- Claude Code 버전 기록(2026-04 시점): 안전 v2.1.34, 캐시 비효율 버그 v2.1.69~91(`--continue -p` 사용 시) — 시점 지난 정보, 현재 판단에 그대로 쓰지 말 것.

## 연결 개념

- [[03_tech_stack]]
- [[03_사업_철학_의사결정]]

## 지식 그래프 링크 🟡 MEDIUM

- [[2026-07-22-03-tech-stack]]
- [[2026-07-22-03-사업-철학-의사결정]]
- [[2026-07-22-04-jh-keanu]]

## 실행 가능한 태스크

- (실행 태스크 없음)

## 태그

#source/unknown #category/개발 #category/AI-에이전트 #개발-워크플로우 #claude-code #tmux #승인-프로세스 #보안원칙

---
*수동 정제: Claude Code 세션 (2026-07-22) — API 크레딧 부족으로 knowledge_distiller.py 재시도 대신 직접 정제. 원본: `02_dev_workflow.md` — 소스: unknown*
