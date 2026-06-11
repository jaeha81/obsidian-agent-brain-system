---
title: 버키 트리거와 스모크 훅
date: 2026-05-31
source: daily-plus/2026-05-31.md (Card 6)
priority: P1
category: knowledge
status: distilled
tags:
  - bucky
  - smoke-test
  - pr
  - trigger
  - pipeline
  - daily-plus
  - knowledge
---

# 버키 트리거와 스모크 훅

> ChatGPT Pulse 2026-05-31 Card 6 증류 (P1 · knowledge-candidate)

## 목적

PR마다 연기 테스트(smoke test)를 작게 정의하여 Bucky 봇이 통과/실패를 판단하고 아티팩트 URL을 첨부하는 실전 템플릿.

## 스모크 훅 정의 포맷

```yaml
# .bucky/smoke-hooks.yml
hooks:
  - id: pr-smoke
    trigger: pull_request.opened
    timeout_sec: 120
    steps:
      - name: build
        run: npm run build
        artifact: dist/
      - name: health_check
        run: curl -sf http://localhost:3000/health
      - name: lint
        run: npm run lint
    on_pass:
      action: approve
      comment: true
      attach_artifacts: true
    on_fail:
      action: block
      comment: true
      notify_channel: "#jh-배포"
```

## 통과 페이로드

```json
{
  "hook_id": "pr-smoke",
  "pr_number": 42,
  "result": "pass",
  "steps": [
    { "name": "build",        "status": "pass", "duration_ms": 8500 },
    { "name": "health_check", "status": "pass", "duration_ms": 120 },
    { "name": "lint",         "status": "pass", "duration_ms": 2300 }
  ],
  "artifacts": [
    { "name": "build output", "url": "https://ci.example.com/artifacts/42/dist.zip" }
  ],
  "comment": "스모크 테스트 통과. 아티팩트: [dist.zip](url)"
}
```

## 실패 페이로드

```json
{
  "hook_id": "pr-smoke",
  "pr_number": 42,
  "result": "fail",
  "steps": [
    { "name": "build",        "status": "pass",   "duration_ms": 8500 },
    { "name": "health_check", "status": "fail",   "duration_ms": 10001, "error": "timeout" },
    { "name": "lint",         "status": "skipped" }
  ],
  "blocker": "health_check",
  "comment": "❌ 스모크 실패: health_check 타임아웃. 배포 차단.",
  "notify": "#jh-배포"
}
```

## 아티팩트 URL 첨부 방식

```python
def attach_artifacts(run_id: str, artifact_dir: str) -> str:
    # CI 아티팩트를 S3/R2에 업로드 후 서명 URL 반환
    url = upload_to_storage(artifact_dir, prefix=f"smoke/{run_id}/")
    return url  # https://storage.example.com/smoke/{run_id}/dist.zip
```

## 관련 컨텍스트

- [[2026-05-30-dp-gate-rules-ci-smoke]] — CI 스모크 테스트 기본 정의
- [[2026-05-31-dp-three-preview-paths]] — 프리뷰 환경 연동
