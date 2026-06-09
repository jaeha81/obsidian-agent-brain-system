---
id: IMPL-RA-10
type: hook-template
trigger: session-end
status: active
created: 2026-06-10
source: review-automation-protocol.md Phase 2
tags: [#hook, #automation, #session]
---

# Hook: 세션종료 알림

## 트리거 조건
- Claude Code 세션 종료 또는 `/goal clear` 완료 시
- `PostSession` 훅 또는 Trigger.dev `onSessionEnd` Job

## 메시지 템플릿

### Discord 알림
```
🔴 **[세션종료]** Claude Code 비활성화
✅ 완료: {{completed_tasks}}
⏳ 미완료: {{pending_tasks}}
💾 메모: {{session_note}}
⏱ 소요: {{duration_min}}분 | {{timestamp}}
```

### Handoff 메모 (자동 생성)
```
이전 세션 메모: memory/project_session_{{date}}.md
완료: {{completed_summary}}
다음 우선순위:
{{next_priorities}}
```

## 변수 목록

| 변수 | 출처 | 예시 |
|------|------|------|
| `{{session_id}}` | Claude Code env | `abc123ef` |
| `{{completed_tasks}}` | user_checklist.json done 항목 | `CL-025, CL-026` |
| `{{pending_tasks}}` | user_checklist.json pending 항목 | `CL-027, CL-028` |
| `{{session_note}}` | 마지막 완료 보고 요약 | `태블릿 음성 인테이크 구현 완료` |
| `{{duration_min}}` | 세션 시작~종료 시간 차이 | `45` |
| `{{next_priorities}}` | 잔여 P0/P1 태스크 | `1. [P1] T025 파이프라인` |
| `{{timestamp}}` | ISO 8601 | `2026-06-10T09:00:00+09:00` |

## Trigger.dev Job 참조
→ `scripts/trigger_jobs/job-session-end.js`
