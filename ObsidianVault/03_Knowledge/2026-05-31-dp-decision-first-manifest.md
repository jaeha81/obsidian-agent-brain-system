---
title: 결정 우선 압축 매니페스트
date: 2026-05-31
source: daily-plus/2026-05-31.md (Card 5)
priority: P1
category: knowledge
status: distilled
tags:
- manifest
- deployment
- decision
- idempotency
- operations
- daily-plus
- knowledge
- source/today_plus
- type/reference
graph_cluster: daily-practice
---

# 결정 우선 압축 매니페스트

> ChatGPT Pulse 2026-05-31 Card 5 증류 (P1 · knowledge-candidate)

## 목적

배포/자동화 오퍼레이션 신호를 한눈에 해석 가능하게 만드는 초간단 매니페스트 규칙. 의사결정 우선, 짧고 구조화, 멱등·재시도 안전.

## 매니페스트 필드 정의

```json
{
  "schema": "ops_manifest_v1",
  "id": "고유 ID (UUID v4 또는 의미있는 슬러그)",
  "decision": "deploy | pause | rollback | escalate | skip",
  "signal_type": "auto | human | scheduled",
  "priority": "P0 | P1 | P2 | P3",
  "idempotency_key": "동일 요청 중복 실행 방지 키",
  "target": "배포/적용 대상 (서비스명 또는 환경)",
  "artifact": "아티팩트 경로 또는 버전",
  "created_at": "ISO8601",
  "expires_at": "ISO8601 (null = 무제한)",
  "metadata": {}
}
```

## 결정 신호 타입

| signal_type | 의미 | 처리 방식 |
|-------------|------|----------|
| auto | 자동화 시스템이 판단 | 즉시 실행 (게이트 통과 시) |
| human | 사람이 명시적으로 승인 | 검증 후 실행 |
| scheduled | 예약된 시간에 실행 | 시간 도래 시 auto로 전환 |

## 운영 채널 포맷

Discord #jh-배포 채널에서 매니페스트를 공유할 때:

```
[ops] deploy · production · v1.2.0
id: deploy-prod-v1.2.0
signal: human
artifact: dist/app-v1.2.0.tar.gz
➜ /bucky exec manifest:deploy-prod-v1.2.0
```

## 멱등성 보장

```python
def execute_manifest(manifest: dict, store: dict) -> str:
    key = manifest["idempotency_key"]

    if key in store:
        existing = store[key]
        if existing["status"] == "completed":
            return f"Already executed: {existing['result']}"
        if existing["status"] == "running":
            return "In progress — skipping duplicate"

    store[key] = {"status": "running", "started_at": now()}
    result = run_operation(manifest)
    store[key] = {"status": "completed", "result": result}
    return result
```

## 관련 컨텍스트

- [[2026-05-30-dp-min-plan-package-template]] — 최소 계획 패키지 (plan_v1)
- [[2026-05-31-dp-ops-snapshot-one-click]] — 운영 스냅샷 원클릭 액션
