---
type: knowledge-note
date: 2026-06-02
source: daily-plus
category: knowledge-candidate
tags:
  - "#area/ai_automation"
  - "#status/active"
summary: Daily Plus 소스 가용성 가드 — ChatGPT Pulse 404/빈 카드 상태를 정상 수집 결과가 아닌 의도적 실패 이벤트로 처리
status: applied
applied_at: 2026-06-11
---

# Daily Plus Source Availability Guard

## 핵심 원칙

ChatGPT Pulse 수집 시 404 또는 빈 카드 상태는 **정상 수집 결과로 저장하지 않는다**.
이를 의도적 실패 이벤트(intentional failure event)로 처리해야 한다.

## 문제 상황

- Pulse 소스가 일시적으로 404 반환
- 카드 목록이 빈 배열로 응답
- 네트워크 타임아웃 후 빈 결과 반환

이 상황에서 빈 결과를 그대로 저장하면:
- 비교 보고서가 "모든 항목 삭제됨"으로 오판
- 이전 정상 데이터를 덮어쓰는 데이터 오염 발생
- 후속 자동화 파이프라인이 잘못된 기준선으로 동작

## 가드 규칙

```python
# 수집 결과 검증 패턴
def is_valid_pulse_result(result):
    if result is None:
        return False, "null_response"
    if result.get("status_code") == 404:
        return False, "source_not_found"
    if len(result.get("items", [])) == 0:
        return False, "empty_collection"
    return True, "ok"

# 저장 전 반드시 검증
valid, reason = is_valid_pulse_result(collected)
if not valid:
    log_failure_event(reason)
    # 이전 데이터 유지, 저장 건너뜀
    return
```

## 실패 이벤트 처리 흐름

1. 실패 감지 → `failure_event` 로그 기록 (타임스탬프 + 사유)
2. 기존 저장 데이터 보존 (덮어쓰지 않음)
3. Bucky 보고 채널에 "수집 실패 - 이전 데이터 유지" 알림
4. 다음 수집 사이클에서 재시도

## 적용 대상 파일

- `scripts/daily_plus_collector.py`
- `scripts/daily_plus_morning_report.py`

## 관련 노트

- [[2026-06-02-dp-bucky-morning-report-failsafe]]
- [[2026-06-02-dp-public-dashboard-integrity]]
