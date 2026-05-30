---
type: system-doc
status: active
created: 2026-05-30
owner: Bucky
---

# Bucky Vault YAML 표준

Bucky 에이전트가 생성·검증하는 모든 Obsidian 노트의 frontmatter 필수/선택 필드 정의.

`scripts/yaml_validator.py`로 실제 파일을 검증할 수 있다.

---

## 필수 필드 (모든 노트 공통)

| 필드 | 타입 | 설명 | 예시 |
|------|------|------|------|
| `type` | string | 노트 유형 | `project`, `task`, `estimate`, `log`, `system-doc`, `context-pack`, `agent-result`, `bridge-test` |
| `status` | string | 현재 상태 | `draft`, `done`, `review`, `active`, `archive` |
| `created` | ISO date | 생성일 | `2026-05-30` |

## 선택 필드 (에이전트 생성 노트)

| 필드 | 타입 | 설명 | 예시 |
|------|------|------|------|
| `project` | string | 연관 프로젝트명 | `wishket-automation` |
| `client` | string | 고객명 (없으면 `-`) | `홍길동`, `-` |
| `source` | string | 입력 출처 | `discord`, `voice`, `manual`, `api` |
| `agent` | string | 작성 에이전트 | `Bucky`, `ClaudeCode`, `Codex` |
| `next_action` | string | 다음 행동 | `"Codex 검수 요청"` |
| `owner` | string | 담당자 | `Bucky`, `jaeha` |
| `updated` | ISO date | 마지막 수정일 | `2026-05-30` |
| `requires_approval` | bool | 에이전트 실행 전 승인 필요 여부 | `true`, `false` |

## 타입별 추가 필드

### `task` 타입

| 필드 | 설명 |
|------|------|
| `priority` | `high`, `medium`, `low` |
| `worker` | 담당 워커 (`ClaudeCode`, `Codex`, `Bucky`) |
| `task_id` | 고유 ID (`T001`, `IMPL-RA-001` 등) |
| `done_when` | 완료 조건 문자열 |

### `estimate` 타입

| 필드 | 설명 |
|------|------|
| `total_min` | 최소 견적 (만원) |
| `total_max` | 최대 견적 (만원) |
| `confidence` | 신뢰도 (0.0~1.0) |
| `platform` | `wishket`, `직접의뢰`, 기타 |

### `agent-result` 타입

| 필드 | 설명 |
|------|------|
| `task_ref` | 원본 태스크 파일명 |
| `worker` | 처리한 에이전트 |
| `success` | `true` / `false` |

---

## 금지 패턴

- `api_key`, `password`, `secret`, `token` 필드에 실제 값 입력 금지
- `client` 필드에 전화번호·주민번호 등 PII 직접 입력 금지 (ID 참조만 허용)
- `status: processing` 상태로 파일 커밋 금지 (in-flight 상태)

---

## 검증 명령

```bash
# 특정 폴더 검증
python -X utf8 scripts/yaml_validator.py ObsidianVault/10_AgentBus/inbox/

# 전체 Vault 검증
python -X utf8 scripts/yaml_validator.py ObsidianVault/

# 특정 파일
python -X utf8 scripts/yaml_validator.py ObsidianVault/10_AgentBus/inbox/my-task.md
```
