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

- 판정: ☐ 통과 / ☐ 조건부 통과 / ☐ 반려
- 발견 이슈:
- 필수 수정:
- 권고 사항:

> 검수 완료 후 사용자에게 직접 보고. 사용자 승인 시 Claude가 Stage 6(Provider Adapter Layer) 착수.
