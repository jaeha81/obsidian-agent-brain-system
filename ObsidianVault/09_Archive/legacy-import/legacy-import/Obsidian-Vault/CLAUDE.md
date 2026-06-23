# LLM Wiki Schema — JH 개발 볼트

> 이 파일은 LLM Wiki 에이전트의 운영 스키마다.
> 개발 자산 전용 볼트 (Obsidian Vault) 의 wiki 레이어를 관리한다.
> 수정 시 반드시 wiki/log.md에 기록하라.

---

## 두 볼트 구조

| 볼트 | 역할 | 스키마 |
|------|------|--------|
| **Obsidian Vault (이곳)** | 개발 브레인 — 패턴·결정·아키텍처·에이전트 복리 지식 | 이 CLAUDE.md |
| **OBSIDIAN-SECOND** | 지식 브레인 — 개념·조사·전략·LLM 지식 | G:\내 드라이브\...\CLAUDE.md |

> 개발 브레인은 "우리가 어떻게 만드는가"를 축적한다.
> 지식 브레인은 "우리가 무엇을 아는가"를 축적한다.

---

## 디렉토리 구조

```
C:\Users\user1\Documents\Obsidian Vault\
├── CLAUDE.md              # 이 스키마 파일
├── wiki/                  # LLM이 작성·유지하는 위키 (절대 수동 편집 금지)
│   ├── index.md           # 마스터 인덱스 (모든 페이지 카탈로그)
│   ├── log.md             # 시간순 활동 로그 (append-only)
│   ├── overview.md        # 전체 합성 개요
│   └── [topic].md         # 개별 개념/엔티티/패턴/결정 페이지
├── raw/                   # 불변 원본 소스 (LLM이 읽기만 함, 절대 수정 금지)
│   ├── memories/          # JH 지식 백과사전 (Claude 대화 누적)
│   │   ├── 00_overview.md
│   │   ├── 01_personal_career.md
│   │   ├── 02_dev_workflow.md
│   │   ├── 03_tech_stack.md
│   │   ├── 04_jh_keanu.md
│   │   ├── 05_jh_estimate_ai.md
│   │   ├── 06_jh_harness.md
│   │   ├── 07_jh_brain.md
│   │   ├── 08_agent_hub_3d.md
│   │   ├── 09_past_projects.md
│   │   └── 10_business_strategy.md
│   ├── articles/          # 웹 아티클, 클리핑
│   ├── papers/            # 논문, 보고서
│   ├── notes/             # 개인 메모, 회의록
│   └── assets/            # 이미지, PDF 등
├── 00_Inbox/              # [RAW] 미분류 신규 소스
├── 01_Projects/           # [RAW] 프로젝트 문서, 에이전트 정의
├── 02_Architecture/       # [RAW] 아키텍처 설계문서
├── 03_Prompts/            # [RAW] 프롬프트 템플릿
├── 04_Issues/             # [RAW] 버그·이슈 기록
├── 05_Logs/               # [RAW] 세션 로그, 결정 기록
├── 06_Deploy/             # [RAW] 배포 기록
└── 07_Archive/            # [RAW] 완료 아카이브
```

> **raw/ 폴더**: 불변 원본 소스 레이어 — LLM이 읽기만 함, 절대 수정 금지.
> **[RAW] 폴더(00~07)**: 개발 자산 소스 레이어 — 동일 규칙 적용.

---

## 세션 시작 프로토콜

새 세션이 열리면 반드시 이 순서로 시작한다:

1. `wiki/index.md` 읽기 → 현재 위키 상태 파악
2. `wiki/log.md` 마지막 5개 항목 확인 → 최근 활동 파악
3. 상태 요약 브리핑 (1~3줄)
4. "무엇을 할까요?" 대기

---

## 핵심 오퍼레이션

### 1. INGEST (소스 추가)

새 소스가 들어오면:

```
[INGEST 흐름]
1. 소스 읽기 (볼트 내 파일 또는 URL)
2. 핵심 포인트 파악 및 논의
3. wiki/source-[slug].md — 소스 요약 페이지 생성
4. 관련 concept/entity/pattern 페이지 업데이트 (교차 참조 포함)
5. wiki/index.md 업데이트
6. wiki/log.md에 ingest 항목 추가
```

**소스 요약 페이지 형식:**
```markdown
---
type: source
category: session | architecture | issue | project | article
date_added: YYYY-MM-DD
origin: 05_Logs/daily/ | 01_Projects/ | 04_Issues/ | ...
tags: [tag1, tag2]
---

# [소스 제목]

## 한 줄 요약
[핵심 내용 1줄]

## 핵심 포인트
- ...

## 위키에 통합된 내용
- [[concept-page]] 업데이트: ...
- [[pattern-page]] 추가: ...

## 관련 페이지
- [[...]]
```

### 2. QUERY (질문 및 탐색)

질문이 들어오면:

```
[QUERY 흐름]
1. wiki/index.md에서 관련 페이지 식별
2. 관련 페이지 읽기 (최대 10개)
3. 답변 합성
4. 좋은 답변은 wiki/ 페이지로 저장 제안
5. wiki/log.md에 query 항목 추가
```

### 3. LINT (건강 검진)

`/lint` 명령 시:

```
[LINT 체크리스트]
□ 모순 감지 — 페이지 간 충돌하는 주장
□ 오래된 클레임 — 새 결정이 반박하는 기존 내용
□ 고아 페이지 — 인바운드 링크 없는 페이지
□ 미생성 페이지 — 언급되지만 페이지 없는 개념
□ 누락 교차 참조 — 연결되어야 할 페이지들
□ 데이터 갭 — 새 세션 로그로 보완 가능한 공백
```

---

## 위키 페이지 타입

| 타입 | 파일명 패턴 | 내용 |
|------|------------|------|
| **개념** | `wiki/concept-[name].md` | 개발 아이디어, 원칙, 접근법 |
| **엔티티** | `wiki/entity-[name].md` | 에이전트, 프로젝트, 시스템, 도구 |
| **패턴** | `wiki/pattern-[name].md` | 검증된 코드/운영 패턴 |
| **결정** | `wiki/decision-[name].md` | 아키텍처 결정 (ADR) |
| **소스** | `wiki/source-[slug].md` | 인제스트된 소스 요약 |
| **비교** | `wiki/compare-[a]-vs-[b].md` | 두 대상 비교 |
| **합성** | `wiki/synthesis-[topic].md` | 주제 전체 합성 |
| **개요** | `wiki/overview.md` | 전체 위키 합성 |

---

## 위키 페이지 표준 형식

```markdown
---
type: concept | entity | pattern | decision | source | compare | synthesis
updated: YYYY-MM-DD
sources: [source-slug1, source-slug2]
tags: [tag1, tag2]
---

# [페이지 제목]

[현재 상태 기술 — 과거 이력이 아닌 현재 이해]

## 핵심 내용
...

## 관련 페이지
- [[page1]] — 관계 설명
- [[page2]] — 관계 설명

## 출처
- [[source-slug]] (날짜)
```

---

## index.md 형식

```markdown
# Wiki Index — JH 개발 볼트
> 마지막 업데이트: YYYY-MM-DD | 소스: N개 | 페이지: N개

## 엔티티 (Entities)
| 페이지 | 요약 | 업데이트 |

## 개념 (Concepts)
| 페이지 | 요약 | 소스수 | 업데이트 |

## 패턴 (Patterns)
| 페이지 | 요약 | 검증일 |

## 결정 (Decisions)
| 페이지 | 요약 | 날짜 |

## 소스 (Sources)
| 페이지 | 카테고리 | 추가일 |
```

---

## log.md 형식

```markdown
## [YYYY-MM-DD] ingest | 소스 제목
- 소스: [origin 경로]
- 생성: wiki/source-...md
- 업데이트: [[page1]], [[page2]]
- 핵심 발견: ...

## [YYYY-MM-DD] query | 질문 키워드
- 질문: "..."
- 참조 페이지: [[page1]], [[page2]]
- 결과: 인라인 답변 | 새 페이지 생성 → [[page]]

## [YYYY-MM-DD] lint | 건강 검진
- 문제: N개 발견
- 조치: ...
```

---

## 행동 규칙

1. **위키는 LLM이 쓴다** — 사용자는 소스와 방향만 제공한다
2. **원본은 불변** — 00_Inbox ~ 07_Archive 파일은 읽기만, 절대 수정하지 않는다
3. **교차 참조 항상** — 새 페이지 생성 시 기존 페이지와 연결한다
4. **log.md는 누락 없이** — 모든 ingest/query/lint는 기록한다
5. **index.md는 즉시 동기화** — 페이지 생성/수정 후 바로 업데이트한다
6. **좋은 답변은 보존** — 가치 있는 쿼리 결과는 wiki 페이지화 제안
7. **모순 발견 즉시 고지** — 새 소스가 기존 내용을 반박하면 명시적으로 알린다
8. **RAW 폴더 수정 금지** — 볼트 폴더(00~07)는 소스 레이어, wiki만 쓸 수 있다

---

## 슬래시 명령어

| 명령어 | 동작 |
|--------|------|
| `/ingest [파일경로 또는 URL]` | 소스 인제스트 시작 |
| `/query [질문]` | 위키 기반 질문 답변 |
| `/lint` | 위키 건강 검진 |
| `/status` | 현재 위키 통계 |
| `/overview` | 전체 합성 개요 갱신 |
| `/new [타입] [이름]` | 새 페이지 수동 생성 |

---

*스키마 버전: 1.0 | 생성: 2026-04-27 | 볼트: JH 개발 볼트 | 소유자: JH*

---

## InfraNodus Graph Layer Integration - 2026-05-12

Codex implemented the first InfraNodus graph layer for this Vault.

Operational additions:
- Obsidian plugin: `infranodus-graph-view`
- Claude Code MCP: `infranodus` via `npx -y infranodus-mcp-server`
- Graph memory: `infranodus/ontology/`, `infranodus/gap-analysis/`, `infranodus/graph-snapshots/`, `infranodus/mcp-logs/`
- Action outputs: `output/research-questions/`, `output/claude-instructions/`, `output/codex-review-targets/`, `output/todo/`

Rules:
1. Keep raw source material in `raw/`.
2. Keep stable synthesis in `wiki/`.
3. Keep graph-derived memory in `infranodus/`.
4. Keep action outputs in `output/`.
5. Do not store InfraNodus API keys in Obsidian notes, GitHub, or JH-SHARED.
6. Ask the user before sending sensitive JH data to external APIs.

Start here:
- `wiki/decision-adopt-infranodus-graph-layer.md`
- `wiki/pattern-graph-gap-driven-research.md`
- `output/claude-instructions/2026-05-12-infranodus-briefing.md`
