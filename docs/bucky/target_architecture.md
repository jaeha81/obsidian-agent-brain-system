# Bucky 세컨드 브레인 — 목표 아키텍처 (target_architecture)

- 작성일: 2026-07-11 (Stage 14, 문서 전용 — 코드 무변경)
- 스펙 근거: `ObsidianVault/00_UPGRADE/BUCKY_SECOND_BRAIN_EVOLUTION_SPEC_v0.1_KR.md` §0.2
- 입력: [`current_state_audit.md`](current_state_audit.md) · [`gap_analysis.md`](gap_analysis.md) · [`assumptions.md`](assumptions.md)
- 원칙: **신규 시스템 신설이 아니라 V3 위에 얹는 갭 기반 확장** ([ADR-0002](../adr/ADR-0002-v3-single-track.md))

---

## 1. 설계 불변 원칙 (정본 3원칙)

| # | 원칙 | 정본 | 파생(캐시) | ADR |
|---|---|---|---|---|
| P-1 | 작업 상태 정본은 하나 | oracle SQLite 큐 | `10_AgentBus` 기존 파일들(운영 워크플로, 정본 아님) | [ADR-0001](../adr/ADR-0001-queue-canonical-oracle.md) |
| P-2 | 지식 정본은 하나의 볼트 | ObsidianVault `03_Knowledge/` (SoT) | gbrain DB · oracle obsidian_index · bucky_memory · vault_rag 임베딩 | [ADR-0005](../adr/ADR-0005-vault-single-sot.md) |
| P-3 | 이벤트는 관측 로그, 버스 아님 | `05_Logs/bucky-events.jsonl` (append-only) | — (구독·라우팅 없음) | [ADR-0003](../adr/ADR-0003-event-log-single-appendonly.md) |

공통 규율: 기존 메커니즘 재사용 우선(승인·모니터링·대시보드), 배선은 기능 플래그 기본 off, 계측·기록 실패는 실행 비차단(try/except 격리), 정책은 shadow 우선([ADR-0004](../adr/ADR-0004-policy-shadow-first.md)).

---

## 2. 목표 구조 (2계층 유지 + 신설 계층)

```text
[오라클 VM — 명령/오케스트레이터]
  oracle/core/api_server.py     HTTP API + SQLite 큐 (정본 P-1) + Bearer 인증
  oracle/core/agents.yaml       실행 노드 등록부 (기계 정본 — AGENTS_CANONICAL은 사람용 뷰)
  oracle/core/obsidian_index.py 볼트 경량 인덱스 (파생 캐시 — P-2)
        ▲ 폴링(pull, claim)
[집PC Windows 11 — 데이터 보유 + 실행]
  oracle/core/worker.py         큐 폴링 → TaskSpec 검증 → 디스패치        [Stage 17 배선]
    └→ scripts/core/provider_adapter.py  프로바이더 단일 관문 (claude_code 실동작)
         ├→ scripts/model_router.py      3티어 라우팅 + explain()
         ├→ scripts/bucky_client.py      Claude CLI 래퍼 (한도·폴백)
         ├→ usage_ledger.record()        사용량 원장                      [Stage 10 신설]
         └→ event_log.emit()             model_decision 등 이벤트         [Stage 15 신설]
  scripts/core/policy_engine.py evaluate(task_spec) 순수 함수 — shadow    [Stage 18/19 신설]
  data/registry/projects.yaml   Task/Goal/Project 분류 축 (큐 정본 불변)  [Stage 16 신설]
  ObsidianVault/                지식 정본 (01_RAW → 03_Knowledge SoT)
    └ knowledge_distiller.py    출처 전파(provenance) + supersedes        [Stage 20 확장]
  docs/ 대시보드(정적 JSON 패턴) + generate_brain_status.py               [Stage 21 신설]
```

승인 경로는 신설하지 않는다: policy가 `require_approval` 판정 시 **기존 `pending_approval/` 파일큐 + `approve_task.py` + Discord `!approve`** 를 그대로 사용한다 (두 경로의 통합 접점 = Stage 19).

---

## 3. 컴포넌트별 현재 → 목표

| 컴포넌트 | 현재 (실측 07-11) | 목표 | Stage |
|---|---|---|---|
| 작업 큐 | oracle SQLite 큐 구축·테스트 완료 (76 PASS) | 그대로 정본 유지 — 변경 없음 | — |
| worker 실행 | echo 스텁 | adapter 디스패치, `features.worker_adapter_dispatch: false` 기본 off | 17 |
| provider adapter | 인터페이스 + 5종 등록, claude_code만 실동작 | 동일 (멀티 provider 실전은 비목표 — 실행 불가 시 명시적 실패) | 17 |
| 사용량 원장 | 없음 (cli-tools.jsonl에 토큰·비용 없음) | `scripts/core/usage_ledger.py` → `data/usage/YYYY-MM.jsonl`, 단가는 `config/model_registry.yaml` | 10 |
| 이벤트 로그 | 로그 3분산 | `scripts/core/event_log.py` → `05_Logs/bucky-events.jsonl` 단일 envelope | 15 |
| model_decision | explain() 존재, 미기록 | emit 준비(15) → worker 디스패치 시 방출(17) | 15·17 |
| 레지스트리 | 없음 | `data/registry/projects.yaml` + `registry.py`, task_spec에 optional `project_id` | 16 |
| 정책 | 산문 문서 (`ROUTING_RULES.md`·`bucky.md`) | `config/policy_rules.yaml`(T0~T3) + `policy_engine.py` 순수 함수 → shadow 배선 | 18·19 |
| 예산 | 티어 라우팅·/spend pressure만 | usage 월 합계 임계 초과 시 경고 이벤트 (차단은 enforce 결정 후) | 19 |
| 메모리 출처 | conversation_id가 증류 후 단절 | distiller가 `source_conversation_id`/`source_file` 전파 + `supersedes`/`valid_until` optional | 20 |
| #processed | 수동 | sidecar `data/memory/processed_index.jsonl` (01_RAW 무수정) | 20 |
| 대시보드 | 33개, org-structure 하드코딩 | `bucky-brain.html` + `bucky_brain_status.json` 신설, org-structure JSON 동적화. 보호 3종 불가침 | 21 |

---

## 4. 데이터·이벤트 흐름 (목표)

1. 사용자/Discord `/oracle` → oracle 큐에 TaskSpec 등록 (정본 P-1).
2. 집PC worker가 폴링·claim → **policy_engine 상담(shadow: 판정을 이벤트로만)** → adapter 디스패치.
3. 디스패치 시: `model_decision` 이벤트 방출 + usage_ledger 기록 (둘 다 실패해도 실행 비차단).
4. 결과는 AgentResult 규약으로 큐에 보고. 지식 산출물은 볼트로 (01_RAW → 증류 → 03_Knowledge, 출처 ID 동반).
5. 대시보드는 큐·usage·이벤트·agents.yaml을 **읽기 전용**으로 집계 (정적 JSON 패턴).

## 5. LangGraph — 도입 보류, 평가 기준만 기록

현 구조(oracle 큐 + worker 폴링 + 순수 함수 정책)로 P0 범위가 전부 충족되므로 도입하지 않는다. 재평가 트리거와 채택 기준:

| 기준 | 채택 조건 (전부 충족 시에만 재검토) |
|---|---|
| 필요성 | 다단계 그래프 상태(분기·병합·중단 재개)가 실제 태스크에서 반복 요구될 것 — 현재는 큐 상태 7종 전이로 충분 |
| 중복성 | oracle 큐·pending_approval 승인 흐름과 역할이 겹치지 않는 계층에 한정 가능할 것 (큐 정본 P-1 침범 금지) |
| 의존성 | oracle/core의 stdlib 전용 원칙을 깨지 않을 것 (도입 시 집PC 측 scripts/ 계층에 한정) |
| 관측성 | 그래프 실행이 bucky-events.jsonl envelope로 관측 가능할 것 |
| 비용 | 학습·유지 비용이 P1 백로그(재개큐·우선순위엔진)를 직접 대체하는 이득을 넘을 것 |

## 6. 비목표 (플랜 Non-goals 상속)

음성 파이프라인(P4) / 에이전트 팩토리·자기진화(P5) / LangGraph 도입 / discord_bot.py 분해(Stage 11 홀드) / 수익화 오브젝트 / 큐 retry·DLQ·인덱스 경로 불일치(P1 백로그 — [`implementation_backlog.md`](implementation_backlog.md)) / **10_AgentBus 신규 파일 큐(영구 금지)**.
