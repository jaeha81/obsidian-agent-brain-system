---
title: 오케스트레이터 승인 게이트와 테스트 링크
date: 2026-05-30
source: daily-plus/2026-05-30.md (Card 1)
priority: P1
category: knowledge
status: distilled
tags:
  - orchestrator
  - approval-gate
  - checklist
  - deployment
  - security
  - daily-plus
  - knowledge
---

# 오케스트레이터 승인 게이트와 테스트 링크

> ChatGPT Pulse 2026-05-30 Card 1 증류 (P1 · knowledge-candidate)

## 목적

오케스트레이터가 사용자에게 프롬프트/배포물을 노출하기 전 반드시 통과해야 하는 최종 승인 체크리스트. 안전·정합·가치를 수치 기준으로 판단한다.

## 사전 승인 체크리스트 포맷

```yaml
approval_gate:
  safety:
    - item: "프롬프트 인젝션 취약점 없음"
      pass_threshold: 0     # 위반 건수
    - item: "PII 노출 없음"
      pass_threshold: 0
  coherence:
    - item: "출력 스키마 일치율"
      pass_threshold: 0.95  # 95% 이상
    - item: "응답 지연 p99"
      pass_threshold: 2000  # ms 이하
  value:
    - item: "테스트 링크 HTTP 200"
      pass_threshold: 1.0
    - item: "기능 커버리지"
      pass_threshold: 0.80
```

## 테스트 링크 검증

승인 게이트는 배포 직전에 test URL을 자동으로 폴링한다.

```python
def verify_test_link(url: str, timeout: int = 10) -> bool:
    resp = requests.get(url, timeout=timeout)
    return resp.status_code == 200 and len(resp.content) > 0
```

- 연속 3회 200 응답 시 통과
- 단 1회라도 4xx/5xx → 즉시 게이트 차단
- 타임아웃 > 10s → 경고 플래그, 검토 대기

## 수치 통과 기준

| 항목 | 통과 | 검토 | 거절 |
|------|------|------|------|
| Safety 위반 건수 | 0 | - | ≥1 |
| 스키마 일치율 | ≥95% | 85~94% | <85% |
| 응답 지연 p99 | ≤2000ms | 2000~5000ms | >5000ms |
| 테스트 링크 | 200 | - | 4xx/5xx |

## 즉시 적용 가능한 형태

```json
{
  "gate_id": "pre-deploy-v1",
  "triggered_by": "orchestrator",
  "timestamp": "ISO8601",
  "checks": [],
  "result": "pass | review | reject",
  "blocker": null
}
```

## 관련 컨텍스트

- [[2026-05-30-dp-gate-rules-ci-smoke]] — CI 스모크 테스트와 연동
- [[2026-05-30-dp-bucky-launch-gate]] — 런치 게이트 자동화
