---
id: IMPL-RA-08
type: hook-template
trigger: impl-complete
status: active
created: 2026-06-10
source: review-automation-protocol.md Phase 2
tags: [#hook, #automation, #implementation]
---

# Hook: 구현완료 알림

## 트리거 조건
- Claude Code가 구현 작업을 완료하고 "완료 보고"를 출력할 때
- 키워드 감지: "완료 보고", "✅ 완료", "구현 완료", "커밋 완료"

## 메시지 템플릿

### Discord 알림
```
✅ **[구현완료]** {{task_title}}
📁 파일: {{files_modified}}
🔍 다음 단계: Codex 검수 대기
⏱ {{timestamp}} | 세션: {{session_id}}
```

### Codex 핸드오프 (Discord #jh-태스크보드)
```
🔍 **Codex 검수 요청**
작업: {{task_title}}
커밋: {{commit_hash_short}}
변경 파일:
{{files_list}}

검수 포인트:
- 타입 안전성
- 보안 취약점
- AI-Slop 패턴
```

## 변수 목록

| 변수 | 출처 | 예시 |
|------|------|------|
| `{{task_title}}` | Claude Code 대화 컨텍스트 | `CL-025 태블릿 음성 인테이크` |
| `{{files_modified}}` | `git diff --name-only HEAD~1` | `scripts/tablet_voice_intake.py` |
| `{{files_list}}` | git diff 파일 목록 | 줄바꿈 구분 목록 |
| `{{commit_hash_short}}` | `git rev-parse --short HEAD` | `388c764` |
| `{{session_id}}` | Claude Code 세션 ID | `abc123` |
| `{{timestamp}}` | ISO 8601 | `2026-06-10T08:14:45+09:00` |

## Trigger.dev Job 참조
→ `scripts/trigger_jobs/job-impl-complete.js`

*Related: [[technical-patterns-hub]]*

