# Codex 독립 검수 요청 — Bucky OS V3 G5 게이트 (Phase C: Stage 18·19)

- 작성일: 2026-07-12
- 요청자: Claude Code (구현) → Codex (독립 검수 #4)
- 브랜치: `bucky-os-v3-core` (HEAD = `a68f945`)
- 검수 대상 커밋 (2건 — **커밋 단위가 검수 정본**):
  - `72242a6` — Stage 18 policy_rules.yaml + policy_engine 순수 함수, 미배선 (신규 3파일, +315)
  - `ab68c09` — Stage 19 worker 정책 shadow 상담 배선 + 예산 경고 (3 files, +173/-1)
- 부수 확인 (재검수 생략분): `0c43835` — G4 필수수정 2건 이행 (model_decision 방출을 실행 provider 확정 직후로 이동 + W15 회귀). G4 재검수는 사용자 결정으로 생략됐으므로, G5에서 필수수정 이행의 정합만 가볍게 확인 요망 (이미 W15가 고정).
- diff 범위 참고: `git log 0c43835^..a68f945`는 위 3건 외에 백로그 상태 갱신 docs 커밋 3건(`04d3b7f`·`b41057d`·`a68f945`)만 포함한다. docs 커밋은 검수 대상이 아니나, 백로그 기재 내용과 실제 구현의 불일치 발견 시 지적 대상이다.
- 기준 문서: `docs/bucky/implementation_backlog.md` §1 (순서 7~8 = Stage 18·19), `docs/adr/ADR-0003-event-log-not-bus.md`, `docs/adr/ADR-0004-policy-shadow-first.md`, 직전 게이트 결과: `docs/CODEX_REVIEW_REQUEST_G4.md` §5
- 플랜 정본(`C:\Users\user1\.claude\plans\foamy-churning-swing.md`)은 CWD 밖 — 접근 금지, 백로그 문서가 CWD 내 대리 정본이다.

> Codex는 독립적으로 검수한다. Claude는 검수에 개입하지 않으며, 검수 결과는 사용자에게 직접 보고된다.
> 사용자 지시가 있기 전까지 Claude는 이 diff를 수정하지 않는다. **Codex 통과 + 사용자 승인 전 다음 Stage(승인 플랜 순서상 Stage 20) 착수 금지.**

---

## 1. 이번 변경의 원칙 (설계 전제)

1. **Stage 18 = 신규 파일만, 미배선.** `config/policy_rules.yaml`(스펙 §11.1 T0~T3 + ROUTING_RULES Approval Gates 산문의 데이터화) + `scripts/core/policy_engine.py`(`evaluate(spec) -> {tier, decision, reason}` 순수 함수 — 부작용·이벤트·차단 없음) + 테스트 18건. **폴백 방향은 보수**: 로드 실패·미분류·티어 정의 결손 → T3 require_approval (다른 모듈의 관대한 crash-금지 폴백과 반대 — 결손이 조용히 auto로 새는 것을 막고, shadow에서는 이벤트만 남아 무해).
2. **Stage 18에 dispatch 폴백 정책 명문화 포함** (G4 권고 1 이행 — 2026-07-12 사용자 A안 확정): `dispatch.fallback_on_run_failure: false` — run() 실패 = 태스크 실패, 폴백은 estimate 단계만. worker 현행 동작(W13·W14가 고정)의 데이터 명문화이지 동작 변경이 아님. **G4 권고 1의 중복 지적 불필요.**
3. **routing_policy.yaml과 top-level 키 중복 금지** — `validate_rules(rules, routing_policy=...)`가 검증. provider 후보열은 routing_policy.yaml, claude 티어는 model_router.TASK_TO_MODEL이 정본 (키 공간 분리).
4. **Stage 19 = worker 1파일 + config + 테스트.** `features.policy_enforcement: shadow` 기본. `handle_task`가 실행 경로 선택(echo/디스패치) **직전**에 `_policy_consult` — 판정을 `policy_decision` 이벤트로만 방출. **shadow 규약(ADR-0004): 어떤 모드·판정(require_approval 포함)에서도 차단·입출력 변형 없음.** off = 상담 안 함(즉시 롤백 스위치). enforce 값이 와도 차단하지 않는다(관측만) — enforce 전환은 플랜 범위 밖(shadow 운영 + 오판정 관측 + 사용자 승인 후 별도 결정), 승인 메커니즘 신설 금지.
5. **예산 경고 (P0-7 잔여)**: 상담 시 `usage_ledger.month_summary().cost_usd`(추정 전용)가 `budget.monthly_warn_usd`(기본 50, 0 = 비활성) 초과면 `budget_warning` 이벤트. policy_enforcement=off면 함께 꺼진다(단일 관측 스위치). 임계 초과 동안 태스크마다 1건 방출되는 것은 수용된 단순화(관측 로그, 차단 아님) — 과한지 여부는 §3.6에서 판단 요망.
6. **관측 불간섭 (ADR-0003)**: `_policy_consult`의 어떤 실패(정책 로드·evaluate 예외·usage 집계 실패)도 예외를 전파하지 않는다 — 관측이 실행을 막지 않는다. emit은 Stage 15 규약대로 자체 비전파.
7. 롤백: Stage 18 = 신규 파일 삭제. Stage 19 = `policy_enforcement: off`(즉시 무력화) 또는 revert.

---

## 2. 변경 파일 목록

### Stage 18 — 정책 엔진 (커밋 72242a6, 기존 파일 무수정)

| 파일 | 역할 |
|---|---|
| `config/policy_rules.yaml` (신규 77줄) | T0~T3 티어 정의 + task_type→tier 매핑(어휘 = model_router.TASK_TO_MODEL + Approval Gates 예약어) + `default_tier: T3` + `dispatch.fallback_on_run_failure: false` |
| `scripts/core/policy_engine.py` (신규 174줄) | `evaluate()` 순수 함수(소문자 정규화·보수 폴백) + `validate_rules()`(구조·키 중복 검증) + 셀프테스트 6항목 |
| `tests/test_policy_engine.py` (신규, 18 tests) | 대표 판정·보수 폴백·yaml 구조·키 중복 검증 |

### Stage 19 — shadow 배선 + 예산 경고 (커밋 ab68c09)

| 파일 | 역할 |
|---|---|
| `oracle/core/worker.py` (+60줄) | `_policy_mode()`(off/false/none/빈값 → 상담 안 함) + `_policy_consult()`(evaluate → policy_decision 이벤트, 예산 체크 → budget_warning, 전체 try/except 비전파) + handle_task 1줄 배선 |
| `config/bucky.yaml` (+11줄) | `features.policy_enforcement: shadow` + `budget.monthly_warn_usd: 50` |
| `oracle/tests/test_worker.py` (+103줄) | W16~W21 추가(아래 §3.5) + **러너 전체 이벤트 임시 경로 격리** (기본 shadow라 handle_task가 실로그에 방출하는 것 방지) |

---

## 3. 검수 항목 (요청)

### 3.1 기존 기능 파손 여부 (최우선)

- [ ] **shadow 바이트 동일 회귀**: `policy_enforcement: shadow`(신규 기본값)에서 `handle_task`의 반환 dict가 off와 완전 동일한가? W17(json.dumps 비교)이 이를 실제로 고정하는가 — echo 경로만 비교하는데 디스패치 경로(W12~W15 결과 불변)도 커버되는가?
- [ ] **`_policy_consult` 비전파 계약**: evaluate 예외·config 로드 실패·month_summary 예외 각각에서 실행이 절대 중단되지 않는가? (의도: 함수 전체 단일 try/except — W18이 evaluate 예외만 고정, 나머지 경로 독립 확인 요망)
- [ ] **기존 W1~W15 무손상**: 특히 W12~W14의 이벤트 검사가 신규 policy_decision 이벤트 추가로 오염되지 않는가? (기존 검사는 kind 필터라 통과 — 독립 확인)
- [ ] **`_policy_mode` 값 처리**: yaml `false`(bool)·`"off"`·결손·로드 실패가 전부 "상담 안 함"으로 수렴하는가? 미지 값(예: `"enforce"`)이 차단으로 이어지는 경로가 정말 없는가?

### 3.2 ADR-0004 준수 (shadow 계약)

- [ ] worker에 판정(`decision`)을 조건 분기로 소비하는 코드가 한 줄도 없는가 — require_approval 판정도 이벤트 방출뿐인가?
- [ ] 승인 메커니즘 신설 없음: pending_approval 파일큐·approve_task.py·Discord !approve에 대한 어떤 수정·대체·신규 경로도 없는가?
- [ ] 문서·주석·커밋 메시지가 "enforce는 미구현·범위 밖"을 정직하게 기술하는가 (과대 보고 금지)?

### 3.3 정책 데이터 정합성

- [ ] `policy_rules.yaml`의 T0~T3 매핑이 CWD 내 산문 정본(`ObsidianVault/00_System/ROUTING_RULES.md` Approval Gates)과 모순되지 않는가? 특히 T3 목록(commit/push/delete/deploy/payment/secrets_access 등)의 결손.
- [ ] task_tiers 어휘가 `model_router.TASK_TO_MODEL` 어휘를 누락 없이 커버하는가 — 누락 시 default_tier T3로 새는 것이 보수 방향이라 안전하지만, 의도된 커버리지인지 확인.
- [ ] `validate_rules`의 routing_policy 키 중복 검증이 실효적인가 (실제 두 yaml에 중복 키가 없는가)?
- [ ] evaluate의 보수 폴백 3경로(rules 없음 / 미분류 / tier 정의 결손)가 전부 T3 require_approval로 수렴하는가?

### 3.4 예산 경고 · 이벤트 정합성

- [ ] `budget_warning` 판정: `float(... or 0)` 변환이 yaml 문자열·음수·비수치에서 안전한가? threshold 0·결손 = 비활성이 보장되는가?
- [ ] month_summary(dedup=True 기본)와의 상호작용: 경고 판정에 쓰는 합계가 이중 기록 배제 후 값인가?
- [ ] `policy_decision`/`budget_warning` payload가 envelope 8필드 규약(Stage 15)에 정합한가? payload에 프롬프트 원문·비밀값이 실리는 경로는 없는가? (의도: verdict 3필드 + mode + task_type / 합계 4필드만)
- [ ] ADR-0003 준수: 신규 이벤트 2종을 소비해 상태 전이·작업 지시에 쓰는 코드가 없는가 (관측 전용 유지)?

### 3.5 테스트 충분성

- [ ] W16(기본 shadow)/W17(off-shadow 바이트 동일 + T0/auto 판정)/W18(상담 예외 불간섭)/W19(임계 초과 경고)/W20(이하 무경고)/W21(디스패치 경로에서 policy_decision이 model_decision보다 먼저) — 각각이 주장 그대로를 검증하는가, mock 형식 통과인가?
- [ ] test_policy_engine 18건이 evaluate·validate_rules의 실제 계약을 고정하는가?
- [ ] 클린 clone(`data/`·`.env` 부재)에서 전 스위트 통과하는가 — unittest 7모듈 146건 + oracle 4종 91건(worker 21·api_server 38·client 22·pipeline_e2e 10).
- [ ] 테스트 러너의 이벤트 격리(EVENTS_PATH 재지정)가 충분한가 — 러너 실행이 실로그(`05_Logs/bucky-events.jsonl`)·실원장(`data/usage/`)을 오염시키는 경로가 남아 있는가?

### 3.6 단순성 (Karpathy 기준)

- [ ] `_policy_consult` 55줄(주석 포함)이 "상담 + 이벤트 2종" 명분에 최소인가? 요청하지 않은 유연성(불필요 옵션·미래 대비 분기)이 들어갔는가?
- [ ] 임계 초과 동안 태스크마다 budget_warning 1건 방출(중복 억제 없음)이 현 단계에서 수용 가능한 단순화인가, 결함인가?
- [ ] policy_rules.yaml에 현 큐 어휘에 없는 예약어(T3 목록)를 미리 등록한 것이 추측성 구현인가, Approval Gates 데이터화의 최소인가?

---

## 4. Claude 측 검증 증거 (참고 — 2026-07-12 HEAD a68f945에서 실측)

```
$ python -X utf8 -m unittest tests.test_config tests.test_task_spec tests.test_model_router_v3 \
    tests.test_event_log tests.test_registry tests.test_provider_adapter tests.test_policy_engine
  Ran 146 tests — OK

$ python -X utf8 oracle/tests/test_worker.py       → 21 PASS / 0 FAIL (W1~W21)
$ python -X utf8 oracle/tests/test_api_server.py   → 38 PASS / 0 FAIL
$ python -X utf8 oracle/tests/test_client.py       → 22 PASS / 0 FAIL
$ python -X utf8 oracle/tests/test_pipeline_e2e.py → 10 PASS / 0 FAIL

$ python -X utf8 scripts/core/policy_engine.py     → 셀프테스트 PASS (6항목)
$ python -X utf8 scripts/core/event_log.py         → 셀프테스트 PASS (7항목)
```

### 테스트 실행법 주의 (게이트 #1~#3 경험 계승)

- unittest 7모듈은 **repo 루트에서 `-m unittest`로만** 실행 (직접 실행 시 namespace 오류 가능).
- oracle 4종은 **직접 실행** (`python -X utf8 oracle/tests/test_*.py`).
- 깨끗한 clone에는 `data/usage/`·`.env`가 없다 — 원장 부재 시 month_summary 빈 집계(cost 0)가 정상이며 crash 없음이 통과 기준.
- gbrain 구 토큰의 git 히스토리 잔존은 기지 사실(재발급 P1 별도) — 중복 지적 불필요.
- G4 권고 2(다중 프로세스 append 경합 통합 테스트)는 미이행 상태로 알려져 있음(기록 실패 비차단 원칙으로 수용 중) — 중복 지적 불필요, 단 이번 diff가 경합 위험을 **키웠다면** 지적 대상.

---

## 5. Codex 검수 결과 기입란 (Codex가 채움)

> 전사: Codex exec 최종 메시지 원문 (2026-07-12, 일회용 clone @ a68f945, danger-full-access, CWD 밖 접근·네트워크 금지 규칙 하 실행)

- 검수일: 2026-07-12
- 판정: ☐ 통과 / ☑ 조건부 통과 / ☐ 반려

### 5.1 발견 이슈

[P2] `config/policy_rules.yaml:27-65` — `model_router.TASK_TO_MODEL`의 유효 키 `default`가 `task_tiers`에서 누락되어, "TASK_TO_MODEL 어휘를 누락 없이 커버한다"는 §3.3 계약을 충족하지 못합니다. 현재는 보수 기본값 T3로 수렴해 즉각적인 안전 저하는 없습니다.

[P2] `tests/test_policy_engine.py:40-42,67-75` — 실제 라우팅 어휘 전체와 `task_tiers`의 포함 관계를 검증하지 않아 위 누락을 탐지하지 못합니다.

### 5.2 필수 수정

- `default`를 의도한 티어로 명시적으로 등록하거나, 라우터의 sentinel이라 정책 어휘에서 제외한다면 그 계약을 코드·문서로 명문화하십시오.
- `set(TASK_TO_MODEL) <= set(task_tiers)` 또는 명시적 제외 집합을 사용하는 회귀 테스트를 추가하십시오.

### 5.3 권고 사항

- `oracle/tests/test_worker.py:312-324`의 W17에 dispatch 경로의 off/shadow 반환값 비교도 추가하십시오. 현재 W17은 echo 경로만 고정합니다. 독립 추가 검증에서는 dispatch 결과도 바이트 동일했습니다.
- config 로드 실패와 `month_summary()` 예외를 W18의 별도 케이스로 고정하십시오. 현재 W18은 evaluate 예외만 검증합니다.
- Approval Gates의 `move/archive/reset/force_push/customer_data/pii`도 T3 예약어로 명시하면 산문 정본과의 감사 가능성이 좋아집니다. 현재는 미분류 기본값 T3로 안전하게 수렴합니다.
- 임계 초과 시 태스크마다 `budget_warning`을 방출하는 현재 구현은 shadow 관측 단계의 단순화로 수용 가능합니다.

### 5.4 독립 재검증 수행 내역

- `python -X utf8 -m unittest tests.test_config tests.test_task_spec tests.test_model_router_v3 tests.test_event_log tests.test_registry tests.test_provider_adapter tests.test_policy_engine`
  - 146 tests, OK
- `python -X utf8 oracle/tests/test_worker.py`
  - 21 PASS / 0 FAIL
- `python -X utf8 oracle/tests/test_api_server.py`
  - 38 PASS / 0 FAIL
- `python -X utf8 oracle/tests/test_client.py`
  - 22 PASS / 0 FAIL
- `python -X utf8 oracle/tests/test_pipeline_e2e.py`
  - 10 PASS / 0 FAIL
- `python -X utf8 scripts/core/policy_engine.py`
  - 셀프테스트 PASS, 6항목
- 추가 독립 검증:
  - dispatch 경로 off/shadow 반환값 바이트 동일 확인
  - `policy_decision`이 `model_decision`보다 먼저 방출됨 확인
  - `False/off/none/빈값/None`에서 상담 비활성 확인
  - config 로드 및 `month_summary()` 예외가 실행 결과를 변경하지 않음 확인
- `0c43835` 정합:
  - 실행 provider 확정 직후 `model_decision` 방출
  - W14 무선택 시 미방출, W15 실제 provider 일치 확인
- 최종 작업트리:
  - 추적 파일 변경 없음
  - 기존 untracked `docs/CODEX_REVIEW_REQUEST_G5.md`만 표시
  - 테스트가 만든 `data/usage/`는 `.gitignore:231`로 제외됨

### 5.5 미검증 항목

- 실제 운영 usage 원장 기반 예산 경고는 clone에 원장이 없어 미검증했습니다. 원장 부재 시 `cost_usd=0.0` 빈 집계와 무중단 동작은 확인했습니다.
- 실제 외부 provider·운영 서버 연동은 네트워크 금지 조건으로 검증하지 않았습니다.

> 검수 완료 후 사용자에게 직접 보고. 사용자 승인 시 Claude가 승인 플랜 순서(Stage 20)로 진행.

---

## 6. 재검증 결과 기입란 — 필수수정 2건 이행분 (Codex가 채움)

> 전사: Codex exec 최종 메시지 원문 (2026-07-12, 일회용 clone @ 248eb47, danger-full-access, CWD 밖 접근·네트워크 금지 규칙 하 실행)
> 이행 방식: 사용자 A안 확정 — `default: T3` 명시 등록 + 포함관계 회귀 테스트 1건 (`test_task_tiers_cover_router_vocabulary`)

- 재검증일: 2026-07-12
- 이행 커밋: `248eb47`
- 판정: ☑ 통과 — **G5 완전 통과 성립** (조건부 통과의 조건 해소)

### 6.1 Codex 최종 메시지 원문

[Codex G5 재검증 결과]
판정: PASS
- 필수수정 ① 이행: 충족 — `config/policy_rules.yaml`에 `default: T3`가 명시 등록됨.
- 필수수정 ② 이행: 충족 — `set(TASK_TO_MODEL) - set(RULES["task_tiers"])` 회귀 테스트 추가. 인메모리로 `default` 제거 시 신규 테스트가 실제 FAIL함을 확인함.
- 동작 중립성: 이행 전·후 모두 `(T3, require_approval)`. `reason`만 미분류 폴백 문구에서 명시 매핑 문구로 변경됨. 소비처는 이벤트 기록뿐이며 이를 판정에 사용하는 코드는 없음.
- 테스트: unittest 7모듈 `147 tests, OK` / oracle 4종 `91 PASS, 0 FAIL` (`38/22/10/21`)
- 범위 초과 변경: 없음 — 지정된 2개 파일, 9줄 추가만 존재.
- 잔여 우려: 없음. G5 비차단 권고 4건은 건드리지 않았으며 별도 백로그 상태 유지. 파일 변조 없이 인메모리 변조만 수행했고 작업 트리는 깨끗함.

G5 필수수정 2건이 완전히 이행되어 완전 통과가 성립합니다.
