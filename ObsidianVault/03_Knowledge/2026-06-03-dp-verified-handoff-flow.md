---
type: knowledge-note
date: 2026-06-03
source: daily-plus
category: knowledge-candidate
tags:
  - "#area/ai_automation"
  - "#status/active"
summary: 검증형 핸드오프 흐름 — 멱등성 키 잠금 전 타임스탬프 + 서명 + SHA 검증, 정책 허용 시 커밋 또는 승인 대기 큐
status: applied
applied_at: 2026-06-11
---

# 검증형 핸드오프 흐름 (Verified Handoff Flow)

## 핵심 원칙

멱등성 키를 잠그기(lock) **전에** 반드시 3단계 검증을 완료해야 한다:
1. 타임스탬프 유효성 확인
2. 서명(Signature) 검증
3. SHA 페이로드 무결성 확인

## 3단계 검증 흐름

```
수신된 웹훅/핸드오프 요청
  ↓
[Step 1] 타임스탬프 검증
  - 현재 시각과의 차이 <= 5분
  - 미래 타임스탬프 거부
  ↓ 통과
[Step 2] 서명 검증 (HMAC-SHA256)
  - X-Signature 헤더 값과 재계산값 비교
  - hmac.compare_digest 사용
  ↓ 통과
[Step 3] SHA 페이로드 무결성
  - 수신 페이로드의 SHA256 해시 계산
  - 헤더에 포함된 X-Payload-Hash와 비교
  ↓ 통과
멱등성 키 잠금 → 커밋 또는 승인 대기 큐
```

## 구현 패턴

```python
from datetime import datetime, timezone, timedelta
import hashlib
import hmac
import json

MAX_TIMESTAMP_DRIFT = timedelta(minutes=5)

def verify_handoff(request_headers: dict, payload: dict) -> tuple[bool, str]:
    # Step 1: 타임스탬프 검증
    ts_str = request_headers.get("X-Ibujang-Timestamp")
    if not ts_str:
        return False, "missing_timestamp"

    request_time = datetime.fromisoformat(ts_str)
    now = datetime.now(timezone.utc)
    if abs(now - request_time) > MAX_TIMESTAMP_DRIFT:
        return False, "timestamp_expired"

    # Step 2: 서명 검증
    received_sig = request_headers.get("X-Ibujang-Signature")
    expected_sig = compute_hmac(payload, ts_str)
    if not hmac.compare_digest(received_sig, expected_sig):
        return False, "invalid_signature"

    # Step 3: SHA 페이로드 무결성
    received_hash = request_headers.get("X-Payload-Hash")
    payload_bytes = json.dumps(payload, separators=(',', ':')).encode()
    computed_hash = hashlib.sha256(payload_bytes).hexdigest()
    if received_hash != computed_hash:
        return False, "payload_integrity_failed"

    return True, "ok"
```

## 커밋 vs 승인 대기 큐 결정

```python
def process_after_verification(payload: dict, idempotency_key: str):
    # 정책 확인
    if requires_approval(payload):
        # 승인 대기 큐에 등록
        queue_for_approval(payload, idempotency_key)
        notify_bucky("pending_approval", payload)
        return {"status": "pending_approval"}

    # 즉시 커밋 허용
    lock_idempotency_key(idempotency_key)
    commit_payload(payload)
    return {"status": "committed"}

def requires_approval(payload: dict) -> bool:
    # 고액 결제, 환불, 민감 작업은 승인 필요
    if payload.get("amount", 0) > 100000:
        return True
    if payload.get("event") in ["order.cancelled", "refund.requested"]:
        return True
    return False
```

## 보안 규칙

- 멱등성 키는 검증 완료 후에만 잠금
- 검증 실패 시 잠금 없이 400 반환
- 승인 대기 큐 항목은 24시간 후 자동 만료
- 모든 검증 실패는 로그에 기록 (공격 패턴 감지용)

## 관련 노트

- [[2026-06-03-dp-ibujang-stripe-webhook]]
- [[2026-06-03-dp-ibujang-min-api-contract]]
- [[2026-06-03-dp-webhook-vault-write-pattern]]
