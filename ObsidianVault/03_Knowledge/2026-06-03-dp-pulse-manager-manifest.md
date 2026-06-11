---
type: knowledge-note
date: 2026-06-03
source: daily-plus
category: knowledge-candidate
tags:
  - "#area/ai_automation"
  - "#status/active"
summary: 이부장 펄스 매니저 매니페스트 — 오늘의_플러스 트리아지용 최소 매니페스트: HMAC + 변경 감지만, approve/implement/hold/archive CTA 포함
status: applied
applied_at: 2026-06-11
---

# 이부장 펄스 매니저 매니페스트

## 목적

`오늘의_플러스` 펄스 아이템을 최소한의 처리로 트리아지(triage)하기 위한 매니페스트.
HMAC 검증과 변경 감지만 수행하고, 4종 CTA로 처리 방향을 결정한다.

## 최소 매니페스트 구조

```yaml
# pulse_manager_manifest.yaml
version: "1.0"
pipeline: ibujang-pulse-manager

processing:
  hmac_verify: true          # HMAC 서명 검증 필수
  change_detection_only: true  # 변경된 항목만 처리
  full_reprocess: false      # 전체 재처리 금지 (성능)

actions:
  approve:
    trigger: "manual or auto-pass"
    effect: "implement 큐에 등록"
  implement:
    trigger: "approve 후"
    effect: "코드 구현 태스크 생성"
  hold:
    trigger: "검토 필요"
    effect: "hold 큐에 보관, 재검토 예약"
  archive:
    trigger: "불필요 판단"
    effect: "archive 폴더로 이동, 활성 큐에서 제거"
```

## 변경 감지 패턴

```python
def detect_changes(previous_pulse: list, current_pulse: list) -> dict:
    prev_ids = {item["id"] for item in previous_pulse}
    curr_ids = {item["id"] for item in current_pulse}

    return {
        "new_items": [i for i in current_pulse if i["id"] not in prev_ids],
        "removed_items": [i for i in previous_pulse if i["id"] not in curr_ids],
        "modified_items": [
            i for i in current_pulse
            if i["id"] in prev_ids and has_changed(i, previous_pulse)
        ]
    }
```

## 4종 CTA 흐름

```
신규 펄스 아이템 도착
  ↓
HMAC 검증 → 실패 시 reject
  ↓
변경 감지 → 변경 없으면 skip
  ↓
트리아지 대기열 등록
  ↓
[approve]      → implement 큐 → 코드 태스크 생성
[implement]    → 즉시 구현 시작
[hold]         → hold 큐 → 7일 후 재검토 예약
[archive]      → archive/ 폴더 이동
```

## Discord 트리아지 메시지 포맷

```
[펄스 매니저] 신규 아이템: {item_title}
우선순위: {priority} | 변경 유형: {change_type}
요약: {summary_1line}

[approve] [implement] [hold] [archive]
```

## 변경 감지만 실행하는 이유

- 전체 재처리는 불필요한 CTA 알림 생성
- 변경 없는 아이템에 대한 approve/hold 오판 방지
- 처리 비용 절감 (Bucky API 호출 최소화)

## 관련 노트

- [[2026-06-03-dp-ibujang-oneclick-pilot]]
- [[2026-06-03-dp-ab-auto-decision-14days]]
- [[2026-06-03-dp-webhook-vault-write-pattern]]
