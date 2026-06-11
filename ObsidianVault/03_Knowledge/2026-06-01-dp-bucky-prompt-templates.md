---
type: knowledge-note
date: 2026-06-01
source: daily-plus
category: agent-prompting
tags:
  - "#area/ai_automation"
  - "#status/staged"
summary: Bucky용 범용 프롬프트 10종 — 메모 분류, 값 추출, 영상 요약, 파일 흡수, 정책 점검 등
status: staged
next_action: Bucky 패킷 확인 후 실제 운영 프롬프트에 선택 적용
---

# Bucky 프롬프트 템플릿 모음 10종

자주 쓰는 작업을 그대로 복붙해서 쓸 수 있는 프롬프트 모음. 출력 형식 한 줄을 포함해 Obsidian/스프레드시트/DB로 파싱 가능.

## 1. 메모 분류 (태깅)

```
태그 후보 5개를 JSON 배열로 출력하라.
입력: {memo_text}
출력 형식: {"tags": ["tag1", "tag2", ...]}
```

## 2. 핵심 값 추출

```
아래 텍스트에서 금액, 날짜, 담당자, 장소를 추출하라.
입력: {text}
출력 형식: {"amount": "", "date": "", "person": "", "location": ""}
```

## 3. 영상/음성 요약

```
아래 전사 텍스트를 3문장으로 요약하라.
입력: {transcript}
출력 형식: {"summary": "...", "action_items": ["...", ...]}
```

## 4. 파일 흡수 (Obsidian ingestion)

```
아래 텍스트를 Obsidian 노트 프런트매터 + 본문으로 변환하라.
입력: {raw_text}
출력 형식: YAML frontmatter + markdown body
필수 필드: type, source, created, tags, summary
```

## 5. 정책 점검

```
아래 계획이 BUCKY_CONTEXT.md의 저장 경계 규칙을 위반하는지 확인하라.
입력: {plan_text}
출력 형식: {"violation": true/false, "reason": "...", "allowed": true/false}
```

## 6. 일일 스냅샷 생성

```
오늘 완료/진행/차단 항목을 3섹션으로 정리하라.
입력: {task_list}
출력 형식: {"done": [...], "in_progress": [...], "blocked": [...]}
```

## 7. 승인 게이트 판단

```
아래 액션이 사용자 승인이 필요한지 판단하라 (commit/push/delete/deploy/send 포함 여부 기준).
입력: {action_description}
출력 형식: {"approval_required": true/false, "reason": "..."}
```

## 8. 견적 항목 추출

```
아래 현장 메모에서 공종, 자재, 수량, 단가를 추출하라.
입력: {site_memo}
출력 형식: [{"item": "", "material": "", "qty": 0, "unit_price": 0}]
```

## 9. 콘텐츠 후크 5개 생성

```
아래 주제로 숏폼 영상 훅 5개를 생성하라 (한국어, 15초 이내).
주제: {topic}
출력 형식: ["훅1", "훅2", ...]
```

## 10. 에이전트 핸드오프 패킷 생성

```
아래 작업을 Bucky Goal Mode 패킷으로 변환하라.
입력: {task_description}
출력 형식: {"goal": "", "baseline": "", "target_state": "", "done_when": "", "constraints": ""}
```

## 적용 시 주의

- staged 상태. 실제 Bucky 운영 프롬프트 변경 전 사용자 확인 필요.
- 개별 프롬프트는 Discord 내 `/bucky prompt <번호> <입력>` 형식으로 호출 가능하도록 설계.
