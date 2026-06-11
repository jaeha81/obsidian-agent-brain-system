---
type: staging
status: review-required
created: 2026-06-01
source: daily-plus 2026-06-01 Card 11
owner: bucky
tags:
  - #status/review-required
  - #area/business_model
summary: "⚠️ Bucky/Claude/Codex 역할 경계에 영향. 구현 전 검토 필요."
category: business_model
next_action: review
---

# 버키용 프롬프트 템플릿 모음 (스테이징)

> ⚠️ Bucky/Claude/Codex 역할 경계에 영향. 구현 전 검토 필요.

Card 11 기반. 10개 프롬프트 템플릿을 역할별로 분류해 스테이징. 사용자 승인 후 `BUCKY_CONTEXT.md` 또는 Context Pack에 반영.

---

## 1. 메모 분류 (태깅)

```
입력: {{raw_note}}
작업: 아래 태그 중 최대 3개 선택해 YAML frontmatter로 반환.
허용 태그: [project, client, strategy, ai_automation, estimate, site, vendor, material, content]
출력 형식:
---
tags: [tag1, tag2]
summary: 한 줄 요약
---
```

---

## 2. 값 추출 (구조화)

```
입력: {{unstructured_text}}
작업: 금액, 날짜, 인물명, 주소를 JSON으로 추출.
출력 형식:
{ "amounts": [], "dates": [], "people": [], "addresses": [] }
```

---

## 3. 동영상/음성 요약

```
입력: {{transcript_text}}
작업: 핵심 결정사항 3개, 다음 액션 2개를 bullet로 요약.
출력 형식:
결정사항:
- ...
다음 액션:
- ...
```

---

## 4. 파일 흡수 (Ingestion) 라우팅

```
입력: {{filename}}, {{content_preview}}
작업: Vault 폴더 판단 (00_Inbox~10_AgentBus 중 하나).
출력 형식: { "target_folder": "...", "reason": "..." }
```

---

## 5. 정책 점검

```
입력: {{policy_text}}
작업: BUCKY_CONTEXT.md 금지사항과 충돌 여부 확인.
출력 형식: { "conflict": true|false, "items": ["..."] }
```

---

## 6~10. (확장 예정)

추가 템플릿은 검토 후 순차 등록.

---

## 검토 체크리스트

- [ ] 각 프롬프트가 Claude/Codex/Bucky 역할 경계를 침범하지 않는지 확인
- [ ] 출력 형식이 기존 Obsidian frontmatter 규칙과 호환되는지 확인
- [ ] 승인 후 `ObsidianVault/06_Context_Packs/bucky-prompt-library.md`로 이동
