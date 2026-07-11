# Codex 독립 검수 요청 — Bucky OS V3 Phase 1 (Stage 3~4)

- 작성일: 2026-07-10
- 요청자: Claude Code (구현) → Codex (독립 검수)
- 브랜치: `bucky-os-v3-core`
- 검수 대상 커밋: `4f0b068` (Stage 3), `25fdc7d` (Stage 4)
- diff 범위: `git diff df7c827..HEAD` (14 files, +873 lines, 삭제 0)
- 기준 문서: `docs/BUCKY_OS_V3_MIGRATION_PLAN.md` §Stage 3·4·5, `docs/BUCKY_OS_V3_AUDIT.md`

> Codex는 독립적으로 검수한다. Claude는 검수에 개입하지 않으며, 검수 결과는 사용자에게 직접 보고된다.
> 사용자 지시가 있기 전까지 Claude는 이 diff를 수정하지 않는다. **Codex 통과 + 사용자 승인 전 Stage 6 착수 금지.**

---

## 1. 이번 변경의 원칙 (설계 전제)

1. **신규 파일만 추가, 기존 파일 무수정** — 예외 단 1건: `.gitignore`에 allowlist 2줄 추가(계약 스키마 버전관리 목적).
2. **큐 정본 = oracle SQLite 큐** (`oracle/core/api_server.py`). 파일 큐 신설 안 함.
3. **하드코딩 일괄 수정 안 함** — config는 "한 곳"만 만들고, 기존 25+24 파일 이관은 Stage 7 이후 점진.
4. **crash 금지** — env 없음/yaml 깨짐/PyYAML 부재에도 예외 없이 빈 dict 폴백.
5. 롤백 = 신규 파일 삭제 + `.gitignore` 2줄 되돌림.

---

## 2. 변경 파일 목록

### Stage 3 — config 단일화 스캐폴드 (커밋 4f0b068)

| 파일 | 역할 |
|---|---|
| `config/bucky.yaml` | 경로(root 상대)·oracle 큐 정본 선언. env 키 이름만 |
| `config/model_registry.yaml` | provider 5종 (claude_code/codex_pro/openai_gpt(disabled)/gemini/anthropic_api) |
| `config/routing_policy.yaml` | provider 후보열만. claude 티어 정본은 model_router.py 유지 |
| `scripts/core/config.py` | ROOT/Vault/AgentBus/data/docs 단일정의 + crash-free yaml 로더 + 셀프테스트 |
| `scripts/core/__init__.py` | 패키지 선언 |
| `tests/test_config.py` | 18 tests |

### Stage 4 — TaskSpec/AgentResult 계약 (커밋 25fdc7d)

| 파일 | 역할 |
|---|---|
| `scripts/core/task_spec.py` | TaskSpec dataclass + validate + 왕복 직렬화 + new_task_id |
| `scripts/core/agent_result.py` | AgentResult dataclass + validate + 왕복 직렬화 |
| `ObsidianVault/10_AgentBus/contracts/task_spec.schema.json` | TaskSpec JSON Schema (draft-07) |
| `ObsidianVault/10_AgentBus/contracts/agent_result.schema.json` | AgentResult JSON Schema |
| `ObsidianVault/10_AgentBus/contracts/model_decision.schema.json` | 라우팅 결정 로그 스키마 (Python 클래스 없음) |
| `tests/test_task_spec.py` | 17 tests |
| `tests/test_agent_result.py` | 16 tests |
| `.gitignore` | `10_AgentBus/contracts/`만 추적하도록 allowlist 추가 |

---

## 3. 검수 항목 (요청)

### 3.1 기존 기능 파손 여부 (최우선)
- [ ] 신규 파일이 기존 import 경로/모듈을 가리거나 충돌하는가? (`scripts/core/`는 신규 패키지 — 기존 `scripts/*.py`와 이름 충돌 없음 확인 요망)
- [ ] `.gitignore` 변경으로 **의도치 않게 노출되는 운영 파일이 있는가?** 특히 `10_AgentBus`의 inbox/claims/outbox 등 3,379개가 추적 대상에 들어오면 안 됨.
  - Claude 측 검증: `git add --dry-run ObsidianVault/10_AgentBus/` → contracts 3종만 출력됨(운영 파일 0). Codex 독립 재확인 요망.
- [ ] `.gitignore` 3단 패턴(`!dir/` → `dir/*` → `!dir/contracts/**`)이 다른 allowlist 규칙과 상호작용해 부작용을 만드는가?

### 3.2 시크릿 / 하드코딩
- [ ] `config/*.yaml`에 실제 키 값이 아닌 **env 변수 이름만** 들어갔는가? (`test_env_keys_are_names_not_values`가 강제하나 독립 확인 요망)
- [ ] 신규 config가 새 절대경로 하드코딩을 도입했는가? (의도: root 자동탐지 + 상대경로만)

### 3.3 oracle 호환성 (계약의 핵심)
- [ ] `task_spec.py`의 `PRIORITIES`·task_id 정규식이 `oracle/core/api_server.py`와 일치하는가?
- [ ] `agent_result.py`의 `VALID_STATUSES`가 oracle `TRANSITIONS.keys() ∪ STATUS_TARGETS`와 정확히 일치하는가?
  - Claude 측 검증: `test_statuses_match_oracle`·`test_priorities_match_oracle`가 oracle을 import해 크로스체크(skip 아님, 통과). Codex는 **oracle이 정본이라는 방향성**이 코드에 실제로 반영됐는지(값 하드코딩이 아니라 oracle과 대조되는지) 판단 요망.
- [ ] `model_decision.schema.json`의 `selected_provider`가 `model_registry.yaml` provider 키와 정합하는가?

### 3.4 테스트 충분성
- [ ] 51 tests(config 18 + task_spec 17 + agent_result 16) 전부 통과. 계약의 왕복 직렬화·경계값·잘못된 입력이 충분히 커버되는가?
- [ ] 빠진 실패 케이스가 있는가? (예: `from_dict`의 부분 필드, 잘못된 타입 주입)

### 3.5 단순성 (Karpathy 기준)
- [ ] 요청하지 않은 추상화/유연성/설정성이 들어갔는가?
- [ ] `model_decision.schema.json`을 Python 클래스 없이 스키마만 둔 결정이 타당한가, 아니면 지금 클래스가 필요한가?

---

## 4. Claude 측 검증 증거 (참고)

```
$ python -X utf8 scripts/core/config.py
  경로 7개 [OK], yaml 3종 로드 OK, providers 5개(enabled 4), 셀프테스트 PASS (exit 0)

$ python -X utf8 -m unittest tests.test_config tests.test_task_spec tests.test_agent_result
  Ran 51 tests — OK

$ git add --dry-run ObsidianVault/10_AgentBus/
  add '.../contracts/agent_result.schema.json'
  add '.../contracts/model_decision.schema.json'
  add '.../contracts/task_spec.schema.json'
  (운영 파일 3,379개 노출 없음)
```

---

## 5. Codex 검수 결과 기입란 (Codex가 채움)

- 검수일: 2026-07-11 (Codex CLI 0.144.0, 3차 시도에서 완료 — 1·2차는 Windows 샌드박스 `deny-read ACLs` 헬퍼 고장으로 불발. 로컬 일회용 clone(25fdc7d 체크아웃)에서 샌드박스 비활성으로 실행. Codex 최종 메시지를 Claude가 그대로 전사)
- 판정: ☑ 조건부 통과 / ☐ 통과 / ☐ 반려
- 발견 이슈:
  - [MED] `tests/test_config.py:26` — 깨끗한 clone에는 ignore된 `data/` 디렉터리가 없어 `test_all_paths_exist`·`test_self_test_passes` 2건 실패 (51개 중 49 통과)
  - [MED] `scripts/core/task_spec.py:57`, `scripts/core/agent_result.py:49` — 잘못된 타입 입력 시 `validate()`가 오류 목록 대신 `TypeError`/`AttributeError`로 중단, `from_dict(None)`도 예외
  - [LOW] `model_decision.schema.json:16` — `selected_provider`가 단순 문자열이라 레지스트리에 없는 provider도 스키마 통과
- 필수 수정:
  1. 깨끗한 clone에서도 51개 테스트 전부 통과하도록 경로 존재성 테스트 수정
  2. TaskSpec·AgentResult의 잘못된 타입/비-dict 입력이 검증 경계에서 예외를 내지 않도록 보강
- 권고 사항:
  - `model_decision.schema.json`을 Python 클래스 없이 둔 결정은 현 단계에서 타당 (소비자 생기기 전 클래스는 불필요한 추상화)
  - PRIORITIES/TASK_ID_RE/VALID_STATUSES는 하드코딩 복제이나 테스트가 oracle을 직접 import해 드리프트를 감지하므로 현 단계 수용 가능
  - 과도한 추상화·AI-Slop 미발견

<details>
<summary>Codex 원문 보고 전문 (2026-07-11)</summary>

```
[Codex 검수 결과 — V3 Phase 1 (Stage 3~4)]
─────────────────
판정: 조건부 통과

발견 이슈:
• [심각도: MED] tests/test_config.py:26 — 깨끗한 clone에는 ignore된 `data/` 디렉터리가 없으므로 `test_all_paths_exist`와 `test_self_test_passes`가 실패합니다. 요구된 51개 테스트 중 2개가 실패했습니다.
  → 런타임 디렉터리의 존재를 필수화하지 않거나, 테스트 fixture에서 임시 경로를 구성해 clone 상태와 무관하게 검증하세요.

• [심각도: MED] scripts/core/task_spec.py:57, scripts/core/agent_result.py:49 — 잘못된 타입이 들어오면 `validate()`가 오류 목록을 반환하지 않고 `TypeError`/`AttributeError`로 중단됩니다. `from_dict(None)`도 양쪽 모두 예외를 냅니다.
  → 문자열·mapping 타입을 먼저 검사하고, 비정상 입력 테스트를 추가하세요.

• [심각도: LOW] ObsidianVault/10_AgentBus/contracts/model_decision.schema.json:16 — `selected_provider`가 단순 문자열이라 레지스트리에 없는 provider도 스키마를 통과합니다. 현재 테스트도 필드 존재 여부만 확인합니다.
  → 스키마 중복 enum보다는 실제 소비 단계에서 `model_registry.yaml` 키와 대조하고 그 테스트를 추가하세요.

필수 수정:
1. 깨끗한 clone에서도 지정된 51개 테스트가 모두 통과하도록 경로 존재성 테스트를 수정할 것.
2. `TaskSpec`·`AgentResult`의 잘못된 타입 및 비-dict 입력이 검증 경계에서 예외를 발생시키지 않도록 보강할 것.

권고 사항:
- `model_decision.schema.json`만 두고 Python 클래스를 만들지 않은 결정은 현 단계에서 타당합니다. 실제 소비자가 생기기 전 클래스 추가는 불필요한 추상화입니다.
- `PRIORITIES`, `TASK_ID_RE`, `VALID_STATUSES`는 런타임에 oracle을 참조하는 구조가 아니라 하드코딩 복제입니다. 다만 테스트가 oracle을 직접 import하여 드리프트를 감지하므로 현재 단계에서는 수용 가능합니다.
- 요청 범위에서 과도한 추상화, 사용하지 않는 클래스·인터페이스 등 뚜렷한 AI-Slop은 발견하지 못했습니다.

독립 재검증 수행 내역:
- `git diff df7c827..25fdc7d`: 14개 파일, +873줄 확인 및 전체 변경 검토.
- `git diff --check df7c827..25fdc7d`: 공백 오류 없음.
- `.gitignore` 전문 및 `git check-ignore --no-index` 검증:
  - inbox/claims/outbox 대표 경로: ignore됨.
  - contracts의 추적 파일·신규 대표 경로: ignore되지 않음.
  - 다른 Vault allowlist와의 유해한 상호작용 없음.
- oracle 직접 대조:
  - priority `low/normal/high` 일치.
  - task ID 생성 형식 일치.
  - 상태 7종이 `TRANSITIONS.keys() ∪ STATUS_TARGETS`와 일치.
- provider 대조: routing policy의 provider 값은 registry 키와 일치. 단, ModelDecision 스키마는 이를 강제하지 않음.
- `config/*.yaml`: 실제 시크릿 및 신규 절대경로 하드코딩 없음. env 변수 이름만 확인.
- 테스트 명령: `Ran 51 tests`, 결과 `FAILED (failures=2)`.
- 비정상 타입 직접 주입: `task_id=int`, `task_type=int`, `agent=int`, `from_dict(None)`에서 예외 재현.

미검증 항목:
- `git add --dry-run`은 안내된 clone 특성상 재현하지 않았습니다.
- CWD 밖 `error-patterns.md`는 CWD 외부 읽기 금지 지시 때문에 확인하지 않았습니다.
─────────────────
```

</details>

> 검수 완료 후 사용자에게 직접 보고. 사용자 승인 시 Claude가 Stage 6(Provider Adapter Layer) 착수.
> **현 상태: 조건부 통과 — 필수 수정 2건 이행 + 사용자 승인 전 Stage 6 금지 유지.**

---

## 6. 필수 수정 이행 + 재검수 요청 (2026-07-11, 사용자 승인 후 Claude 이행)

- 수정 커밋: `bdb436d` / diff 범위: `git diff 25fdc7d..bdb436d` (6 files)
- 필수 수정 1 이행: `scripts/core/config.py`에 `RUNTIME_KEYS`(현재 `data`뿐) 도입 — 런타임 생성·gitignore 경로는 `self_test()`와 `test_all_paths_exist`에서 존재 비필수화 (존재하면 디렉터리여야 함은 유지)
- 필수 수정 2 이행: `TaskSpec`/`AgentResult`의 `validate()`에 문자열 타입 검사 선행(`task_id`/`task_type`/`agent`), `from_dict()`는 비-dict 입력(`None` 포함) 시 예외 대신 필수 필드 `""`인 invalid 인스턴스 반환 → `validate()`가 위반 보고. 비정상 입력 테스트 8건 추가 (`InvalidInputTests` × 2 파일)
- Claude 측 증거:
  - `python -X utf8 -m unittest tests.test_config tests.test_task_spec tests.test_agent_result` → `Ran 59 tests — OK` (기존 51 + 신규 8)
  - clean clone 재현: `data/` 없는 일회용 clone(scratchpad)에서 동일 명령 → `Ran 59 tests — OK`

### 6.1 Codex 재검수 결과 기입란 (Codex가 채움)

- 검수일: 2026-07-11 (Codex CLI 0.144.0, 일회용 clone HEAD=bdb436d, data/ 부재 환경. Codex 최종 메시지를 Claude가 그대로 전사)
- 판정: ☑ 조건부 통과 / ☐ 통과 / ☐ 반려 — "필수 수정 2건은 모두 이행. 단 self_test()에 LOW급 false-negative 신규 발생"
- 발견 이슈:
  - [LOW] `scripts/core/config.py:117` — 런타임 경로가 일반 파일로 존재해도 실패에서 제외됨 (임시 파일 주입 시 `[MISS]` 출력하며 `self_test()==0` 재현) → `key not in RUNTIME_KEYS or path.exists()` 조건 + 회귀 테스트 요구
  - [LOW] diff 범위 표기 — `25fdc7d..bdb436d`는 실제 5커밋/14파일(일일 데이터·수집 커밋 포함). 단 `bdb436d` 단독은 정확히 6파일로 **커밋 자체의 범위 오염 없음**
- 요청 항목 판단: RUNTIME_KEYS=`{"data"}` 분류 타당 / from_dict invalid 인스턴스 계약 타당(소비자는 현재 테스트뿐) / selected_provider LOW는 범위 밖 유지가 맞음 / AI-Slop 미발견
- 재검증 수행 내역 (Codex 직접 실행):
  - `git show --stat bdb436d`: 6 files +81/-13, 무관 변경 없음
  - 테스트: `Ran 59 tests — OK` (`DATA_EXISTS=False` 환경)
  - 비정상 타입 직접 주입(task_id/task_type/agent=int, from_dict(None) 양쪽): 전부 `exception=NONE`, 오류 목록/invalid 인스턴스 반환
  - 임시 일반 파일을 data 경로로 주입: `셀프테스트 PASS`(false-negative) 재현 → 위 LOW 근거
  - `git diff --check`: 공백 오류 없음

### 6.2 재검수 LOW 보완 이행 (2026-07-11, Claude)

- `config.py` self_test: 런타임 키는 "아예 없음"만 허용 — 일반 파일로 존재하면 실패 처리 (`key not in RUNTIME_KEYS or path.exists()`)
- 회귀 테스트 `test_runtime_path_as_regular_file_fails` 추가 (임시 일반 파일 주입 → `self_test()==1` 검증)
- 증거: `Ran 60 tests — OK`
- 나머지 LOW(diff 범위 표기)는 문서 사안 — `bdb436d` 단독 범위가 정본이며 본 문서에 명기함

> **현 상태: 필수 수정 2건 + 재검수 LOW 보완 이행 완료. Stage 6 착수는 사용자 승인 대기.**
