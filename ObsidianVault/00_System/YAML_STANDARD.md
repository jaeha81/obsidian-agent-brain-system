---
type: system-doc
status: active
created: 2026-05-30
owner: Bucky
tags:
  - #status/active
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
| `source` | string | 입력 출처 (URL 또는 파일 경로 허용) | `discord`, `voice`, `manual`, `api`, `web`, `file`, `chatgpt`, `today_plus`, `meeting`, `youtube`, `x`, `notion`, `newsletter`, `llm_wiki`, `client`, `field`, `idea`, `"https://youtu.be/..."`, `"daily-plus/2026-06-10.md"` |
| `source_type` | string | 출처 범주 (source가 URL일 때 필수) | `youtube`, `x`, `notion`, `newsletter`, `discord`, `voice`, `web`, `file`, `manual`, `today_plus`, `meeting`, `llm_wiki` |
| `department` | list | 담당 부문 — **반드시 YAML 리스트 형식** | `[ai_automation, interior]` — 단일도 리스트: `[system]` |
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

## 지식관리 선택 필드 (신규 노트 권장)

> art-1/art-2 기반 지식 분류용 선택 필드. 필수 필드(type/status/created)는 불변.

| 필드 | 타입 | 설명 | 예시 |
|------|------|------|------|
| `category` | string | 대분류 | `ai_automation`, `interior_design`, `business_model` |
| `subcategory` | string | 세부 분류 | `make_com`, `client_consulting` |
| `keywords` | list | 핵심 키워드 3~10개 | `["AI", "자동화", "Make.com"]` |
| `summary` | string | 한 줄 요약 | `"Make.com 웹훅 자동화 설계"` |
| `next_action` | string | 다음 실행 행동 | `"Bucky에게 검토 요청"` |
| `review_date` | ISO date | 재검토 예정일 | `2026-06-10` |
| `business_value` | string | 사업화 가치 | `high`, `medium`, `low` |
| `automation_value` | string | 자동화 가치 | `high`, `medium`, `low` |
| `confidence` | string | 신뢰도 | `high`, `medium`, `low` |

### `department` 유효값

| 값 | 설명 |
|----|------|
| `ai_automation` | AI·자동화 시스템 |
| `interior` | 인테리어 사업 |
| `consulting` | 클라이언트 컨설팅 |
| `content` | 콘텐츠 제작 |
| `business_dev` | 사업 개발·제안 |
| `system` | 시스템·인프라·에이전트 운영 |
| `knowledge` | 지식 관리·볼트·Raw→Wiki 파이프라인 |
| `revenue` | 수익화·매출 관련 논의 |

다중 부문 소속 노트는 리스트로 기재: `department: [ai_automation, system]`

> ⚠️ **YAML 리스트 형식 필수**: `department: ai_automation` 단일 문자열은 validator 오류 → 반드시 `department: [ai_automation]`

---

## source / source_type 사용 가이드 (2026-06-18 추가)

| 상황 | source 값 | source_type 값 |
|------|-----------|----------------|
| Discord 메시지 | `discord` | 생략 |
| YouTube 영상 | URL (`"https://youtu.be/..."`) | `youtube` |
| X(트위터) 포스트 | URL 또는 `x` | `x` |
| Daily Plus 카드 | `"daily-plus/YYYY-MM-DD.md (Card N)"` | `today_plus` |
| LLM Wiki 정제 콘텐츠 | `llm_wiki` | `llm_wiki` |
| Notion 임포트 | URL 또는 `notion` | `notion` |
| 뉴스레터 | URL 또는 `newsletter` | `newsletter` |

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
