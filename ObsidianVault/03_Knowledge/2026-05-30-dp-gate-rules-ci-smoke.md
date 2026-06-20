---
title: 게이트 규칙과 CI 스모크 테스트
date: 2026-05-30
source: daily-plus/2026-05-30.md (Card 2)
priority: P1
category: knowledge
status: distilled
tags:
- ci
- smoke-test
- gate
- deployment
- automation
- daily-plus
- knowledge
- source/today_plus
- type/reference
graph_cluster: daily-practice
---

# 게이트 규칙과 CI 스모크 테스트

> ChatGPT Pulse 2026-05-30 Card 2 증류 (P1 · knowledge-candidate)

## 목적

자동 배포 전 초단기 스모크 테스트와 결정 규칙 도입 가이드. 치명적 실패(인증·SHA 불일치)는 즉시 차단하고, 통과/검토/거절을 수치·규칙으로 일관 처리한다.

## 스모크 테스트 3종

### 1. 인증 테스트
```bash
# API 키 또는 토큰이 유효한지 확인
curl -sf -H "Authorization: Bearer $TOKEN" "$BASE_URL/health" \
  | jq '.status == "ok"'
```

### 2. SHA 불일치 테스트
```bash
# 배포 아티팩트 해시 검증
EXPECTED=$(cat deploy.sha256)
ACTUAL=$(sha256sum artifact.tar.gz | awk '{print $1}')
[ "$EXPECTED" = "$ACTUAL" ] || exit 1
```

### 3. 엔드포인트 응답 테스트
```bash
# 핵심 엔드포인트 200 응답 확인
for endpoint in /api/health /api/status; do
  STATUS=$(curl -so /dev/null -w "%{http_code}" "$BASE_URL$endpoint")
  [ "$STATUS" = "200" ] || exit 1
done
```

## 결정 규칙 포맷

```yaml
gate_decision:
  pass:
    conditions:
      - smoke_tests_passed: true
      - sha_match: true
      - auth_valid: true
    action: "deploy"
  review:
    conditions:
      - smoke_tests_passed: true
      - performance_degraded: true  # p99 > 2x baseline
    action: "notify_and_hold"
  reject:
    conditions:
      - smoke_tests_passed: false
      - auth_valid: false
    action: "block_and_alert"
```

## 로그·감사 저장 형식

```json
{
  "run_id": "ci-2026-05-30T00:00:00Z",
  "commit": "sha256:abc...",
  "gate": "smoke-v1",
  "tests": [
    { "name": "auth", "result": "pass", "duration_ms": 120 },
    { "name": "sha_match", "result": "pass", "duration_ms": 5 },
    { "name": "endpoints", "result": "pass", "duration_ms": 340 }
  ],
  "decision": "pass",
  "saved_to": "logs/ci-audit/2026-05-30.jsonl"
}
```

감사 로그는 `logs/ci-audit/YYYY-MM-DD.jsonl` 형식으로 append-only 저장.

## 관련 컨텍스트

- [[2026-05-30-dp-orchestrator-approval-gate]] — 오케스트레이터 승인 게이트
- [[2026-05-31-dp-bucky-trigger-smoke-hook]] — Bucky 트리거 스모크 훅
