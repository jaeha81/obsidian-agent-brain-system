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
| 6 | 17 | B | worker 실행 배선 (echo 스텁→어댑터, 플래그 기본 off) | 기존 1파일 | P0-5,11 | 대기 |
| — | G4 | 게이트 | Codex 검수 #3 (Phase B 일괄) | — | — | 대기 |
| 7 | 18 | C | policy_rules.yaml + policy_engine.py (순수 함수, 미배선) | 신규만 | P0-6 | 대기 |
| 8 | 19 | C | 정책 배선 shadow 모드 + 예산 경고 (기존 승인 3종 재사용) | 기존 수정 | P0-6,7 | 대기 |
| — | G5 | 게이트 | Codex 검수 #4 (Phase C) | — | — | 대기 |
| 9 | 20 | D | 메모리 출처 전파 (Stage 12 선행 축소판) | 기존 2파일 | P0-4 | 대기 |
| 10 | 21 | E | 최소 대시보드 (static-JSON 패턴 확장 + org-structure 동적화) | 신규 위주 | P0-10 | 대기 |
| — | G6 | 게이트 | Codex 검수 #5 + P0 완료 판정 (스펙 §20 Story 5/6/7 대조) | — | — | 대기 |

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
| P0-10 | 최소 대시보드 | 21 |
| P0-11 | 실행 결선 | 17 |

## 3. P1 백로그 (P0 완료·G6 통과 후 착수 후보 — 착수 전 사용자 승인)

| # | 항목 | 근거 갭 | 비고 |
|---|---|---|---|
| P1-1 | 크로스 소스 중복탐지 | G15 | distiller 3중 dedup은 단일 소스 내 — 소스 간 통합 필요 |
| P1-2 | 재개 큐 (중단 태스크 이어가기) | — | 스펙 시나리오 A(뒤섞인 요청) 완전 충족용 |
| P1-3 | 우선순위 엔진 | — | 현재는 사용자 수동 우선순위 |
| P1-4 | gbrain 인덱스 경로 불일치 해소 (생산 `data/` vs 소비 `memory/`) | G14 | 파생 캐시 계층 — 정본 원칙(P-2) 위반 아님, 배선 결함 |
| P1-5 | 큐 retry·DLQ | G6 | 오라클 큐 상태 전이표 확장 |
| P1-6 | 백업 정책 문서화 | assumptions `backup_policy: 미문서화` | 볼트·SQLite·usage 원장 복구 절차 |

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
3. 01_RAW #processed 방식 — 권고: sidecar 인덱스 + LIBRARIAN_RULES 개정 승인 (Stage 20 착수 전 확정)
