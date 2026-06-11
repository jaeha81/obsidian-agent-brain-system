---
title: 최소 에이전트 텔레메트리 신호
date: 2026-06-10
source: daily-plus/2026-06-10.md (Card 10)
priority: P1
category: knowledge
status: distilled
tags:
  - telemetry
  - agent
  - metrics
  - monitoring
  - p95
  - daily-plus
  - knowledge
---

# 최소 에이전트 텔레메트리 신호

> ChatGPT Pulse 2026-06-10 Card 10 증류 (P1 · knowledge-candidate)

## 목적

에이전트 운영에서 추적할 5가지 최소 신호를 정의하고, 이벤트 스키마와 경고 임계값을 제공한다.

## 5가지 핵심 신호

| # | 신호명 | 경고 임계값 | 심각 임계값 |
|---|--------|------------|------------|
| S1 | 레이턴시 (p95) | > 2.0s | > 5.0s |
| S2 | 토큰 사용량 | 기준 대비 +30% | +100% |
| S3 | 입력 신뢰도 | < 0.85 | < 0.70 |
| S4 | 출력 신뢰도 | < 97% | < 90% |
| S5 | 사용자 승인률 | < 80% | < 60% |

## 이벤트 스키마

```json
{
  "ts": "2026-06-10T09:30:00Z",
  "app": "ibujang-agent",
  "session_id": "sess-abc123",
  "latency_ms": 1850,
  "tokens": {
    "input": 1200,
    "output": 450,
    "total": 1650,
    "baseline_total": 1500
  },
  "confidence": {
    "input": 0.91,
    "output": 0.98
  },
  "user_approval": {
    "approved": true,
    "session_approval_rate": 0.87
  },
  "alerts": []
}
```

## 경고 임계값 로직

```python
def check_alerts(event: dict) -> list[str]:
    alerts = []

    # S1: 레이턴시
    if event['latency_ms'] > 2000:
        alerts.append(f"WARN: latency {event['latency_ms']}ms > 2000ms")
    if event['latency_ms'] > 5000:
        alerts.append(f"CRITICAL: latency {event['latency_ms']}ms > 5000ms")

    # S2: 토큰
    baseline = event['tokens']['baseline_total']
    total = event['tokens']['total']
    if total > baseline * 1.3:
        alerts.append(f"WARN: token usage +{(total/baseline-1)*100:.0f}% over baseline")

    # S3: 입력 신뢰도
    if event['confidence']['input'] < 0.85:
        alerts.append(f"WARN: input confidence {event['confidence']['input']:.2f} < 0.85")

    # S4: 출력 신뢰도
    if event['confidence']['output'] < 0.97:
        alerts.append(f"WARN: output confidence {event['confidence']['output']:.2f} < 0.97")

    # S5: 사용자 승인률
    if event['user_approval']['session_approval_rate'] < 0.80:
        alerts.append(f"WARN: approval rate {event['user_approval']['session_approval_rate']:.0%} < 80%")

    return alerts
```

## 모니터링 대시보드 설계

```
+---------------------------+---------------------------+
|  레이턴시 p95 (실시간)      |  토큰 사용량 트렌드          |
|  [████████░░] 1.85s        |  [+12% vs 기준]            |
+---------------------------+---------------------------+
|  입력/출력 신뢰도            |  사용자 승인률               |
|  IN: 0.91 / OUT: 0.98      |  87% (최근 50세션)          |
+---------------------------+---------------------------+
|  최근 경고 (24h)                                        |
|  [09:15] WARN: latency 2,100ms > 2,000ms               |
+------------------------------------------------------ -+
```

## 신호 수집 방법

```python
# 에이전트 실행 후 텔레메트리 기록
import time
import json
from pathlib import Path

def record_telemetry(event: dict):
    log_path = Path("logs/telemetry.jsonl")
    log_path.parent.mkdir(exist_ok=True)
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")

    alerts = check_alerts(event)
    for alert in alerts:
        print(f"[ALERT] {alert}")
        # TODO: Slack 또는 Discord webhook 전송
```

## 관련 컨텍스트

- [[ibujang-ops-report]]
- [[manifest-hmac-acceptance]]
- [[poc-verify-matrix]]
