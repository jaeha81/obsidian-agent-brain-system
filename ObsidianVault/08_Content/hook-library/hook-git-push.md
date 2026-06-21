---
id: IMPL-RA-07
type: hook-template
trigger: git-push
status: active
created: 2026-06-10
source: review-automation-protocol.md Phase 2
tags: [#hook, #automation, #git]
---

# Hook: git push 알림

## 트리거 조건
- `git push origin master` 완료 직후
- Claude Code PostToolUse:Bash 훅 또는 Trigger.dev `onGitPush` Job

## 메시지 템플릿

### Discord 알림 (짧은 포맷)
```
🚀 **[git push]** {{branch}} → {{remote}}
📦 {{commit_count}}개 커밋 | {{files_changed}}개 파일
🔗 {{commit_hash_short}}: {{commit_message}}
⏱ {{timestamp}}
```

### Obsidian 로그 (05_Logs/push-log.md append)
```markdown
## {{date}} {{time}} — push

- branch: {{branch}}
- commits: {{commit_count}} ({{commit_hash_short}})
- message: {{commit_message}}
- files: {{files_changed}} changed, +{{insertions}}/-{{deletions}}
```

## 변수 목록

| 변수 | 출처 | 예시 |
|------|------|------|
| `{{branch}}` | `git rev-parse --abbrev-ref HEAD` | `master` |
| `{{remote}}` | git push 대상 | `origin` |
| `{{commit_count}}` | `git log origin/master..HEAD --oneline \| wc -l` | `3` |
| `{{commit_hash_short}}` | `git rev-parse --short HEAD` | `388c764` |
| `{{commit_message}}` | `git log -1 --pretty=%s` | `feat: 태블릿 음성 인테이크` |
| `{{files_changed}}` | `git diff --stat` | `4 files changed` |
| `{{timestamp}}` | ISO 8601 | `2026-06-10T08:14:45+09:00` |

## Trigger.dev Job 참조
→ `scripts/trigger_jobs/job-git-push.js`

*Related: [[technical-patterns-hub]]*

