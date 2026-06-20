---
type: system-doc
status: active
created: 2026-06-18
owner: Bucky
tags:
  - status/active
  - area/knowledge
  - relay
  - llm-wiki
  - pipeline
---

# Knowledge Relay — Raw→Wiki 지식 릴레이 프로토콜

> Phase 1 (LLM Wiki 진화 루프 실행 가이드)
> 원칙 출처: [[CLAUDE.md 지식 진화 루프 규칙]] | 영상: 칼퇴연구소 AI생산성, 2026-06-11

---

## 릴레이란?

외부 지식(YouTube, X, Discord, Daily Plus 등)을 **검증·정제하여 Wiki로 연결**하는 파이프라인.

> "자료를 많이 모으는 것보다 중요한 건 AI가 읽고 활용할 수 있는 구조로 정리하는 것."

---

## 게이트웨이 기준 (Wiki 진입 필터)

모든 raw 자료는 아래 기준을 **하나 이상** 통과해야 Wiki에 진입한다.

| 기준 | 설명 | 판단 예시 |
|------|------|-----------|
| **재사용성** | 이후 프로젝트·세션에서 반복 참조될 것인가? | ✅ 설계 패턴 / ❌ 일회성 링크 |
| **행동 유발성** | 이 지식이 실행 결정을 바꾸는가? | ✅ API 요금 변경 / ❌ 일반 뉴스 |
| **Bucky 활용성** | 에이전트가 Context Pack에서 인용 가능한가? | ✅ 룰·플랜·패턴 / ❌ 감성 글 |

> ❌ 통과 못하면 `01_RAW/`에 `#unprocessed` 태그로 남기고 위키로 올리지 않는다.

---

## 릴레이 파이프라인 (4단계)

```
[외부 소스] → 01_RAW/ → (게이트 통과?) → 03_Knowledge/ or 04_Wiki/ → 연결
```

### Step 1 — 수집 (Capture)
- 도구: Discord `jh-지식인테이크` 채널, Bucky capture, 수동 저장
- 저장 위치: `01_RAW/` (날짜-소스명 파일명)
- YAML: `source`, `source_type`, `status: raw`

### Step 2 — 게이트 검사 (Gate Check)
- 위 **게이트웨이 기준** 3개 검토
- 중복 여부: `03_Knowledge/`, `04_Wiki/`에서 동일 주제 검색
  - 70%+ 겹침 → 기존 노트에 섹션 추가 (새 파일 금지)
- 통과 실패 → `#unprocessed` 태그 추가, 파이프라인 중단

### Step 3 — 정제 (Distill)
- 핵심 인사이트만 추출 (전체 내용 복사 금지)
- 실행 포인트 / 적용 아이디어 섹션 추가
- YAML 업데이트: `status: knowledge` 또는 `status: wiki`
- `source` 원본 경로 보존

### Step 4 — 연결 (Link)
- 관련 노트와 `[[wikilink]]` 연결
- 해당 Context Pack에 항목 추가 (해당 시)
- 원본 `01_RAW/` 파일에 `#processed` 태그 추가

---

## 소스별 릴레이 템플릿

### YouTube 영상

```yaml
source: "https://youtu.be/<id>"
source_type: youtube
channel: "<채널명>"
publish_date: "YYYYMMDD"
status: knowledge
```

저장 경로: `03_Knowledge/YYYY-MM-DD-yt-<제목>.md`

### Daily Plus 카드

```yaml
source: "daily-plus/YYYY-MM-DD.md (Card N)"
source_type: today_plus
status: knowledge
```

저장 경로: `03_Knowledge/YYYY-MM-DD-dp-<주제>.md`

### X (트위터) 팁

```yaml
source: "<tweet URL 또는 x>"
source_type: x
status: knowledge
```

저장 경로: `03_Knowledge/YYYY-MM-DD-x-<주제>.md`

### Discord 지식 인테이크

```yaml
source: discord
source_type: discord
status: knowledge
```

저장 경로: `03_Knowledge/YYYY-MM-DD-dc-<주제>.md`

---

## 볼트 구조 결정 (LLM Wiki 원칙)

> JH 시스템은 **단일 볼트** 방식을 유지한다.

- 이유: 부서간 연결 링크가 끊어지지 않음, Bucky가 전체 컨텍스트 접근 가능
- 대신 `department` YAML 필드로 논리적 분리 (`[ai_automation]`, `[interior]` 등)
- 민감 데이터: `09_Archive/private/` 또는 `.gitignore`로 처리

---

## 주간 병합 패스 (Weekly Relay Pass)

매주 1회 (권장: 월요일):

- [ ] `01_RAW/` 중 7일+ 된 `#unprocessed` 파일 10개 → 게이트 재검토
- [ ] `00_Inbox/` 중 7일+ 항목 → 처리 또는 `09_Archive/`로 이동
- [ ] 중복 노트 발견 시 병합 후 원본에 `#merged-into: <대상파일>` 기록
- [ ] 가장 오래된 미처리 RAW 중 위키 가치 있는 것 3개 → 정제 완료

---

## 릴레이 금지 패턴

- 게이트 미통과 자료를 Wiki에 직접 복사
- 원본 URL 없이 요약만 저장 (출처 보존 필수)
- 동일 주제 노트를 중복 생성 (기존 노트 업데이트 우선)
- `status: raw` 파일을 Bucky Context Pack에서 직접 참조

---

## 관련 파일

- [[YAML_STANDARD]] — source, source_type, department 필드 규칙
- [[ROUTING_RULES]] — Layer 1/2/3 MCP 접근 계층
- [[AI_BRAIN_LAYER_STRATEGY]] — 기억 레이어 전략 프레임
- [[sync-protocol]] — AgentBus 동기화 프로토콜
