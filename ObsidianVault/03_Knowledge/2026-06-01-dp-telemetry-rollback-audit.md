---
title: 텔레메트리 롤백 감사 운영서
date: 2026-06-01
source: daily-plus/2026-06-01.md (Card 6)
priority: P1
category: knowledge
status: distilled
tags:
  - telemetry
  - rollback
  - audit
  - deployment
  - monitoring
  - daily-plus
  - knowledge
---

# 텔레메트리 롤백 감사 운영서

> Daily Plus Pulse 2026-06-01 Card 6 증류 (P1 · knowledge-candidate)

## 목적

배포 실패를 자동 감지·되돌리는 감사·자동 롤백 플레이북. 배포 후 문제 빠른 탐지, 버튼 한 번에 롤백, 모든 매출/요금 관련 행위 감사 추적.

## 감지 임계값

| 지표 | 정상 범위 | 경고 임계값 | 자동 롤백 임계값 |
|------|---------|-----------|--------------|
| 결제 성공률 | ≥ 95% | < 90% | < 80% |
| API 오류율 | < 1% | > 3% | > 10% |
| 페이지 로드 (P95) | < 2초 | > 4초 | > 8초 |
| 텔레메트리 누락률 | < 2% | > 5% | > 15% |
| 5xx 응답률 | < 0.5% | > 2% | > 5% |

감지 주기: 1분마다 집계, 5분 이동평균으로 판단.

## 롤백 트리거 조건

```yaml
rollback_triggers:
  - condition: payment_success_rate < 0.80
    window: 5m
    action: auto_rollback
    notify: ["#jh-알림", "#jh-수익알림"]

  - condition: api_error_rate > 0.10
    window: 5m
    action: auto_rollback
    notify: ["#jh-알림"]

  - condition: p95_latency > 8000  # ms
    window: 10m
    action: alert_and_hold
    notify: ["#jh-알림"]
    manual_approval_required: true

  - condition: telemetry_drop_rate > 0.15
    window: 10m
    action: alert
    notify: ["#jh-알림"]
```

## 롤백 실행 절차

```bash
# 1. 현재 배포 버전 확인
git log --oneline -5

# 2. 이전 안정 버전으로 되돌리기 (Vercel)
vercel rollback <deployment-url>

# 3. 또는 Git 태그 기반 롤백
git checkout tags/stable-<YYYYMMDD>
vercel --prod

# 4. 롤백 완료 확인
curl -s https://<domain>/api/health | jq '.version'
```

Bucky 명령어: `/rollback EP-001 <version>` → Discord #jh-승인게이트 거쳐 실행

## 감사 로그 필드

```json
{
  "audit_id": "aud_<uuid>",
  "ts": "2026-06-01T10:00:00Z",
  "actor": "bucky | claude-code | user:jaeha8104",
  "action": "charge | publish | rollback | config_change",
  "resource": "stripe_payment | vercel_deployment | manifest",
  "resource_id": "cs_xxx | dpl_xxx | EP-001",
  "amount_krw": 49000,
  "result": "success | failure | pending",
  "reason": "auto_rollback_triggered: payment_success_rate=0.75",
  "idempotency_key": "aud-EP-001-20260601-001",
  "ip": "1.2.3.4",
  "metadata": {}
}
```

저장 경로: `ObsidianVault/00_System/audit_logs/YYYY-MM/`

## 자동화 구현 방법

```python
# 모니터링 루프 (30초 간격)
import time, requests

def check_health(metrics_url: str) -> dict:
    return requests.get(metrics_url).json()

def should_rollback(metrics: dict) -> bool:
    return (
        metrics['payment_success_rate'] < 0.80 or
        metrics['api_error_rate'] > 0.10
    )

def execute_rollback(deployment_id: str):
    # Vercel API 롤백 호출
    requests.post(
        f"https://api.vercel.com/v1/deployments/{deployment_id}/rollback",
        headers={"Authorization": f"Bearer {VERCEL_TOKEN}"}
    )
    write_audit_log(action="rollback", resource_id=deployment_id)

while True:
    metrics = check_health(METRICS_URL)
    if should_rollback(metrics):
        execute_rollback(CURRENT_DEPLOYMENT_ID)
        break
    time.sleep(30)
```

## 구현 우선순위

- [ ] 지표 수집 엔드포인트 (`/api/metrics`) 구현
- [ ] 롤백 트리거 조건 YAML 작성
- [ ] Vercel 롤백 API 연동
- [ ] 감사 로그 저장 파이프라인 구축
- [ ] Discord 알림 채널 연결

## 관련 컨텍스트

- 모든 배포·과금 행위의 감사 추적 기반
- [[수익-우선-안전-매니페스트]], [[클라우드-코드-플러그인-계획]]
