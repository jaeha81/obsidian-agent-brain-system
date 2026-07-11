# Bucky 세컨드 브레인 — 갭 분석 (gap_analysis)

- 작성일: 2026-07-11 (Stage 13, 문서 전용 — 코드 무변경)
- 스펙 근거: `ObsidianVault/00_UPGRADE/BUCKY_SECOND_BRAIN_EVOLUTION_SPEC_v0.1_KR.md` §0.2
- 입력: [`current_state_audit.md`](current_state_audit.md) §3 공백 22건 (탐색 에이전트 3개 실측, 2026-07-11)
- 처분 기준: **해소 Stage** (플랜 Stage 13~21에 배정) / **P1 백로그** (P0 이후, Stage 14 `implementation_backlog.md`에 수록) / **보류** (필요성 재평가 전 착수 금지)

---

## 1. 3분류 총괄

| 분류 | 건수 | 갭 번호 |
|---|---|---|
| 해소 Stage 배정 | 15 | G1~G5, G7~G12, G16(=G2), G18, G20~G22 |
| P1 백로그 | 4 | G6, G14, G15, G17(강제 부분) |
| 보류 | 3 | G13, G17(경고까지는 Stage 19), G19 |

> G17(예산)은 **분할 처분**: 경고 이벤트까지 Stage 19 해소, "강제(차단)"는 enforce 전환 결정(플랜 오픈 퀘스천 1) 이후 — 그 전까지 보류.

---

## 2. 코어 갭 (7건)

| # | 갭 | 처분 | 근거·비고 |
|---|---|---|---|
| G1 | usage 사용량 원장 부재 (cli-tools.jsonl에 토큰·비용 없음) | **Stage 10** | `scripts/core/usage_ledger.py` + `data/usage/YYYY-MM.jsonl`. 계측 = adapter run() 래퍼 + bucky_client record() 1줄 |
| G2 | 정책 엔진 부재 (리스크 규칙이 산문 문서에만 존재) | **Stage 18 → 19** | 18 = 순수 함수 엔진(미배선), 19 = shadow 배선 |
| G3 | 통합 이벤트 봉투 부재 — 로그 3분산 | **Stage 15** | `scripts/core/event_log.py` → `05_Logs/bucky-events.jsonl` 단일 append-only (큐 아님, 10_AgentBus 무접촉) |
| G4 | model_decision 미방출 (explain()은 존재하나 기록 안 됨) | **Stage 15 → 17** | 15 = emit 준비, 17 = worker 디스패치 시 배선 |
| G5 | worker 실행 미결선 (echo 스텁) | **Stage 17** | `features.worker_adapter_dispatch: false` 기본 off, claude_code만 실동작 |
| G6 | 큐 retry·DLQ 부재 | **P1 백로그** | 플랜 Non-goals 명시. 오라클 큐 상태 전이표는 이미 안정 |
| G7 | 승인 경로 이중화 (파일큐/CLI/Discord 병립, 정책과 미연결) | **Stage 19** | 신규 승인 메커니즘 신설 금지 — 기존 `pending_approval/` + `approve_task.py` + `!approve` 재사용이 통합 접점 |

## 3. 메모리 갭 (8건)

| # | 갭 | 처분 | 근거·비고 |
|---|---|---|---|
| G8 | 불변 이벤트 원장 부재 | **Stage 15** | G3과 동일 산출물(bucky-events.jsonl)로 해소 |
| G9 | valid_until·감쇠 부재 | **Stage 20 (부분)** | optional 필드(`valid_until`/`last_verified`)까지만. 감쇠 로직은 보류(스펙 P0 아님) |
| G10 | supersedes 기계관계 부재 | **Stage 20** | 증류 노트 frontmatter optional 필드 |
| G11 | #processed 자동화 부재 | **Stage 20** | 01_RAW 무수정 — sidecar `data/memory/processed_index.jsonl` (오픈 퀘스천 3 권고안) |
| G12 | origin ID 전파 부재 (conversation_id가 증류 후 단절) | **Stage 20** | distiller에서 `source_conversation_id`/`source_file` 전파. wiki_gate는 통과만 |
| G13 | 노드 버저닝 부재 | **보류** | 스펙 P0 아님. supersedes(G10) 운영 관측 후 필요성 재평가 |
| G14 | 인덱스 배선 불일치 (생산 `data/` vs 소비 `memory/`) | **P1 백로그** | 플랜 Non-goals 명시 (gbrain 인덱스 경로 불일치) |
| G15 | 크로스 소스 중복탐지 부재 (distiller 3중 dedup은 단일 소스 내) | **P1 백로그** | 플랜 P1 목록의 "중복탐지" 항목 |

## 4. 대시보드·정책 갭 (7건)

| # | 갭 | 처분 | 근거·비고 |
|---|---|---|---|
| G16 | 정책 엔진 코드 부재 | **Stage 18** | **G2와 동일 사안** (실측 도메인이 달라 중복 계상됨) — 동일 산출물로 해소 |
| G17 | 예산 강제 부재 | **Stage 19 (경고) / 보류 (강제)** | 19 = usage 월 합계 임계 초과 시 경고 이벤트. 차단(enforce)은 오픈 퀘스천 1 — shadow 관측 + 사용자 승인 후 별도 결정 |
| G18 | 실시간 조직도 부재 (org-structure 하드코딩) | **Stage 21** | JSON 로드로 동적화. 보호 3종(bucky-os/bucky-agent-os/ai-usage) 불가침 |
| G19 | 중앙 스케줄 레지스트리 부재 (Task Scheduler 7종 git 밖 분산) | **보류** | 플랜 범위 외. 예약작업은 git 밖 수동 재등록 관리가 현행 운영 방식 — Stage 21에서 읽기전용 표시만 검토 |
| G20 | `docs/bucky/`·`docs/adr/` 문서 계층 부재 | **Stage 13~14** | 본 문서로 해소 시작. 14에서 target_architecture/backlog/ADR-0001~4 완성 |
| G21 | AGENTS_CANONICAL 깨진 참조 | **Stage 14** | 기계 정본 = `oracle/core/agents.yaml` 헤더 명시, 사람용 파생 뷰로 복구 |
| G22 | 리스크 룰 코드화 부재 (`ROUTING_RULES.md`·`bucky.md` 산문) | **Stage 18** | `config/policy_rules.yaml` T0~T3 데이터화. routing_policy.yaml과 중복 키 금지 |

---

## 5. 분류 외 항목 (22건에 미포함)

| 항목 | 성격 | 처분 |
|---|---|---|
| gbrain 토큰 하드코딩 (`scripts/gbrain_mcp_proxy.py:14`) | 보안 발견 (갭이 아니라 결함) | **Stage 10 동반 핫픽스** — [`current_state_audit.md`](current_state_audit.md) §4 |
| Codex 게이트 #2 필수수정 6건 | 기존 코드 결함 (V3 Stage 3~8 산출물) | 게이트 절차 — 사용자 승인 후 이행 → Codex 재검수. `docs/CODEX_REVIEW_REQUEST_PHASE_2.md` |

## 6. 원칙 확인 (갭 해소 시 불변 조건)

- **볼트 일원화**: 어떤 갭 해소도 파생 저장소(gbrain DB·인덱스·bucky_memory)를 정본으로 승격하지 않는다. 지식 정본은 ObsidianVault `03_Knowledge/` 하나다 ([`current_state_audit.md`](current_state_audit.md) §2, 07-11 사용자 확정).
- **큐 단일 정본**: 작업 상태 정본은 oracle SQLite 큐. `10_AgentBus` 파일 큐 신설 영구 금지.
- **기존 재사용 우선**: 승인(G7)·모니터링(G17)·대시보드(G18)는 기존 메커니즘 확장으로만 해소 — 병행 신설 금지.
