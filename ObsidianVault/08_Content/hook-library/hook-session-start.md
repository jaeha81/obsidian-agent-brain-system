---
id: IMPL-RA-09
type: hook-template
trigger: session-start
status: active
created: 2026-06-10
source: review-automation-protocol.md Phase 2
tags: [#hook, #automation, #session]
---

# Hook: 세션시작 알림

## 트리거 조건
- Claude Code 세션이 시작될 때
- `PreSession` 훅 또는 Trigger.dev `onSessionStart` Job

## 메시지 템플릿

### Discord 알림
```
🟢 **[세션시작]** Claude Code 활성화
📋 이전 세션: {{prev_session_id}}
🎯 Goal: {{session_goal}}
📅 {{date}} {{time}}
```

### Obsidian 세션 로그 (05_Logs/session-log.md append)
```markdown
## {{date}} {{time}} — 세션시작

- session_id: {{session_id}}
- prev_session: {{prev_session_id}}
- goal: {{session_goal}}
- context_packs: {{context_packs}}
```

## 변수 목록

| 변수 | 출처 | 예시 |
|------|------|------|
| `{{session_id}}` | Claude Code env | `abc123ef` |
| `{{prev_session_id}}` | memory/last_session | `zxy987` |
| `{{session_goal}}` | /goal 설정값 | `마저 다 진행해` |
| `{{context_packs}}` | context_pack_selector 결과 | `bucky-agent-os` |
| `{{date}}` | 현재 날짜 | `2026-06-10` |
| `{{time}}` | 현재 시각 | `08:14` |

## Trigger.dev Job 참조
→ `scripts/trigger_jobs/job-session-start.js`

*Related: [[technical-patterns-hub]]*
