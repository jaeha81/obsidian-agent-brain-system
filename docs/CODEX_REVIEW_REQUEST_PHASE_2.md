# Codex 독립 검수 요청 — Bucky OS V3 Phase 2 (Stage 6~8)

- 작성일: 2026-07-11
- 요청자: Claude Code (구현) → Codex (독립 검수)
- 브랜치: `bucky-os-v3-core` (HEAD = `b6c8bd0`)
- 검수 대상 커밋 (5건 — **커밋 단위가 검수 정본**):
  - `35dadd6` — Stage 6 Provider Adapter Layer (8 files, +639)
  - `8ff3655` — Stage 7 Model Router provider 확장 (2 files, +204/-3)
  - `a245856` — Stage 8 오라클 큐 ↔ TaskSpec 연결 (2 files, +40/-9)
  - `a7f38eb` — 부속: Claude 한도 초과 시 Codex 폴백 복원 (1 file, +135/-1)
  - `b6c8bd0` — 부속: Claude CLI npm 경로 폴백 복원 (1 file, +24/-1)
- diff 범위 참고: `git diff 360216f..b6c8bd0`는 위 5건 외에 무관 커밋 4건(`376e1fd`·`5c28321`·`d921185` 플랜 문서 갱신, `3abf783` 일일 자동 데이터)을 포함한다. 게이트 #1 재검수의 "범위 오염" 지적을 반영해 **이번 검수는 5개 커밋 각각의 단독 diff가 정본**임을 명기한다.
- 기준 문서: `docs/BUCKY_OS_V3_MIGRATION_PLAN.md` §Stage 6·7·8, `docs/BUCKY_OS_V3_AUDIT.md`, 게이트 #1 결과: `docs/CODEX_REVIEW_REQUEST_PHASE_1.md` §5~6

> Codex는 독립적으로 검수한다. Claude는 검수에 개입하지 않으며, 검수 결과는 사용자에게 직접 보고된다.
> 사용자 지시가 있기 전까지 Claude는 이 diff를 수정하지 않는다. **Codex 통과 + 사용자 승인 전 다음 Stage(승인 플랜 순서상 Stage 13) 착수 금지.**

---

## 1. 이번 변경의 원칙 (설계 전제)

1. **Stage 6 = 신규 파일만** (`scripts/core/provider_adapter.py` + `scripts/providers/` 5종 + 테스트). 인터페이스 + 안전 stub 우선, 실연동 최소화 (플랜 §Stage 6).
2. **crash 금지 3규칙**: 키 없음 → `disabled` 반환 / CLI 없음 → healthcheck `failed` 반환 / `run()` 내 예외 → 전부 `failed` AgentResult로 변환 (호출측 예외 전파 금지).
3. **Stage 7 = 기존 파일 수정 1개** (`scripts/model_router.py`). 기존 `TASK_TO_MODEL`·`fallback_chain` 무변경 — 회귀 테스트로 고정. `provider_candidates()` 추가는 routing_policy.yaml 정본, 로드 실패 시 `DEFAULT_PROVIDER_CHAIN` 폴백.
4. **Stage 8 = oracle worker만 수정**, `discord_bot.py` 무수정 (플랜 §Stage 8). 큐 정본 = oracle SQLite 유지, 파일 큐 신설 없음.
5. **부속 2건은 신규 기능이 아니라 회귀 복원**: `120267c` 시점에 유실된 `61b4120`의 기존 기능(한도 초과 시 Codex 폴백, npm 경로 폴백)을 복원한 것. 복원의 동등성이 검수 포인트.
6. 롤백 = Stage 6 신규 파일 삭제 + Stage 7·8·부속 커밋 revert.

---

## 2. 변경 파일 목록

### Stage 6 — Provider Adapter Layer (커밋 35dadd6)

| 파일 | 역할 |
|---|---|
| `scripts/core/provider_adapter.py` | `ProviderAdapter` 베이스: `healthcheck()`/`estimate()`/`run()` 공통 계약 + Health/Estimate dataclass + 셀프테스트 |
| `scripts/providers/__init__.py` | `ADAPTERS` 레지스트리(5종) + `get_adapter`/`all_adapters` 팩토리 |
| `scripts/providers/claude_cli_adapter.py` | 기존 `bucky_client.py` 내부 호출 호환 래퍼 (기존 경로 무파손) |
| `scripts/providers/codex_cli_adapter.py` | codex CLI probe |
| `scripts/providers/gemini_adapter.py` | google-genai 패키지 probe |
| `scripts/providers/anthropic_api_adapter.py` | env 키 존재 확인만 (실호출 없음) |
| `scripts/providers/openai_adapter.py` | stub, registry `enabled: false` |
| `tests/test_provider_adapter.py` | 31 tests |

### Stage 7 — Model Router provider 확장 (커밋 8ff3655)

| 파일 | 역할 |
|---|---|
| `scripts/model_router.py` | `provider_candidates(task_type)` 추가 (overrides→defaults→`DEFAULT_PROVIDER_CHAIN`), CLI `--providers` 플래그, **import 시점 stdout 무조건 재래핑 → utf8 가드 + 재래핑 전 flush로 수정** (Stage 6 셀프테스트에서 실측된 미flush 버퍼 유실 버그) |
| `tests/test_model_router_v3.py` | 17 tests (yaml 정책·주입 정책·기존 기능 회귀 고정·stdout 보존) |

### Stage 8 — 오라클 큐 ↔ TaskSpec 연결 (커밋 a245856)

| 파일 | 역할 |
|---|---|
| `oracle/core/worker.py` | `handle_task`: payload+레코드에서 TaskSpec 복원 → AgentResult(completed) dict 반환. `run_once` 실패 경로: `{error:...}` → AgentResult(failed). `sys.path.append`로 `scripts/core` 참조 |
| `oracle/tests/test_worker.py` | W3·W6을 AgentResult 형식 검증으로 갱신 (필드셋 고정) |

### 부속 — bucky_client.py 회귀 복원 (커밋 a7f38eb, b6c8bd0)

| 커밋 | 내용 |
|---|---|
| `a7f38eb` | `LIMIT_PATTERNS` 확장 복원(subscription limit/out of usage/resets am·pm/429/한국어 변형), `run_bucky`·`run_bucky_with_tools` 체인 소진 시 `_run_codex_after_claude_limit` 레그, `_invoke_codex`(codex exec `--sandbox`, tools=workspace-write·기본 read-only, `--output-last-message` 임시파일 회수), env 게이트 `BUCKY_CODEX_ON_LIMIT` |
| `b6c8bd0` | `_windows_npm_command_path`: PATH에 claude 없을 때 `%APPDATA%\npm\claude(.cmd)` 탐지, `bucky_command()` which 실패 시 폴백 재연결 |

---

## 3. 검수 항목 (요청)

### 3.1 기존 기능 파손 여부 (최우선)

- [ ] **model_router.py 기존 소비자 회귀**: `select_model`/`fallback_chain`/`model_for_command`를 import하는 기존 코드(discord_bot.py 등)의 동작이 변하지 않는가? 기존 `TASK_TO_MODEL` 무변경이 실제로 지켜졌는가?
- [ ] **stdout 재래핑 변경의 부작용**: 기존(무조건 재래핑) → 신규(utf8이면 스킵, 재래핑 전 flush). win32에서 기존 호출자가 재래핑에 의존하던 케이스가 깨지는가? 반대로 이 수정이 주장하는 "미flush 버퍼 유실"이 실제 버그였는가 (구버전 재현)?
- [ ] **worker.py 반환 형식 변경**: `handle_task`가 `{echo:...}` → AgentResult dict로 바뀌었다. 이 result를 소비하는 기존 코드가 있는가? (Claude 판단: `api_server.py`는 result를 JSON blob으로 저장만 함 — 독립 확인 요망)
- [ ] **worker.py의 `sys.path.append(scripts/core)`**: append(뒤 추가)라 기존 `oracle/core` 모듈(client 등)이 우선이라는 게 Claude 판단이나, top-level 이름 `task_spec`/`agent_result`가 다른 경로의 동명 모듈과 충돌할 여지가 있는가?
- [ ] **bucky_client.py 폴백 누수**: 한도 초과가 아닌 일반 오류(BuckyError)가 Codex 레그로 새는 경로가 있는가? (의도: `BuckyLimitError`일 때만)

### 3.2 시크릿 / 하드코딩

- [ ] 신규 코드에 키 값·토큰·새 절대경로 하드코딩이 없는가? (셀프테스트 출력의 CLI 경로는 런타임 탐지 결과이지 하드코딩 아님 — 독립 확인 요망)
- [ ] `provider_adapter.py`가 `.env`를 로드하는데(`load_dotenv`, override=False), env 값이 로그·예외 메시지·AgentResult에 노출되는 경로가 있는가? (의도: `missing_env_keys()`는 키 **이름**만 다룸)

### 3.3 계약 정합성 (Stage 4 계약과의 연결)

- [ ] `run()`이 반환하는 AgentResult의 `status`가 `agent_result.py`의 `VALID_STATUSES` 안에 있는가? (`_failed`는 "failed" 고정)
- [ ] `provider_candidates()` 반환 이름·`DEFAULT_PROVIDER_CHAIN`(`["claude_code"]`)이 `config/model_registry.yaml` providers 키와 정합하는가?
- [ ] `providers/__init__.py`의 `ADAPTERS` 키 5종이 registry providers 키와 1:1인가?
- [ ] worker의 `completed`/`failed`가 oracle `TRANSITIONS` 체계와 정합하는가?
- [ ] `run(task_spec, instruction)` 설계 — TaskSpec에 지시문 필드가 없어 별도 인자로 받는 결정이 타당한가, 아니면 TaskSpec 확장이 맞았는가?

### 3.4 회귀 복원의 동등성 (부속 2건)

- [ ] `git show 61b4120` 등 히스토리와 대조해, 복원이 유실 전 기능과 **동등**한가? 복원을 빙자한 신규 동작이 끼어들지 않았는가?
- [ ] `LIMIT_PATTERNS` 확장의 오탐 위험: `429`, `resets .*(am|pm)` 같은 패턴이 한도와 무관한 출력에 매치되어 정상 실행을 Codex로 넘길 수 있는가? 이 패턴이 적용되는 지점(stderr/stdout/예외 메시지)이 어디인지와 함께 판단 요망.
- [ ] `_invoke_codex`의 sandbox 기본값(read-only, tools 시 workspace-write)이 안전한가? `--output-last-message` 임시파일이 누수 없이 정리되는가?

### 3.5 테스트 충분성

- [ ] 53 tests(provider_adapter 31 + model_router_v3 17 + command_resolution 2 + codex_fallback 3) + oracle 76 전부 통과. 빠진 실패 케이스가 있는가? (예: policy에 잘못된 타입 주입, 어댑터 registry 결손 항목, 폴백 레그의 timeout)
- [ ] Stage 7 회귀 고정 테스트가 기존 동작을 실제로 고정하는가 (형식적 통과가 아니라)?

### 3.6 단순성 (Karpathy 기준)

- [ ] Stage 6이 "인터페이스 + 안전 stub 우선"인데, 베이스 클래스 + 5 어댑터 + 팩토리 구조에 요청하지 않은 추상화·유연성이 들어갔는가?
- [ ] `Health`/`Estimate` dataclass 도입이 현 단계에 과한가?

---

## 4. Claude 측 검증 증거 (참고 — 2026-07-11 HEAD b6c8bd0에서 실측)

```
$ python -X utf8 -m unittest tests.test_provider_adapter tests.test_model_router_v3 \
    tests.test_bucky_client_command_resolution tests.test_bucky_client_codex_fallback
  Ran 53 tests — OK

$ python -X utf8 oracle/tests/test_worker.py       → 6 PASS / 0 FAIL
$ python -X utf8 oracle/tests/test_api_server.py   → 38 PASS / 0 FAIL
$ python -X utf8 oracle/tests/test_client.py       → 22 PASS / 0 FAIL
$ python -X utf8 oracle/tests/test_pipeline_e2e.py → 10 PASS / 0 FAIL

$ python -X utf8 scripts/core/provider_adapter.py
  == 어댑터 5종 ==
  [OK] claude_code / [FAILED] codex_pro(CLI 없음) / [DISABLED] openai_gpt
  [FAILED] gemini(패키지 없음) / [OK] anthropic_api
  셀프테스트 PASS (exit 0)
```

### 테스트 실행법 주의 (게이트 #1 경험 계승)

- `tests.test_bucky_client_command_resolution`은 **repo 루트에서 `-m unittest`로만** 실행 (직접 실행 시 namespace 오류).
- oracle 4종은 **직접 실행** (`python -X utf8 oracle/tests/test_*.py`).
- 깨끗한 clone에는 `data/`·`.env`가 없다 — 게이트 #1 필수수정으로 테스트는 clone 환경에서도 통과하도록 수정된 상태(`RUNTIME_KEYS`). env 부재 시 어댑터는 `disabled`로 판정될 뿐 crash하지 않아야 하며, 이것이 통과 기준이다.

---

## 5. Codex 검수 결과 기입란 (Codex가 채움)

- 검수일: 2026-07-11 (Codex CLI 0.144.0-alpha.4, 일회용 clone HEAD=b6c8bd0, data/·.env 부재 환경, `--sandbox danger-full-access`. Codex 최종 메시지를 Claude가 그대로 전사)
- 판정: ☐ 통과 / ☑ 조건부 통과 / ☐ 반려
- 발견 이슈 (MED 6 · LOW 3):
  - [MED] `oracle/core/worker.py:57` — payload가 오라클 정본 필드를 덮어쓰고 `TaskSpec.validate()` 미호출 → 잘못된 task_id·priority·task_type도 `completed` 처리
  - [MED] `oracle/core/worker.py:35` — `task_spec`을 top-level 모듈로 로드해 `core.task_spec.TaskSpec`과 클래스 분리 → 유효한 worker TaskSpec이 ProviderAdapter에서 거절됨 (Codex 실재현)
  - [MED] `provider_adapter.py:43` vs `bucky_client.py:25` — `.env` override 정책 불일치 (False vs True) → 호출자 env를 bucky_client가 덮어씀
  - [MED] `provider_adapter.py:122` — 실행 불가 stub(Codex·Gemini·Anthropic)도 `Estimate.ok=True` 반환 (실재현: estimate ok / run failed 모순)
  - [MED] `model_router.py:35` — custom 비-UTF8 wrapper 교체 시 기존 wrapper GC가 공유 buffer를 닫음 (실재현: `sys.stdout.closed=True`) → `reconfigure()` 권고
  - [MED] `bucky_client.py:49,276` — bare `429`·`resets .*(am|pm)` 오탐 (실재현: `port 4290`, `cache resets ... 10am` 매치) + `stderr or stdout`이라 한쪽 출력의 한도 메시지 누락 가능
  - [LOW] `claude_cli_adapter.py:30` — 내부 폴백 발생 시에도 AgentResult가 최초 모델·`claude_code`만 기록
  - [LOW] `model_router.py:161` — provider 체인이 문자열 여부만 검사 → registry에 없는 `typo_provider`도 통과
  - [LOW] `oracle/tests/test_worker.py:85` — 전체 TaskSpec payload·정본 필드 충돌·invalid 실패 경로 미테스트
- 필수 수정:
  1. worker의 TaskSpec 병합 우선순위(정본 필드 마지막 병합) + 검증 실패를 `AgentResult(failed)`로
  2. worker와 ProviderAdapter의 `core.task_spec.TaskSpec` import 통일 (클래스 정체성 일원화)
  3. `.env` 우선순위 `override=False` 일관화 + 충돌 우선순위 테스트
  4. stub provider의 `Estimate` 계약을 실행 가능 상태와 일치
  5. stdout/stderr 재설정을 `reconfigure()` 기반으로
  6. 한도 판정 정규식(HTTP 429 문맥·단어 경계) + stderr·stdout 결합 판정
- 권고 사항: fallback 실행 주체·실제 명령의 AgentResult 정확 기록 / `registry or load_model_registry()`의 빈 dict 무시·비-list `env_keys` fail-open 수정 / config 누락 시 skip하는 테스트를 실패 처리 + 재현 사례 회귀 고정 / oracle 테스트 임시 디렉터리 정리
- 미검증: `61b4120` 객체가 clone에 부재 → 복원 동등성은 `120267c^`·`fec17e5`·`add4868` 대조로 "거의 동등" 판단까지만. 실 provider 호출·운영 env 충돌은 정적·mock 재현까지만.

<details>
<summary>Codex 원문 보고 전문 (2026-07-11)</summary>

```
[Codex 검수 결과 — V3 Phase 2 (Stage 6~8)]
─────────────────
판정: 조건부 통과

발견 이슈:
• [심각도: MED] oracle/core/worker.py:57 — payload가 오라클 정본 필드를 덮어쓰며 `TaskSpec.validate()`도 호출하지 않아 잘못된 task_id·priority·task_type도 `completed` 처리된다.
  → 큐 레코드 정본 필드를 마지막에 병합하고 검증 실패를 `AgentResult(failed)`로 처리한다.

• [심각도: MED] oracle/core/worker.py:35 — `task_spec`을 top-level 모듈로 로드해 `core.task_spec.TaskSpec`과 클래스가 분리된다. 실제 재현에서 유효한 worker TaskSpec이 ProviderAdapter에서 거절됐다.
  → `scripts` 경로와 `core.task_spec`·`core.agent_result` 패키지 import로 정본을 통일한다.

• [심각도: MED] scripts/core/provider_adapter.py:43, scripts/bucky_client.py:25 — 어댑터는 `.env override=False`를 선언하지만 이후 `bucky_client`가 `override=True`로 다시 로드해 호출자의 환경변수를 덮어쓴다.
  → 전체 경로를 `override=False`로 통일하고 충돌 우선순위 테스트를 추가한다.

• [심각도: MED] scripts/core/provider_adapter.py:122 — 실행이 항상 실패하는 Codex·Gemini·Anthropic stub도 health만 통과하면 `Estimate.ok=True`를 반환한다.
  → stub은 `Estimate.ok=False` 또는 명시적 `execution_supported=False`를 반환한다.

• [심각도: MED] scripts/model_router.py:35 — 사용자 정의 비-UTF8 `TextIOWrapper`를 교체하면 기존 wrapper GC가 공유 buffer를 닫는다. 재현 결과 import 후 `sys.stdout.closed=True`였다.
  → wrapper 교체 대신 `stream.reconfigure(encoding="utf-8", errors="replace")`를 사용한다.

• [심각도: MED] scripts/bucky_client.py:49,276 — bare `429`와 광범위한 `resets .*(am|pm)`이 `4290` 포트 오류 같은 일반 실패도 한도 초과로 오인해 Codex 폴백을 실행한다. 반대로 `stderr or stdout`이라 양쪽 출력 중 하나의 한도 메시지는 놓칠 수 있다.
  → HTTP 429 문맥과 단어 경계를 적용하고 stderr·stdout을 합쳐 판정한다.

• [심각도: LOW] scripts/providers/claude_cli_adapter.py:30 — Claude 모델 또는 Codex로 폴백해도 AgentResult는 항상 `claude_code`와 최초 모델 명령만 기록한다.
  → 실제 provider·성공 모델·시도 목록을 반환하거나 어댑터 내부 폴백을 비활성화한다.

• [심각도: LOW] scripts/model_router.py:161 — provider 체인은 문자열 여부만 검사해 `typo_provider`도 유효 후보로 반환한다.
  → model registry membership과 중복까지 검증하고 실패 시 기본 체인으로 폴백한다.

• [심각도: LOW] oracle/tests/test_worker.py:85 — 전체 TaskSpec payload, 정본 필드 충돌 및 invalid TaskSpec 실패 경로가 테스트되지 않는다.
  → Stage 8 계약을 직접 검증하는 E2E 케이스를 추가한다.

필수 수정:
1. worker의 TaskSpec 병합 우선순위와 검증 경계를 수정한다.
2. worker와 ProviderAdapter가 동일한 `core.task_spec.TaskSpec`을 사용하도록 import를 통일한다.
3. `.env` 우선순위를 `override=False`로 일관되게 만든다.
4. stub provider의 Estimate 계약을 실행 가능 상태와 일치시킨다.
5. stdout/stderr 재설정을 `reconfigure()` 기반으로 변경한다.
6. Claude 한도 판정 정규식과 stderr/stdout 결합 로직을 보강한다.

권고 사항:
- fallback 실행 주체와 실제 명령을 AgentResult에 정확히 기록한다.
- 빈 registry 주입을 무시하는 `registry or load_model_registry()`와 비-list `env_keys` fail-open을 수정한다.
- 정본 config 누락 시 skip하는 테스트를 실패 처리하고, 위 재현 사례를 회귀 테스트로 고정한다.
- Oracle 테스트의 임시 디렉터리 자동 정리를 추가한다.

독립 재검증 수행 내역:
- `git rev-parse HEAD` → `b6c8bd016759d640191dd7c44cd32d85360ad01d`.
- `git show 35dadd6`, `8ff3655`, `a245856`, `a7f38eb`, `b6c8bd0` → 각 단독 diff 검토 완료.
- `python -X utf8 -m unittest tests.test_provider_adapter tests.test_model_router_v3 tests.test_bucky_client_command_resolution tests.test_bucky_client_codex_fallback` → 53 tests, OK.
- Oracle 직접 실행 4종 → 6/38/22/10 PASS, 총 76 PASS.
- `python -X utf8 scripts/core/provider_adapter.py` → disabled/failed 상태에서 crash 없이 셀프테스트 PASS.
- 구버전 stdout 재현 → `before-import` 유실 확인. 현재 기본 스트림에서는 보존되지만 custom wrapper는 닫힘 확인.
- 잘못된 worker payload → invalid TaskSpec이 `completed`로 반환됨을 확인.
- stub estimate 재현 → Anthropic·Codex 모두 `Estimate.ok=True`, `run.status=failed`.
- 한도 패턴 재현 → `port 4290`, `cache resets ... 10am` 모두 오탐.
- 시크릿 패턴 검사 → 실제 키·토큰 및 신규 운영 절대경로 하드코딩 없음.
- `git diff --stat`, `git diff --check` → 추적 파일 변경 없음. 테스트가 CWD에 생성한 untracked `bucky_*` 임시 산출물은 무수정 규칙에 따라 삭제하지 않음.

미검증 항목:
- `61b4120` 객체가 clone에 없어 `git show 61b4120:scripts/bucky_client.py` 직접 대조 불가. `120267c`에서도 해당 파일이 삭제된 상태다.
- 대체로 `120267c^`, `fec17e5`, `add4868`과 비교했으며 복원 함수는 거의 동등했지만, 지정 정본과의 완전한 동일성은 확정할 수 없다.
- `.env`, data 및 실제 Claude/Codex/API 환경이 없어 실 provider 호출과 운영 환경변수 충돌은 정적·mock 재현까지만 검증했다.
- 초기 PowerShell 프로필 자동 로드 시도는 실행정책으로 거부됐으며, 이후 모든 셸 명령은 프로필 로드 없이 실행했다.
─────────────────
```

</details>

> 검수 완료 후 사용자에게 직접 보고. 사용자 승인 시 Claude가 승인 플랜 순서(Stage 13)로 진행.
> **현 상태: 조건부 통과 — 필수 수정 6건. 사용자 지시 전 Claude 수정 착수 금지.**
