---
type: system-doc
status: active
created: 2026-05-31
owner: Bucky
tags:
  - #status/active
---

# Vault 태그 표준 (TAG_STANDARD)

art-1/art-2 기반으로 설계된 계층형 태그 체계. 기존 YAML_STANDARD.md의 필드 체계와 호환.

---

## 태그 5대 분류

### 1. area 태그 — 주제 영역

| 태그 | 용도 |
|------|------|
| `#area/gpt_feedback` | GPT/오늘의 플러스 피드백 기록 |
| `#area/ai_automation` | AI 자동화 시스템 |
| `#area/make_com` | Make.com 워크플로우 |
| `#area/obsidian_brain` | Obsidian 지식관리 시스템 |
| `#area/interior_design` | 인테리어 디자인 |
| `#area/construction` | 시공/감리 |
| `#area/field_management` | 현장관리 |
| `#area/client_consulting` | 견적/상담/고객 관리 |
| `#area/vendor_meeting` | 협력사/미팅 관리 |
| `#area/content_monetization` | 콘텐츠 수익화 |
| `#area/web_revenue` | 웹/광고 수익 |
| `#area/business_model` | 사업화 아이디어/모델 |
| `#area/stock_investment` | 주식 투자 |
| `#area/crypto_investment` | 가상화폐 투자 |
| `#area/personal_growth` | 개인 성장/학습 |
| `#area/research` | 참고자료/리서치 |

### 2. type 태그 — 자료 유형

| 태그 | 용도 |
|------|------|
| `#type/chat` | GPT 채팅 기록 |
| `#type/feedback` | 피드백/회고 |
| `#type/idea` | 아이디어 |
| `#type/project` | 프로젝트 |
| `#type/workflow` | 워크플로우 |
| `#type/meeting` | 미팅 기록 |
| `#type/client` | 클라이언트 정보 |
| `#type/estimate` | 견적서 |
| `#type/field_note` | 현장 노트 |
| `#type/strategy` | 전략 문서 |
| `#type/template` | 템플릿 |
| `#type/reference` | 참고자료 |
| `#type/action` | 실행 항목 |

### 3. status 태그 — 진행 상태

> 기존 YAML `status` 필드와 연동. 태그로도 표현 가능.

| 태그 | 의미 |
|------|------|
| `#status/inbox` | 분류 전 대기 |
| `#status/active` | 현재 진행 중 |
| `#status/review_needed` | 검토 필요 |
| `#status/waiting` | 외부 대기 |
| `#status/completed` | 완료 |
| `#status/hold` | 보류 |
| `#status/archive` | 아카이브 |

### 4. priority 태그 — 우선순위

| 태그 | 의미 |
|------|------|
| `#priority/p1` | 즉시 실행 가능 |
| `#priority/p2` | 검토 후 실행 |
| `#priority/p3` | 장기 참고 |
| `#priority/hold` | 보류 |

### 5. source 태그 — 자료 출처

| 태그 | 의미 |
|------|------|
| `#source/chatgpt` | ChatGPT 채팅 |
| `#source/today_plus` | 오늘의 플러스 |
| `#source/meeting` | 미팅 |
| `#source/youtube` | 유튜브 |
| `#source/web` | 웹 |
| `#source/client` | 클라이언트 |
| `#source/field` | 현장 |
| `#source/idea` | 아이디어 |
| `#source/discord` | Discord 채널 |
| `#source/voice` | 음성 노트 |
| `#source/api` | API/자동화 유입 |

### 6. department 태그 — 담당 부문

> `YAML_STANDARD.md`의 `department` 필드와 1:1 대응. 노트가 복수 부문에 속하면 태그도 복수 부여.

| 태그 | 의미 |
|------|------|
| `#department/ai_automation` | AI·자동화 시스템 |
| `#department/interior` | 인테리어 사업 |
| `#department/consulting` | 클라이언트 컨설팅 |
| `#department/content` | 콘텐츠 제작 |
| `#department/business_dev` | 사업 개발·제안 |
| `#department/system` | 시스템·인프라·에이전트 운영 |

---

## Graph View 그룹 설정

아래 검색식을 `.obsidian/graph.json` colorGroups에 적용.

| 그룹명 | 검색식 |
|--------|--------|
| GPT 피드백 | `tag:#area/gpt_feedback` |
| AI 자동화 | `tag:#area/ai_automation` |
| Make.com | `tag:#area/make_com` |
| Obsidian Brain | `tag:#area/obsidian_brain` |
| 인테리어 | `tag:#area/interior_design OR tag:#area/construction` |
| 현장관리 | `tag:#area/field_management` |
| 클라이언트 | `tag:#area/client_consulting` |
| 협력사 | `tag:#area/vendor_meeting` |
| 수익화 | `tag:#area/content_monetization OR tag:#area/web_revenue` |
| 사업모델 | `tag:#area/business_model` |
| 투자 | `tag:#area/stock_investment OR tag:#area/crypto_investment` |
| 실행중 | `tag:#status/active` |
| 검토필요 | `tag:#status/review_needed` |
| 보관 | `tag:#status/archive` |

---

## 적용 규칙

- 신규 노트 작성 시 `area` + `type` + `status` 태그 최소 1개씩 부여
- `department` 태그는 복수 부문 소속 시 복수 부여 (YAML `department` 리스트와 동기화)
- `priority/p1` 태그는 즉시 실행 가능한 항목에만 사용
- 기존 태그는 제거하지 않고 병존 (기존 노트 소급 적용 금지)
- Dataview 쿼리는 태그 기반으로 작성 (폴더 기반 병용 가능)
