# Codex 독립 검수 요청 — Bucky OS V3 G4 게이트 (Phase B: Stage 10·15·16·17)

- 작성일: 2026-07-12
- 요청자: Claude Code (구현) → Codex (독립 검수 #3)
- 브랜치: `bucky-os-v3-core` (HEAD = `2150ea6`)
- 검수 대상 커밋 (4건 — **커밋 단위가 검수 정본**):
  - `0455040` — Stage 10 usage_ledger 원장 + gbrain 토큰 하드코딩 핫픽스 (6 files, +294/-3)
  - `8a88256` — Stage 15 통합 이벤트 로그 event_log.py (2 files, +409)
  - `f70c430` — Stage 16 Task/Goal/Project 레지스트리 최소판 (6 files, +352)
  - `a79994d` — Stage 17 worker 어댑터 디스패치 배선, 플래그 기본 off (3 files, +136/-2)
- diff 범위 참고: `git log 0455040^..2150ea6`은 위 4건 외에 백로그 상태 갱신 docs 커밋 4건(`d92e2a0`·`8abb27c`·`103269f`·`2150ea6`)만 포함한다. docs 커밋은 검수 대상이 아니나, 백로그 기재 내용과 실제 구현의 불일치 발견 시 지적 대상이다.
- 기준 문서: `docs/bucky/implementation_backlog.md` §1 (순서 3~6 = Stage 10·15·16·17), `docs/adr/ADR-0002-v3-single-track.md`, `docs/adr/ADR-0003-event-log-not-bus.md`, 직전 게이트 결과: `docs/CODEX_REVIEW_REQUEST_PHASE_2.md` §5~6
- 플랜 정본(`C:\Users\user1\.claude\plans\foamy-churning-swing.md`)은 CWD 밖 — 접근 금지, 백로그 문서가 CWD 내 대리 정본이다.

> Codex는 독립적으로 검수한다. Claude는 검수에 개입하지 않으며, 검수 결과는 사용자에게 직접 보고된다.
> 사용자 지시가 있기 전까지 Claude는 이 diff를 수정하지 않는다. **Codex 통과 + 사용자 승인 전 다음 Stage(승인 플랜 순서상 Stage 18) 착수 금지.**

---

## 1. 이번 변경의 원칙 (설계 전제)

1. **Stage 10 = 신규 원장 + 계측 2점 + 핫픽스 1건.** `usage_ledger.record()`는 예외를 전파하지 않는다 — 계측 실패가 실행을 막지 않는다. claude_code는 `bucky_client`(layer="cli")와 `provider_adapter.run()`(layer="adapter") 양쪽에서 기록되므로 이중 계산 배제는 `month_summary(dedup=True)`가 담당. pricing은 예산 **추정** 전용(구독 CLI 실행은 토큰 과금이 아님 — 실청구와 다름을 주석에 명시).
2. **Stage 10 핫픽스**: `gbrain_mcp_proxy.py`의 토큰 리터럴 제거 → `.env GBRAIN_TOKEN`(override=False). 토큰 부재 시 stderr 안내 + exit 1. **주의: git 히스토리에 구 토큰이 잔존하는 것은 이미 알려진 사실이며 토큰 재발급은 별도 후속 작업(P1)으로 계획됨 — 중복 지적 불필요.**
3. **Stage 15 = 신규 파일만** (`scripts/core/event_log.py` + 테스트). **event_log는 관측 전용 — 버스·큐가 아니다** (ADR-0003). emit 계열은 실패해도 예외를 전파하지 않는다. 오라클 SQLite 큐가 작업 정본이라는 사실은 불변.
4. **Stage 16 = 분류 축만.** 레지스트리(`scripts/core/registry.py` + `data/registry/projects.yaml`)는 Task/Goal/Project **분류** 축이지 작업 큐가 아니다 — 작업 정본은 오라클 큐 불변. `task_spec.py` 4줄·`task_spec.schema.json` 5줄은 선택 필드 추가(하위 호환 필수). 10_AgentBus **파일 큐 신설 금지** 원칙 준수 — schema.json 수정은 계약 문서 갱신이지 큐 신설이 아님(위반 여부 독립 판단 요망).
5. **Stage 17 = oracle worker 1파일 + config 플래그 + 테스트.** `features.worker_adapter_dispatch` 기본 **false** = 기존 echo 스텁 유지(회귀 보증 + 즉시 롤백 스위치). config 로드 실패·부재도 False. on일 때만 `provider_candidates` 순회 → estimate ok인 첫 어댑터 `run()`. model_decision 이벤트는 실행 전 방출(Stage 15 실배선), usage 기록은 adapter.run() 내부 Stage 10 관문 단일 담당(worker 중복 기록 금지). 전 provider 불가 시 명시적 failed + `worker_dispatch_failed` 이벤트.
6. **과대 보고 금지 전제**: 실동작 provider는 claude_code뿐(나머지 스텁). Stage 17은 인터페이스 완성이지 멀티 provider 실전이 아니다. 문서·커밋 메시지가 이를 정직하게 기술하는지도 검수 대상.
7. 롤백 = Stage 10·15·16 신규 파일 삭제 + 각 커밋 revert. Stage 17은 config 플래그 off(기본값)만으로도 기능 무력화.

---

## 2. 변경 파일 목록

### Stage 10 — usage_ledger + gbrain 핫픽스 (커밋 0455040)

| 파일 | 역할 |
|---|---|
| `scripts/core/usage_ledger.py` (신규 224줄) | `data/usage/YYYY-MM.jsonl` append-only 기록 + `month_summary()` 월 합계(dedup 규칙: claude_code layer cli/adapter 이중기록 배제) + 셀프테스트 6항목 |
| `config/model_registry.yaml` | `pricing:` 신설 (haiku 1/5 · sonnet 3/15 · opus 5/25 USD per 1M — 예산 추정 전용) |
| `scripts/bucky_client.py` | `_invoke_bucky` 말미 `_usage_record()` 1건 (import 실패 시 no-op 폴백) |
| `scripts/core/provider_adapter.py` | `run()` → `_execute` 결과를 `_record_usage()` 래퍼로 계측 후 반환 |
| `scripts/gbrain_mcp_proxy.py` | 토큰 리터럴 제거 → `.env GBRAIN_TOKEN` (부재 시 exit 1) |
| `.gitignore` | `data/usage/` 등록 (오픈 퀘스천 2, 07-11 사용자 A안 확정) |

### Stage 15 — 통합 이벤트 로그 (커밋 8a88256)

| 파일 | 역할 |
|---|---|
| `scripts/core/event_log.py` (신규 254줄) | 이벤트 엔벨로프 emit + `emit_model_decision` (model_router `explain()` 스키마 정합) + 셀프테스트 |
| `tests/test_event_log.py` (신규 155줄) | 14 tests |

### Stage 16 — 레지스트리 최소판 (커밋 f70c430)

| 파일 | 역할 |
|---|---|
| `scripts/core/registry.py` (신규 158줄) | Task/Goal/Project 분류 축 조회 |
| `data/registry/projects.yaml` (신규) | 프로젝트 정의 시드 |
| `scripts/core/task_spec.py` (+4줄) | 선택 분류 필드 추가 |
| `ObsidianVault/10_AgentBus/contracts/task_spec.schema.json` (+5줄) | 계약 문서 동기화 |
| `tests/test_registry.py` (신규, 19 tests) / `tests/test_task_spec.py` (+14줄) | 테스트 |

### Stage 17 — worker 디스패치 배선 (커밋 a79994d)

| 파일 | 역할 |
|---|---|
| `oracle/core/worker.py` | `handle_task`에 `_dispatch_enabled()` 분기 + `_dispatch()` (provider 순회·이벤트 방출·명시 실패) |
| `config/bucky.yaml` | `features.worker_adapter_dispatch: false` 신설 |
| `oracle/tests/test_worker.py` | W11(off 회귀)/W12(on 디스패치)/W13(disabled 폴백)/W14(명시 실패+이벤트) 추가 — 총 14건 |

---

## 3. 검수 항목 (요청)

### 3.1 기존 기능 파손 여부 (최우선)

- [ ] **플래그 off 회귀 보증**: `worker_adapter_dispatch: false`(기본값)에서 `handle_task`의 입출력이 Stage 8~9 시점과 완전 동일한가? W1~W10 회귀 테스트가 실제로 이를 고정하는가?
- [ ] **provider_adapter.run() 계측 래퍼**: `_execute` 예외 → `_failed` 변환 경로가 Stage 6 crash 금지 계약을 그대로 유지하는가? `_record_usage()` 내부 예외가 결과 반환을 막을 수 있는가? (의도: import 실패 return + record 자체 비전파 — 독립 확인 요망)
- [ ] **bucky_client 계측 1건**: `_usage_record` 호출이 기존 폴백 체인·한도 판정 흐름에 부작용이 없는가?
- [ ] **task_spec.py +4줄의 하위 호환**: 기존 TaskSpec 생산자·소비자(oracle worker, provider_adapter, discord 경로)가 새 필드 없이도 동작하는가? `from_dict`/`validate()` 계약이 깨지지 않는가?
- [ ] **gbrain_mcp_proxy exit 1**: 토큰 부재 시 즉시 종료로 바뀐 것이 기존 운영(예약 작업·MCP 설정)에서 조용한 무한 실패로 이어질 여지는? (히스토리상 이전에는 하드코딩 토큰으로 무조건 기동)

### 3.2 시크릿 / 하드코딩

- [ ] 신규 코드에 키 값·토큰·새 절대경로 하드코딩이 없는가? (gbrain 구 토큰이 **현 HEAD 트리**에서 완전히 제거됐는가 — 히스토리 잔존은 기지 사실이므로 제외)
- [ ] usage 원장·이벤트 로그 기록에 프롬프트 원문·env 값 등 민감 정보가 저장되는 경로가 있는가? (의도: input_chars/output_chars는 길이만 기록)
- [ ] `data/usage/`가 `.gitignore`에 실제로 걸리는가 — clone에는 untracked 운영 파일이 없으므로 `git check-ignore -v data/usage/2026-07.jsonl`류로 검증할 것 (`git add --dry-run` 재현 불가).

### 3.3 계약 정합성

- [ ] **dedup 규칙의 정확성**: claude_code가 cli+adapter 양층에서 기록될 때 `month_summary(dedup=True)`가 이중 계산을 정확히 배제하는가? 반대로 adapter 단독 실행(비 claude_code)이 dedup에 잘못 걸려 과소 집계되는 경우는?
- [ ] **model_decision 스키마 정합**: `emit_model_decision(explain(...))`이 받는 dict와 event_log 스키마·model_router `explain()` 반환 형식이 3자 정합하는가?
- [ ] **worker `_dispatch` 계약**: instruction은 `payload["instruction"]`(Stage 8 규약) — 부재 시 빈 문자열로 adapter에 전달되고 adapter가 "instruction 없음" failed를 반환하는 경로가 의도대로인가? 반환 AgentResult status가 oracle `TRANSITIONS`와 정합하는가?
- [ ] **usage 이중 기록 금지**: worker `_dispatch`가 adapter.run() 외부에서 usage를 기록하지 않는 것이 사실인가? 반대로 dispatch 경로에서 기록 누락되는 provider 조합은?
- [ ] **ADR-0003 준수**: event_log 소비 코드가 이벤트를 상태 전이·작업 지시에 사용하는 곳이 없는가 (관측 전용 유지)?
- [ ] **레지스트리 경계**: registry.py가 오라클 큐 정본을 읽거나 변경하는 경로가 없는가? 10_AgentBus에 큐성 파일을 신설하지 않았는가?

### 3.4 이벤트·원장 파일 I/O 안전성

- [ ] append-only jsonl의 동시 기록(oracle worker + CLI 동시 실행) 시 레코드 파손 여지는? (Windows 파일 잠금 특성 포함 — 실측 가능하면 재현)
- [ ] emit/record 실패 침묵 설계의 부작용: 디스크 오류·경로 부재 시 이벤트 유실이 조용히 누적되는데, 이것이 P0-2(이벤트 기록)·P0-7(비용 원장) 목적과 충돌하는 수준인가?
- [ ] 로그·원장 파일 경로가 CWD/레포 상대 기준으로 안전하게 해석되는가 (`BUCKY_ROOT`류 env 주입 시 포함)?

### 3.5 테스트 충분성

- [ ] unittest 6모듈 128건(registry·task_spec·event_log·model_router_v3·config·provider_adapter) + oracle 4종 84건(worker 14·api_server 38·client 22·pipeline_e2e 10)이 클린 clone(`data/`·`.env` 부재)에서 전부 통과하는가?
- [ ] Stage 10에 전용 unittest 파일이 없다(셀프테스트 6항목만). 원장 dedup·비전파 계약이 회귀 테스트로 고정되지 않은 것이 위험 수준인가?
- [ ] W12(dispatch on) 테스트가 실제 어댑터 경로를 검증하는가, mock으로 형식만 통과하는가?

### 3.6 단순성 (Karpathy 기준)

- [ ] usage_ledger 224줄·event_log 254줄·registry 158줄이 각 Stage "최소판" 명분에 걸맞은가? 요청하지 않은 추상화·유연성(불필요 옵션·미사용 필드)이 들어갔는가?
- [ ] `_dispatch`의 skipped 수집·이벤트 방출 구조가 현 단계(실동작 provider 1종)에 과한가, 아니면 명시 실패 보고를 위한 최소인가?

---

## 4. Claude 측 검증 증거 (참고 — 2026-07-12 HEAD 2150ea6에서 실측)

```
$ python -X utf8 -m unittest tests.test_registry tests.test_task_spec tests.test_event_log \
    tests.test_model_router_v3 tests.test_config tests.test_provider_adapter
  Ran 128 tests — OK

$ python -X utf8 oracle/tests/test_worker.py       → 14 PASS / 0 FAIL (W1~W14)
$ python -X utf8 oracle/tests/test_api_server.py   → 38 PASS / 0 FAIL
$ python -X utf8 oracle/tests/test_client.py       → 22 PASS / 0 FAIL
$ python -X utf8 oracle/tests/test_pipeline_e2e.py → 10 PASS / 0 FAIL

$ python -X utf8 scripts/core/usage_ledger.py      → 셀프테스트 6항목 PASS
$ python -X utf8 scripts/core/event_log.py         → 셀프테스트 PASS
$ python -X utf8 scripts/core/provider_adapter.py  → 셀프테스트 PASS

격리 실경로 E2E (Stage 17): 임시 BUCKY_ROOT + dispatch on → model_decision·
worker_dispatch_failed 이벤트 2종 기록 확인 (실로그 무접촉)
```

### 테스트 실행법 주의 (게이트 #1·#2 경험 계승)

- unittest 6모듈은 **repo 루트에서 `-m unittest`로만** 실행 (직접 실행 시 namespace 오류 가능).
- oracle 4종은 **직접 실행** (`python -X utf8 oracle/tests/test_*.py`).
- 깨끗한 clone에는 `data/usage/`·`.env`가 없다 — env 부재 시 어댑터 `disabled`·원장 부재 시 빈 집계가 정상이며 crash 없음이 통과 기준.
- `gbrain_mcp_proxy.py`는 GBRAIN_TOKEN 없으면 exit 1이 **의도된 동작** (핫픽스 목적).

---

## 5. Codex 검수 결과 기입란 (Codex가 채움)

- 검수일: 2026-07-12 (Codex CLI 0.144.0-alpha.4, 일회용 clone HEAD=`2150ea6`, `data/usage/`·`.env` 부재 환경, `--sandbox danger-full-access`. Codex 최종 메시지를 Claude가 그대로 전사)
- 판정: ☐ 통과 / ☑ 조건부 통과 / ☐ 반려

### 5.1 발견 이슈 (MED 1)

- [MED] `oracle/core/worker.py:105` — `model_decision` 이벤트를 provider 가용성 검사 **전에** 방출하여, 실제 실행 provider와 `selected_provider`가 다르게 기록됨. Codex 재현: 후보 `["dead", "live"]`에서 `dead` disabled 조건 시 실제 실행 agent는 `live`였지만 이벤트에는 `dead`가 기록됨.
  → 실행 가능한 adapter가 확정된 뒤 이벤트를 방출하거나, 확정된 provider를 `selected_provider`로 전달하도록 수정.

### 5.2 필수 수정

1. Stage 17의 `model_decision.payload.selected_provider`가 실제 실행된 provider를 나타내도록 이벤트 방출 시점·인자를 수정
2. 1순위 disabled, 2순위 실행 사례에서 이벤트의 `selected_provider == 실제 결과 agent`를 검증하는 회귀 테스트 추가

### 5.3 권고 사항

- 실제 provider 실행 실패 시 다음 후보로 폴백할지 정책을 명시하고 테스트할 것. 현재는 `estimate.ok` 이후 `run()`이 failed를 반환하면 다음 후보를 시도하지 않음.
- Windows/G Drive 환경의 다중 프로세스 append 경합을 별도 통합 테스트로 검증할 것.

### 5.4 독립 재검증 수행 내역

- `git show 0455040`/`8a88256`/`f70c430`/`a79994d`: 각 커밋 단독 diff와 변경 파일 전수 검토.
- `python -X utf8 -m unittest tests.test_registry tests.test_task_spec tests.test_event_log tests.test_model_router_v3 tests.test_config tests.test_provider_adapter`: 128 tests, OK.
- oracle 직접 실행 4종: test_worker 14 / test_api_server 38 / test_client 22 / test_pipeline_e2e 10 — 전부 PASS (총 84).
- 셀프테스트: usage_ledger 6항목 / event_log 7항목 / provider_adapter (CLI·API key 부재에서 FAILED/DISABLED 판정, crash 없음) — 전부 PASS.
- `git check-ignore -v data/usage/2026-07.jsonl` → `.gitignore:231:data/usage/` 규칙 매칭 확인.
- `GBRAIN_TOKEN` 제거 후 `gbrain_mcp_proxy.py` 실행 → 설정 안내 stderr 출력 + exit 1 확인 (의도된 동작).
- Stage 17 폴백 별도 재현 → `selected_provider` 불일치 실증 (§5.1).
- 종료 전 `git diff --exit-code`·`git diff --cached --exit-code`·`git status --short`: 추적 파일 변경 없음 (요청서만 기존 untracked).

### 5.5 미검증 항목

- CWD 밖의 canonical 문서, 계획서, 메모리 및 절대경로 자료는 접근 금지로 미검증.
- 네트워크 금지로 실제 gbrain endpoint 연동 미검증.
- Claude/Codex CLI 및 API key 부재로 실제 provider dispatch E2E 미검증.
- 실제 G Drive 동기화 환경에서의 동시 append 경합 미검증.

<details>
<summary>Codex 원문 보고 전문 (2026-07-12)</summary>

```
[Codex 검수 결과 — V3 G4 게이트 (Phase B: Stage 10·15·16·17)]
─────────────────
판정: 조건부 통과

발견 이슈:
• [심각도: MED] oracle/core/worker.py:105 — `model_decision` 이벤트를 provider 가용성 검사 전에 방출하여, 실제 실행 provider와 `selected_provider`가 다르게 기록됨. 재현 결과 실제 실행 agent는 `live`였지만 이벤트에는 `dead`가 기록됨.
  → 실행 가능한 adapter가 확정된 뒤 이벤트를 방출하거나, 확정된 provider를 `selected_provider`로 전달하도록 수정

필수 수정:
1. Stage 17의 `model_decision.payload.selected_provider`가 실제 실행된 provider를 나타내도록 이벤트 방출 시점·인자를 수정
2. 1순위 disabled, 2순위 실행 사례에서 이벤트의 `selected_provider == 실제 결과 agent`를 검증하는 회귀 테스트 추가

권고 사항:
- 실제 provider 실행 실패 시 다음 후보로 폴백할지 정책을 명시하고 테스트할 것. 현재는 `estimate.ok` 이후 `run()`이 failed를 반환하면 다음 후보를 시도하지 않음.
- Windows/G Drive 환경의 다중 프로세스 append 경합을 별도 통합 테스트로 검증할 것.

독립 재검증 수행 내역:
- `git show 0455040`, `git show 8a88256`, `git show f70c430`, `git show a79994d`
  - 각 커밋 단독 diff와 변경 파일 전수 검토
- `python -X utf8 -m unittest tests.test_registry tests.test_task_spec tests.test_event_log tests.test_model_router_v3 tests.test_config tests.test_provider_adapter`
  - `Ran 128 tests`, `OK`
- `python -X utf8 oracle/tests/test_worker.py`
  - 14 PASS / 0 FAIL
- `python -X utf8 oracle/tests/test_api_server.py`
  - 38 PASS / 0 FAIL
- `python -X utf8 oracle/tests/test_client.py`
  - 22 PASS / 0 FAIL
- `python -X utf8 oracle/tests/test_pipeline_e2e.py`
  - 10 PASS / 0 FAIL
- `python -X utf8 scripts/core/usage_ledger.py`
  - 셀프테스트 PASS 6항목
- `python -X utf8 scripts/core/event_log.py`
  - 셀프테스트 PASS 7항목
- `python -X utf8 scripts/core/provider_adapter.py`
  - CLI·API key 부재 상태에서 adapter가 FAILED/DISABLED로 판정되고 crash 없이 셀프테스트 PASS
- `git check-ignore -v data/usage/2026-07.jsonl`
  - `.gitignore:231:data/usage/` 규칙 매칭 확인
- `GBRAIN_TOKEN` 제거 후 `python -X utf8 scripts/gbrain_mcp_proxy.py`
  - 설정 안내를 stderr에 출력하고 exit 1 확인
- Stage 17 폴백 별도 재현
  - 후보 `["dead", "live"]`, `dead` disabled 조건에서 실제 결과 agent=`live`, 이벤트 `selected_provider=dead` 확인
- 종료 전 `git diff --exit-code`, `git diff --cached --exit-code`, `git status --short`
  - 추적 파일 변경 없음
  - 요청서 `docs/CODEX_REVIEW_REQUEST_G4.md`만 기존 untracked 상태

미검증 항목:
- CWD 밖의 canonical 문서, 계획서, 메모리 및 절대경로 자료는 접근 금지로 미검증
- 네트워크 금지로 실제 gbrain endpoint 연동 미검증
- Claude/Codex CLI 및 API key 부재로 실제 provider dispatch E2E 미검증
- 실제 G Drive 동기화 환경에서의 동시 append 경합 미검증
─────────────────
```

</details>

> 검수 완료 후 사용자에게 직접 보고. 사용자 승인 시 Claude가 승인 플랜 순서(Stage 18)로 진행.
> **현 상태: G4 조건부 통과 (07-12) — MED 1건·필수수정 2건은 사용자 지시 후 이행. Stage 18 착수는 사용자 승인 대기.**
