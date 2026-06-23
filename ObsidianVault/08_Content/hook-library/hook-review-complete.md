---
id: IMPL-RA-11
type: hook-template
trigger: review-complete
status: active
created: 2026-06-10
source: review-automation-protocol.md Phase 2
tags: [#hook, #automation, #codex, #review]
---

# Hook: 검수완료 알림

## 트리거 조건
- Codex가 검수 완료 보고를 Discord에 전송할 때
- 키워드: "검수완료", "LGTM", "검수 결과", "Codex 검수"

## 메시지 템플릿

### Claude Code 피드백 (Discord #jh-태스크보드)
```
🔍 **[검수완료]** Codex 리뷰 결과
작업: {{task_title}}
결과: {{verdict}} ({{issue_count}}개 이슈)
{{issues_summary}}

→ 수정 필요: {{needs_fix}}
→ 바로 배포 가능: {{ready_to_deploy}}
```

### Obsidian 검수 로그 (05_Logs/codex-review-log.md append)
```markdown
## {{date}} — {{task_title}}

- verdict: {{verdict}}
- issues: {{issue_count}}
- commit: {{commit_hash_short}}
- needs_fix: {{needs_fix}}

### 이슈 목록
{{issues_detail}}
```

## verdict 값

| 값 | 의미 |
|----|------|
| `LGTM` | 이슈 없음, 즉시 배포 가능 |
| `MINOR_ISSUES` | 경미한 이슈, 선택적 수정 |
| `NEEDS_FIX` | 필수 수정 항목 존재 |
| `BLOCKED` | 보안/데이터 손실 위험, 즉시 롤백 필요 |

## 변수 목록

| 변수 | 출처 | 예시 |
|------|------|------|
| `{{task_title}}` | 검수 대상 태스크 | `CL-025 태블릿 음성 인테이크` |
| `{{verdict}}` | Codex 판정 | `LGTM` |
| `{{issue_count}}` | 발견된 이슈 수 | `0` |
| `{{issues_summary}}` | 이슈 요약 | `타입 안전성 이슈 1개` |
| `{{issues_detail}}` | 이슈 상세 목록 | markdown 리스트 |
| `{{needs_fix}}` | bool | `false` |
| `{{ready_to_deploy}}` | bool | `true` |
| `{{commit_hash_short}}` | 검수 대상 커밋 | `388c764` |

## Trigger.dev Job 참조
→ `scripts/trigger_jobs/job-review-complete.js`

*Related: [[technical-patterns-hub]]*
