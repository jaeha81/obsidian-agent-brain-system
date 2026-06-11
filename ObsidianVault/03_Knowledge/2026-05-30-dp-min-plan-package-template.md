---
title: 최소 계획 패키지 템플릿
date: 2026-05-30
source: daily-plus/2026-05-30.md (Card 3)
priority: P1
category: knowledge
status: distilled
tags:
  - plan
  - manifest
  - sha256
  - bucky
  - discord
  - daily-plus
  - knowledge
---

# 최소 계획 패키지 템플릿

> ChatGPT Pulse 2026-05-30 Card 3 증류 (P1 · knowledge-candidate)

## 목적

에이전트 오케스트레이션을 검증 가능한 계획으로 표준화하는 템플릿. Discord에서 짧게 실행 지시하고, CI·로컬에서 서명/해시로 동일한 계획인지 확인한다.

## /bucky exec 명령 포맷

Discord에서 최소 계획 패키지를 실행하는 방법:

```
/bucky exec plan:<plan_id> env:<target_env> approve:<yes|no>
```

예시:
```
/bucky exec plan:deploy-v1.2.0 env:production approve:yes
```

## plan_v1 JSON 구조

```json
{
  "schema": "plan_v1",
  "id": "deploy-v1.2.0",
  "created_at": "2026-05-30T09:00:00Z",
  "author": "bucky",
  "goal": "production 배포 — v1.2.0",
  "steps": [
    {
      "seq": 1,
      "action": "smoke_test",
      "target": "staging",
      "expect": "pass"
    },
    {
      "seq": 2,
      "action": "deploy",
      "target": "production",
      "artifact": "dist/app-v1.2.0.tar.gz",
      "sha256": "abc123..."
    },
    {
      "seq": 3,
      "action": "verify",
      "url": "https://app.example.com/health",
      "expect_status": 200
    }
  ],
  "signature": {
    "algo": "sha256",
    "value": "def456..."
  }
}
```

## 검증 스크립트

```python
import hashlib, json

def verify_plan(plan_path: str) -> bool:
    with open(plan_path) as f:
        plan = json.load(f)

    # 서명 필드 제외하고 재계산
    sig = plan.pop("signature")
    canonical = json.dumps(plan, sort_keys=True, ensure_ascii=False)
    computed = hashlib.sha256(canonical.encode()).hexdigest()
    return computed == sig["value"]
```

## 사용 원칙

- 계획 ID는 불변 — 수정 시 새 ID 발급
- 동일 plan_id가 여러 환경에서 실행될 경우 sha256이 매번 일치해야 함
- Discord 명령과 CI 실행의 plan_id가 불일치하면 즉시 거절

## 관련 컨텍스트

- [[2026-05-30-dp-orchestrator-approval-gate]] — 승인 게이트
- [[2026-05-30-dp-bucky-launch-gate]] — 런치 게이트 자동화
- [[2026-05-30-dp-obsidian-yaml-standard]] — YAML 표준과 SHA-256 필드
