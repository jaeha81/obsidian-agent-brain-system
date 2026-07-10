# Bucky OS V3 — 마이그레이션 플랜 (공사 계획서)

- 작성일: 2026-07-10
- 기준 문서: `docs/BUCKY_OS_V3_AUDIT.md` (현황 실측), `ObsidianVault/00_UPGRADE/upgrade-intake-2026-07-10.md` (V3 원안)
- 원칙: **기존 기능을 깨지 않는다. 단계마다 검증하고, Codex 독립 검수 게이트를 거친 뒤 다음 단계로 간다. 한 번에 갈아엎지 않는다.**

---

## 0. 확정 결정 (이 플랜의 전제)

1. **큐 정본 = oracle SQLite 큐** (`oracle/core/api_server.py`). V3 원안의 10_AgentBus 파일 큐(pending/running/retry/dead_letter)는 **만들지 않는다**. — 사용자 승인 07-10
2. 오라클 = 명령/오케스트레이터, 집PC = 데이터 보유 + 실행 (07-08 확정). Bucky Kernel 로직은 이 2계층 위에 얹는다.
3. TaskSpec/AgentResult JSON 계약은 **oracle 큐의 payload/result 필드 확장**으로 도입한다 (별도 파일 큐 계약이 아님).
4. `scripts/model_router.py`는 교체하지 않고 provider 차원(claude/codex/gpt/gemini)으로 **확장**한다.
5. `discord_bot.py` 분해(음성/메시지 pipeline 분리)는 **후순위 + 별도 승인 게이트** (B4 #3 홀드와 동일 사유).

---

## 1. 단계 개요

| Stage | 이름 | 코드 변경 | 위험도 | 상태 |
|---|---|---|---|---|
| 0 | 안전 준비 (브랜치·시크릿 점검) | 없음 | 없음 | ✅ 완료 07-10 |
| 1 | AUDIT 문서 | 없음 | 없음 | ✅ 완료 07-10 |
| 2 | 이 플랜 문서 | 없음 | 없음 | ✅ 완료 07-10 |
| 3 | config 단일화 스캐폴드 | 신규 파일만 | 낮음 | ✅ 완료 07-10 (4f0b068, 테스트 18) |
| 4 | TaskSpec/AgentResult 계약 | 신규 파일만 | 낮음 | ✅ 완료 07-10 (25fdc7d, 테스트 33) |
| 5 | Codex 독립 검수 게이트 #1 | 없음 | — | 🔶 요청서 작성됨, Codex·승인 대기 |
| 6 | Provider Adapter Layer | 신규 파일만 | 낮음~중간 | 대기 |
| 7 | Model Router provider 확장 | 기존 1파일 수정 | 중간 | 대기 |
| 8 | 오라클 큐 ↔ TaskSpec 연결 | 기존 수정 | 중간 | 대기 |
| 9 | Codex 독립 검수 게이트 #2 | 없음 | — | 대기 |
| 10 | usage_ledger + 대시보드 | 신규 위주 | 낮음 | 대기 |
| 11 | Discord pipeline 분해 | 대형 수정 | **높음** | **홀드 (별도 승인)** |
| 12 | Memory Engine | 신규 위주 | 중간 | 후순위 |

각 Stage는 완료 시 "변경 파일 / 실행 명령과 출력 / 위험 / 미완료" 형식으로 보고하고,
사용자 확인 후 다음 Stage로 넘어간다 (큰 작업 분할 프로토콜).

---

## 2. 단계별 상세

### Stage 3 — config 단일화 스캐폴드 (다음 착수 대상)

**목표**: 흩어진 경로·모델명·provider 설정이 들어갈 "한 곳"을 만든다. 기존 파일은 건드리지 않는다.

- 생성: `config/bucky.yaml`, `config/model_registry.yaml`, `config/routing_policy.yaml`, `scripts/core/config.py`, `scripts/core/__init__.py`
- `model_registry.yaml`: claude_code / codex_pro / openai_gpt(enabled:false) / gemini / anthropic_api 정의. **실제 키 값 금지, env 키 이름만**.
- `config.py`: ROOT/Vault/AgentBus/data/docs 경로 단일 정의 + yaml 로더. env 없어도 crash 금지.
- **하지 않는 것**: 기존 25개 절대경로·24개 모델명 하드코딩 파일의 일괄 수정. (파일별 이관은 Stage 7 이후 점진)
- 검증: `python -X utf8 scripts/core/config.py` 셀프테스트 + 신규 테스트 `tests/test_config.py`
- 롤백: 신규 파일 삭제만으로 원상복구 (기존 파일 무수정이므로)

### Stage 4 — TaskSpec / AgentResult 계약

**목표**: 에이전트들이 일을 받고 보고하는 표준 서식.

- 생성: `scripts/core/task_spec.py`, `scripts/core/agent_result.py`,
  `ObsidianVault/10_AgentBus/contracts/task_spec.schema.json`, `agent_result.schema.json`, `model_decision.schema.json`
- 필드: V3 원안 §Phase 4 목록 그대로 (task_id, source, channel, task_type, priority, required_capabilities, constraints, expected_output, created_at / agent, status, summary, files_changed, commands_run, test_result, risks, next_actions).
- **정합성 규칙**: task_id·status 값은 oracle 큐(`api_server.py`)의 기존 체계와 호환되게 설계 (충돌 시 oracle 체계가 정본).
- 기존 10_AgentBus inbox/outbox 구조는 **무수정** — contracts/ 디렉터리만 추가.
- 검증: `tests/test_task_spec.py`, `tests/test_agent_result.py` (스키마 왕복 직렬화)
- 롤백: 신규 파일 삭제

### Stage 5 — Codex 독립 검수 게이트 #1

- Stage 3~4 diff에 대해 `docs/CODEX_REVIEW_REQUEST_PHASE_1.md` 작성 → 사용자가 Codex에 전달.
- 검수 항목: 기존 기능 파손 여부, 시크릿, 하드코딩 잔존, 스키마-oracle 호환성, 테스트 충분성.
- **Codex 통과 + 사용자 승인 전 Stage 6 착수 금지.**

### Stage 6 — Provider Adapter Layer

- 생성: `scripts/core/provider_adapter.py`(인터페이스), `scripts/providers/claude_cli_adapter.py`, `codex_cli_adapter.py`, `gemini_adapter.py`, `anthropic_api_adapter.py`, `openai_adapter.py`(stub, disabled)
- 공통 메서드: `healthcheck()` / `estimate(task_spec)` / `run(task_spec)`
- 키 없음 → disabled 반환 (crash 금지). CLI 없음 → healthcheck failed 반환.
- 이번 단계는 **인터페이스 + 안전 stub 우선**, 실연동 최소화.
- claude_cli_adapter는 기존 `bucky_client.py`를 내부 호출하는 호환 래퍼로 시작 (기존 경로 무파손).

### Stage 7 — Model Router provider 확장

- 수정: `scripts/model_router.py` 1개 (또는 `scripts/routing/model_router_v3.py` 신설 + 기존을 wrapper 유지 — Codex 검수 의견 반영해 택1)
- task_type → provider 후보열(codex_pro/claude_code/gemini/…) 반환 기능 추가. 기존 `TASK_TO_MODEL`(claude 티어 선택)은 유지.
- 검증: `tests/test_model_router_v3.py` + 기존 model_router 테스트 회귀 통과

### Stage 8 — 오라클 큐 ↔ TaskSpec 연결

- oracle 큐 payload에 TaskSpec을 싣고, result에 AgentResult를 싣는 규약 적용.
- 수정 후보: `oracle/core/worker.py`(결과를 AgentResult 형식으로), `scripts/discord_bot.py`는 **이 단계에서 무수정**.
- 검증: `oracle/tests/` 4종 회귀 + E2E 1건

### Stage 10 — usage_ledger + 대시보드

- 생성: `scripts/core/usage_ledger.py`, `data/usage/` (jsonl 기록)
- 대시보드는 기존 docs 대시보드에 섹션 추가 우선, 신규 html은 필요 시.

### Stage 11 — Discord pipeline 분해 (홀드)

- 262KB `discord_bot.py`에서 message/voice/response_sender 분리. **별도 승인 없이 착수 금지.**
- 선행 조건: Stage 5·9 게이트 통과, 봇 무중단 전환 계획서 별도 작성.

---

## 3. 금지 사항 (V3 원안 §10 계승 + 추가)

1. .env/API key/토큰 출력·커밋 금지
2. 기존 bucky_*.py, model_router.py, discord_bot.py, 10_AgentBus 구조 삭제 금지
3. 10_AgentBus 파일 큐(pending/running/retry/dead_letter) 신설 금지 — 큐 정본은 oracle
4. 전체 일괄 재작성 금지 — Stage 단위, 게이트 통과 후 진행
5. 테스트 없이 성공 보고 금지 (증거 강제 규칙 적용)
6. 하드코딩 25+24 파일 일괄 수정 금지 — 점진 이관만

---

## 4. 롤백 총칙

- Stage 3~6, 10: 신규 파일 삭제 = 완전 롤백 (기존 파일 무수정 원칙)
- Stage 7~8: 수정 파일이 1~2개로 제한되므로 `git checkout <파일>` 단위 롤백
- 브랜치 전체 폐기 시: master로 복귀 (`git checkout master`), 브랜치 삭제
