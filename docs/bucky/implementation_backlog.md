# Bucky 세컨드 브레인 — 구현 백로그 (implementation_backlog)

- 작성일: 2026-07-11 (Stage 14, 문서 전용 — 코드 무변경)
- 역할: **스펙 P0/P1 → V3 Stage 번호 매핑 테이블** (플랜 포지셔닝 결정 — [ADR-0002](../adr/ADR-0002-v3-single-track.md))
- 플랜 정본: `C:\Users\user1\.claude\plans\foamy-churning-swing.md` (세컨드브레인 Stage 13~21) / V3: `docs/BUCKY_OS_V3_MIGRATION_PLAN.md`
- 실행 규율: 모든 Stage = 1세션 크기. 커밋 단위 = Stage 단위, 커밋/푸시는 사용자 승인 후. Phase 경계마다 Codex 독립 검수 게이트

---

## 1. 단계 총괄표 (승인 플랜 전사)

| 순서 | Stage | Phase | 이름 | 코드 변경 | 스펙 P0 | 상태 |
|---|---|---|---|---|---|---|
| 0 | 9 | 기존 | Codex 검수 게이트 #2 — 선행 필수 | 없음 | — | ✅ 통과 (07-11 재검수, 필수수정 6건 이행 dd48547) |
| 1 | 13 | A | 문서 1차: current_state_audit + gap_analysis + assumptions(§26) | 없음 | P0-1 | ✅ 완료 (07-11, 1e14b7d) |
| 2 | 14 | A | 문서 2차: target_architecture + backlog + ADR-0001~4 + AGENTS_CANONICAL 복구 | 없음 | P0-1 | 본 문서 |
| — | G3 | 게이트 | Codex 문서 검수 (경량) | — | — | ✅ 통과 (07-11 — 지적 5건 수정 1660548, 수정분 재확인은 사용자 결정으로 생략) |
| 3 | 10 | B | usage_ledger (V3 Stage 10 축소판) + gbrain 토큰 하드코딩 핫픽스 | 신규 위주 | P0-7 | ✅ 완료 (07-11, 0455040 — 셀프테스트 6항목 + oracle 회귀 80 PASS) |
| 4 | 15 | B | 이벤트 엔벨로프(event_log.py) + model_decision 방출 준비 | 신규 위주 | P0-2,8 | ✅ 완료 (07-11, 8a88256 — 테스트 14 + 셀프테스트 7 + 회귀 92·oracle 80 무손상, 실경로 E2E 확인) |
| 5 | 16 | B | Task/Goal/Project 레지스트리 최소판 | 신규 위주 | P0-3 | ✅ 완료 (07-12, f70c430 — 테스트 128건·oracle 80 무손상, 3-lens 검수 통과, projects.yaml 추적 확인) |
| 6 | 17 | B | worker 실행 배선 (echo 스텁→어댑터, 플래그 기본 off) | 기존 1파일 | P0-5,11 | ✅ 완료 (07-12, a79994d — worker 14건·oracle 84 PASS·unittest 128건 OK·격리 실경로 E2E, 실동작은 claude_code뿐) |
| — | G4 | 게이트 | Codex 검수 #3 (Phase B 일괄) | — | — | ✅ 통과 (07-12 — 조건부 통과 후 필수수정 2건 이행 `0c43835`: model_decision 방출 시점 수정 + W15 회귀, worker 15·oracle 85·unittest 128 OK, 재검수는 사용자 결정으로 생략. 결과: `docs/CODEX_REVIEW_REQUEST_G4.md` §5) |
| 7 | 18 | C | policy_rules.yaml + policy_engine.py (순수 함수, 미배선) | 신규만 | P0-6 | ✅ 완료 (07-12, 72242a6 — 신규 테스트 18건·unittest 146 OK·oracle 85 무손상, dispatch 폴백 정책 A안 명문화 포함) |
| 8 | 19 | C | 정책 배선 shadow 모드 + 예산 경고 (기존 승인 3종 재사용) | 기존 수정 | P0-6,7 | ✅ 완료 (07-12, ab68c09 — worker 21건(W17 off-shadow 바이트 동일 회귀 포함)·oracle 91 PASS·unittest 146 무손상. shadow 기본, 차단 없음. enforce는 별도 결정, 승인 신설 없음) |
| — | G5 | 게이트 | Codex 검수 #4 (Phase C) | — | — | ✅ 통과 (07-12 — 조건부 통과 후 필수수정 2건 이행 `248eb47`: task_tiers에 default 명시 등록(T3, 사용자 A안) + 포함관계 회귀 테스트, unittest 147 OK·oracle 91 PASS. Codex 재검증 PASS로 완전 통과 성립. 결과: `docs/CODEX_REVIEW_REQUEST_G5.md` §5·§6. 비차단 권고 4건은 §5.3 백로그) |
| 9 | 20 | D | 메모리 출처 전파 (Stage 12 선행 축소판) | 기존 2파일 | P0-4 | ✅ 완료 (07-13, ad78af5 — 신규 테스트 8건·01_RAW 해시 불변 assert, sidecar `data/memory/processed_index.jsonl` 채택(오픈 퀘스천 3 확정)) |
| 10 | 21 | E | 최소 대시보드 (static-JSON 패턴 확장 + org-structure 동적화) | 신규 위주 | P0-10 | ✅ 완료 (07-13, 15e65b8 + 산출물 772e28b — 신규 테스트 13건, 오라클 읽기전용(mode=ro) 집계. org-structure는 기존 agent-tree 유지 + 실행인프라 섹션 추가(사용자 A안), 보호 3종 무접촉) |
| — | G6 | 게이트 | Codex 검수 #5 + P0 완료 판정 (스펙 §20 Story 5/6/7 대조) | — | — | 🔄 진행 중 (07-13 — 검수 결과: **코드 조건부 통과 / P0 완료 판정 기각**. 필수수정 4건 중 ①범위 결정=**A안 사용자 승인**(§2.1) ②병합 provenance ③sidecar 실패 격리 ④process_batch 통합 테스트 → ②③④ 이행 완료, **재검수 대기**. 결과: `docs/CODEX_REVIEW_REQUEST_G6.md` §6) |

## 2. 스펙 P0 → Stage 매핑

| 스펙 P0 | 내용 | 해소 Stage |
|---|---|---|
| P0-1 | 현재 상태 조사·문서화 (`docs/bucky/*` + `docs/adr/`) | 13·14 |
| P0-2 | 이벤트 기록 | 15 |
| P0-3 | 통합 작업 레지스트리 | 16 (분류 축만 — 작업 정본은 오라클 큐 불변) |
| P0-4 | 메모리 출처 추적 | 20 (Stage 12 선행 축소판) |
| P0-5 | 모델 게이트웨이 | 17 (인터페이스 완성 — claude_code만 실동작, 과대 보고 금지) |
| P0-6 | 승인 정책 | 18·19 (shadow까지 — enforce는 별도 결정) |
| P0-7 | 비용 원장·예산 | 10 (원장) · 19 (경고) |
| P0-8 | model_decision 감사 | 15 (준비) · 17 (배선) |
| P0-9 | 테스트 하네스 | 전용 Stage 없음 — 기존 `tests/` unittest + `oracle` 회귀 스위트에 Stage 13~21이 각각 테스트 추가. **부분 충족**: `unittest discover` 기준 기존 실패 32건(discord 의존 모듈 등, Stage 13~21과 무관)이 남아 하네스가 green이 아니다 → 정리는 P1-7 |
| P0-10 | 최소 대시보드 | 21 |
| P0-11 | 실행 결선 | 17 |

> P0-9 행은 G6 검수(2026-07-13)에서 Codex가 **매핑표 누락**으로 지적해 추가했다. 스펙 원문은 `P0-N` 번호를 쓰지 않고 「P0 — 기반 안정화」 아래 1~11 순번 목록으로만 표기하며, 9번이 「테스트 하네스」다.

## 2.1 P0 범위 확정 — 2026-07-13 사용자 승인 (A안)

**결정**: P0의 완료 기준을 **배관(instrumentation·인터페이스·shadow 관측)까지**로 공식 축소하고, 스펙 §20 Story 5·6·7의 **행동 조건**은 P1로 이월한다.

- **근거**: 원 플랜 오픈 퀘스천 1(「정책 enforce 전환 시점 — 이번 범위는 shadow까지」)과 일치한다. 행동 조건(자동 실행·승인 차단)은 실행 위험이 높아 shadow 운영 관측과 별도 승인 게이트를 거치는 것이 안전하다.
- **경위**: G6 Codex 검수(#5)가 「배관 완료 = P0 완료」 포지션을 **기각**하고 "구현하거나, 사용자 승인으로 스펙/P0 범위를 공식 변경하라"고 요구했다. 사용자가 후자(A안)를 선택했다.
- **효력**: 이 결정으로 아래 항목은 **P0 미충족이 아니라 P0 범위 밖**이다. 롤백 스위치(`features.policy_enforcement: off`)는 켜진 채로 유지한다.

| 스펙 Story | 이월되는 행동 조건 | 이월처 |
|---|---|---|
| Story 5 | 사실/추론의 기계적 구분 축 | P1-8 |
| Story 5 | 정정(supersedes)의 검색·인덱스 반영 | P1-9 |
| Story 6 | T0/T1 정책 기반 **자동 실행** (shadow→enforce 전환) | P1-10 |
| Story 6 | T3 실행 전 **승인 요청·차단** | P1-10 |
| Story 6 | 기간·예산·범위 **묶음 승인** | P1-11 |
| Story 7 | **프로젝트별 예산** (현재는 월 전역 임계만) | P1-12 |
| Story 7 | 예산 임계치 **차단** (현재는 경고만) | 보류 §4 (기존 항목) |

## 3. P1 백로그 (P0 완료·G6 통과 후 착수 후보 — 착수 전 사용자 승인)

| # | 항목 | 근거 갭 | 비고 |
|---|---|---|---|
| P1-1 | 크로스 소스 중복탐지 | G15 | distiller 3중 dedup은 단일 소스 내 — 소스 간 통합 필요 |
| P1-2 | 재개 큐 (중단 태스크 이어가기) | — | 스펙 시나리오 A(뒤섞인 요청) 완전 충족용 |
| P1-3 | 우선순위 엔진 | — | 현재는 사용자 수동 우선순위 |
| P1-4 | gbrain 인덱스 경로 불일치 해소 (생산 `data/` vs 소비 `memory/`) | G14 | 파생 캐시 계층 — 정본 원칙(P-2) 위반 아님, 배선 결함 |
| P1-5 | 큐 retry·DLQ | G6 | 오라클 큐 상태 전이표 확장 |
| P1-6 | 백업 정책 문서화 | assumptions `backup_policy: 미문서화` | 볼트·SQLite·usage 원장 복구 절차 |
| P1-7 | 테스트 하네스 green화 | P0-9 | `unittest discover` 기존 실패 32건 정리 (discord 등 선택적 의존성 가드) |
| P1-8 | 사실/추론 구분 축 | §2.1 Story 5 | 현재 `confidence` 숫자만 있음 — 기계적 구분 필드 필요 |
| P1-9 | supersedes의 검색 반영 | §2.1 Story 5 | 필드는 있으나 검색·인덱스 미배선. 노드 버저닝(보류 §4)과 함께 재평가 |
| P1-10 | 정책 enforce 전환 (자동 실행 + 승인 차단) | §2.1 Story 6 | **위험**: 실행 경로 변경. shadow 오판정 관측 + 별도 승인 게이트 선행 (오픈 퀘스천 1) |
| P1-11 | 묶음 승인 (기간·예산·범위) | §2.1 Story 6 | 미구현. P1-10 이후 |
| P1-12 | 프로젝트별 예산 | §2.1 Story 7 | 현재 월 전역 임계(`budget.monthly_warn_usd`)만 존재 |

## 4. 보류 (필요성 재평가 전 착수 금지)

| 항목 | 근거 갭 | 재평가 트리거 |
|---|---|---|
| 노드 버저닝 | G13 | supersedes(Stage 20) 운영 관측 후 |
| 중앙 스케줄 레지스트리 | G19 | Task Scheduler 7종 git 밖 수동 관리가 현행 — Stage 21에서 읽기전용 표시만 검토 |
| 예산 강제(차단) | G17 후반 | shadow 운영 + 오판정 관측 + 사용자 승인 (오픈 퀘스천 1) |
| LangGraph | — | [`target_architecture.md`](target_architecture.md) §5 채택 기준 전부 충족 시 |

## 5. 오픈 퀘스천 (해당 Stage 착수 전 사용자 확정 — 플랜 정본 상속)

1. 정책 enforce 전환 시점 — 권고: 이번 범위는 shadow까지 (Stage 19 착수 전 재확인)
2. 데이터 위치·git 추적 — ✅ 확정 (07-11 사용자 A안): 원장류는 repo `data/`+`05_Logs/`, `data/usage/`는 .gitignore (0455040 반영)
3. 01_RAW #processed 방식 — ✅ 확정 (07-12 사용자 A안): sidecar 인덱스 `data/memory/processed_index.jsonl` (01_RAW 불변성 보존), LIBRARIAN_RULES·CLAUDE.md 개정 완료 (ad78af5 반영)
