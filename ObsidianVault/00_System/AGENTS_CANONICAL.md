---
type: agent-reference
title: AGENTS_CANONICAL — 에이전트 정본 참조 허브 (사람용 파생 뷰)
status: active
created: 2026-07-11
---

# AGENTS_CANONICAL — 에이전트 정본 참조 허브

> **이 문서는 사람용 파생 뷰다. 그 자체가 정본이 아니다.**
> - **실행 노드 등록부의 기계 정본 = `oracle/core/agents.yaml`** (api_server가 직접 읽는 파일 — 노드 추가·변경은 반드시 거기서)
> - 역할·권한 경계의 정본 = `ObsidianVault/03_Projects/agents/roles.md` (status: canonical)
> - 라우팅·스킬 매핑의 정본 = `ObsidianVault/00_System/ROUTING_RULES.md`
> - 본 문서와 정본이 어긋나면 **정본이 이긴다.** 여기서는 요약과 링크만 유지한다.
>
> (복구 이력: 본 파일은 `AGENTS.md`·`ROUTING_RULES.md`가 참조해 왔으나 실재하지 않던 깨진 참조를 2026-07-11 Stage 14에서 복구한 것이다.)

## 1. 실행 노드 (기계 정본: `oracle/core/agents.yaml` — 아래는 07-11 스냅샷)

| id | type | location | role | status |
|---|---|---|---|---|
| bucky-main | core | oracle | central-brain | active |
| home-pc-agent | local | home-pc | main-workstation | active |
| office-pc-agent | local | office-pc | office-client | standby |
| laptop-agent | local | laptop | mobile-client | standby |
| interior-estimate-ai | commercial | oracle | estimate-generator | development |

## 2. 역할 에이전트 — 권한·금지 요약 (정본: `roles.md` + 각 정의 파일)

| 에이전트 | 역할 | 핵심 금지 | 정의 파일 |
|---|---|---|---|
| User (JH) | 방향·우선순위·승인·최종 결정 소유 | — | `03_Projects/agents/roles.md` |
| Bucky | 오케스트레이터·지시 관리자 — 분류, Context Pack 선택, 패킷 발행, 결과 취합 | 직접 구현 없음. 레거시 폴더를 정본화하지 않음 | `03_Projects/agents/bucky.md` |
| Claude Code | 구현·운영 — 코드/파일 수정, 스크립트 실행, 증거 기록 | 위험 변경 자체 승인 금지. 명시 승인 없는 commit/push/삭제/이동/reset/마이그레이션 금지 | `roles.md` + 저장소 `CLAUDE.md` |
| Codex | 독립 검수 — 구현 결과·리스크·테스트·AI-slop 리뷰, **사용자 직보** | Claude 판단 자동 추종 금지. 명시 요청 없는 파일 수정·커밋 금지 | `03_Projects/agents/codex-instructions.md` |
| Charlie | 독립 시스템 감사 — 결정적·로컬·읽기 전용 점검, 드리프트·부패 보고 | 오케스트레이션·자동 수정·git 쓰기 금지 | `03_Projects/agents/charlie.md` |
| Hermes | Bucky 내부 추론 백엔드 (선택적) | 사용자 대면 권한 없음 | `roles.md` |

행위별 권한 매트릭스(구현/리뷰/커밋/삭제/규칙 변경)는 `roles.md`의 Role Matrix가 정본 — 여기 중복 전재하지 않는다.

## 3. 인계 프로토콜 (정본 링크)

- **Bucky → Claude Code**: Bucky 패킷 (project/goal/scope/constraints/verification/done_when …) — 형식 정본: `C:\Users\user1\.claude\CLAUDE.md` "Bucky Packet Format"
- **Claude Code → Codex**: 간결·증거 기반 핸드오프. Codex는 독립 검수 후 사용자 직보, 사용자 지시 후에만 Claude가 수정 착수
- **세션 간**: `C:\Users\user1\.claude\handoff\latest-handoff.md` (SessionStart 훅 자동 주입)
- **완료 보고**: 증거 강제 형식 (작업/증거/실행 전/실행 후/미완료) — 정본: 전역 `CLAUDE.md`

## 4. 스킬-에이전트 매핑

`ROUTING_RULES.md` "스킬-에이전트 매핑" 절이 정본이며 본 문서의 권한 정의(§2)와 연동된다 — 담당 외 에이전트의 스킬 무단 실행 금지.

## 5. 예정 변경

- Stage 18: §2의 산문 권한·리스크 규칙(T0~T3)이 `config/policy_rules.yaml`로 코드화됨 (shadow 우선 — `docs/adr/ADR-0004-policy-shadow-first.md`). 코드화 후에도 본 문서는 사람용 뷰로 유지.
- Stage 21: §1 스냅샷 표가 대시보드(JSON 동적화)로 대체 후보 — 그 전까지 agents.yaml 변경 시 본 표를 수동 동기화.
