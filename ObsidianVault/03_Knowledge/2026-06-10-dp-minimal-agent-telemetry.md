---
type: knowledge-note
date: 2026-06-10
source: daily-plus
category: verification
tags:
- '#area/ai_automation'
- '#status/active'
summary: 최소 에이전트 텔레메트리 — 5개 신호, 이벤트 스키마, 일별 상태 표시 기준
status: applied
applied_at: 2026-06-11
graph_cluster: daily-practice
---

# 최소 에이전트 텔레메트리 신호

에이전트 운영 상태를 최소한의 신호로 모니터링하는 기준.
과도한 로깅 대신 5개 핵심 신호만 추적해 운영 부담을 줄인다.

---

## 5개 핵심 신호

### Signal 1 — Latency (응답 지연)

| 항목 | 값 |
|---|---|
| 측정 대상 | 요청 수신 → 응답 완료까지 ms |
| 기준 p95 | 2,000ms |
| 알림 조건 | p95 > 2,000ms |
| 알림 채널 | Discord #agent-alerts |
| 측정 주기 | 실시간 (매 요청) |

```python
# 측정 예시
import time

start = time.monotonic()
response = await agent.process(request)
latency_ms = (time.monotonic() - start) * 1000

if latency_ms > 2000:
    await alert_discord(f"[LATENCY] p95 초과: {latency_ms:.0f}ms")
```

---

### Signal 2 — Token Usage (토큰 사용량)

| 항목 | 값 |
|---|---|
| 측정 대상 | 요청당 input + output 토큰 합계 |
| 기준 | 주간 baseline 대비 |
| 알림 조건 | 주간 baseline 대비 +30% 초과 |
| 알림 채널 | Discord #agent-alerts |
| 측정 주기 | 시간별 집계, 일별 리포트 |

```python
# 주간 baseline 대비 계산
weekly_avg = get_weekly_token_average()
current_tokens = response.usage.total_tokens

if current_tokens > weekly_avg * 1.30:
    await alert_discord(f"[TOKENS] baseline+30% 초과: {current_tokens:,} (baseline: {weekly_avg:,})")
```

---

### Signal 3 — Input Confidence (입력 신뢰도)

| 항목 | 값 |
|---|---|
| 측정 대상 | 입력 의도 분류 신뢰도 (0.0-1.0) |
| 기준 | 0.85 |
| 알림 조건 | confidence < 0.85 |
| 알림 채널 | Discord #agent-alerts |
| 측정 주기 | 실시간 (매 요청) |

낮은 신뢰도 = 에이전트가 요청 의도를 명확히 파악하지 못함.
0.85 미만 시 사용자에게 명확화 요청을 먼저 보낸다.

---

### Signal 4 — Output Confidence (출력 검증율)

| 항목 | 값 |
|---|---|
| 측정 대상 | 출력 검증 통과율 (validation pass rate) |
| 기준 | 97% |
| 알림 조건 | pass rate < 97% |
| 알림 채널 | Discord #agent-alerts |
| 측정 주기 | 시간별 집계 |

검증 규칙 예시:
- JSON 스키마 유효성
- 필수 필드 존재
- 금지 콘텐츠 포함 여부
- 출력 길이 범위

---

### Signal 5 — User Approval Rate (사용자 승인율)

| 항목 | 값 |
|---|---|
| 측정 대상 | 사용자가 에이전트 출력을 승인한 비율 |
| 기준 | 80% |
| 알림 조건 | approval rate < 80% |
| 알림 채널 | Discord #agent-alerts |
| 측정 주기 | 일별 집계 |

승인율 80% 미만 = 출력 품질 문제 또는 요청-출력 불일치 신호.
일주일 연속 80% 미만 시 프롬프트 검토 필요.

---

## 최소 이벤트 스키마

모든 에이전트 이벤트는 아래 최소 필드를 포함해야 한다.

```json
{
  "ts": "2026-06-10T14:30:00.000Z",
  "app": "bucky-discord-bot",
  "latency_ms": 1234,
  "tokens": {
    "input": 512,
    "output": 256,
    "total": 768
  },
  "input_conf": 0.92,
  "output_conf": 0.98,
  "approval": true
}
```

### 필드 설명

| 필드 | 타입 | 설명 |
|---|---|---|
| `ts` | ISO 8601 | 이벤트 발생 시각 (UTC) |
| `app` | string | 에이전트/앱 식별자 |
| `latency_ms` | number | 요청-응답 지연 ms |
| `tokens` | object | input/output/total 토큰 수 |
| `input_conf` | float 0-1 | 입력 의도 분류 신뢰도 |
| `output_conf` | float 0-1 | 출력 검증 통과율 |
| `approval` | boolean | 사용자 승인 여부 |

---

## 일별 상태 표시 형식

매일 오전 9시 Discord #daily-digest 채널에 자동 발송.

```
[Agent Telemetry] 2026-06-10

Latency  p95: 1,234ms   [OK]
Tokens   avg: 892/req   [OK]   (+8% vs baseline)
Input    conf: 0.91     [OK]
Output   valid: 98.2%   [OK]
Approval rate: 84%      [OK]

총 요청: 127건 | 실패: 2건 | 알림 발생: 0건
```

알림 조건 초과 시:
```
[ALERT] Output 검증율 96.1% — 기준(97%) 미달
최근 실패 유형: JSON schema 오류 3건, 길이 초과 1건
```

---

## 구현 위치

- 텔레메트리 수집: `scripts/agent_telemetry.py`
- 이벤트 저장: `data/telemetry/YYYY-MM-DD.jsonl`
- Discord 발송: 기존 Discord 봇 webhook 재사용
- 대시보드: `docs/agent-os.html` → AI Usage 탭 확장 고려

## 관련 노트
- [[hubs/JH System]]
