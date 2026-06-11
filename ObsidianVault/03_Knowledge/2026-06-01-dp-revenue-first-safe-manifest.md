---
title: 수익 우선 안전 매니페스트
date: 2026-06-01
source: daily-plus/2026-06-01.md (Card 5)
priority: P1
category: knowledge
status: distilled
tags:
  - manifest
  - permissions
  - revenue
  - agent
  - security
  - daily-plus
  - knowledge
---

# 수익 우선 안전 매니페스트

> Daily Plus Pulse 2026-06-01 Card 5 증류 (P1 · knowledge-candidate)

## 목적

버키(Bridge)나 Git pre-receive 훅에 붙여쓸 수익 우선 매니페스트. 폴더→에이전트→허용 액션 선언, 서명/타임스탬프/멱등성 강제, 원클릭 과금/게시/롤백 흐름.

## 폴더 권한 선언 형식

```yaml
# revenue-manifest.yaml
version: "1.0"
issued_at: "2026-06-01T00:00:00Z"
issuer: "jaeha8104"
idempotency_key: "rev-manifest-EP-001-v1"

folders:
  - path: "ObsidianVault/05_Revenue"
    agent: "bucky"
    allowed_actions:
      - read
      - write_payment_record
      - notify_discord
    forbidden_actions:
      - delete
      - bulk_export
  - path: "scripts/billing"
    agent: "claude-code"
    allowed_actions:
      - read
      - execute_charge
      - execute_rollback
    approval_required: true
    approval_channel: "#jh-승인게이트"

revenue_actions:
  charge:
    max_amount_krw: 100000
    approval_threshold_krw: 50000
    require_signature: true
  publish:
    environments: ["staging", "production"]
    require_signature: true
  rollback:
    max_lookback_hours: 72
    require_signature: false  # 롤백은 즉시 허용
```

## 서명 검증 절차

```python
import hmac, hashlib, time, json

MANIFEST_SECRET = "<env:MANIFEST_SECRET>"

def sign_manifest(payload: dict) -> str:
    """매니페스트 페이로드에 HMAC-SHA256 서명 생성"""
    body = json.dumps(payload, sort_keys=True).encode()
    return hmac.new(MANIFEST_SECRET.encode(), body, hashlib.sha256).hexdigest()

def verify_manifest(payload: dict, signature: str) -> bool:
    """서명 검증 + 타임스탬프 만료(5분) 확인"""
    expected = sign_manifest(payload)
    ts = payload.get("issued_at", "")
    age = time.time() - int(ts) if ts.isdigit() else float('inf')
    return hmac.compare_digest(expected, signature) and age < 300

def check_idempotency(key: str, store: dict) -> bool:
    """멱등성 키 중복 실행 방지"""
    if key in store:
        return False  # 이미 실행됨
    store[key] = time.time()
    return True
```

## 과금 액션 승인 게이트

```
[에이전트 과금 요청]
       ↓
[매니페스트 서명 검증]
       ↓ (실패 시 즉시 거부)
[금액 ≤ approval_threshold?]
  YES → 자동 실행
  NO  → Discord #jh-승인게이트 알림
       ↓
[사용자 /approve <idempotency_key> 입력]
       ↓
[5분 내 승인 없으면 자동 취소]
       ↓
[멱등성 키 기록 → 실행]
```

### Discord 승인 메시지 포맷

```
[과금 승인 요청]
액션: execute_charge
금액: ₩79,000 (EP-001)
요청자: claude-code
idempotency_key: rev-charge-EP-001-20260601
만료: 5분

/approve rev-charge-EP-001-20260601
/reject rev-charge-EP-001-20260601
```

## 구현 우선순위

- [ ] `revenue-manifest.yaml` 작성 및 버전 관리
- [ ] `sign_manifest()` / `verify_manifest()` 함수 배포
- [ ] Discord 승인 게이트 봇 명령어 등록
- [ ] Git pre-receive 훅에 매니페스트 검증 삽입
- [ ] 멱등성 키 저장소 (Redis or SQLite)

## 관련 컨텍스트

- Bucky 에이전트 권한 관리 전체 흐름
- [[텔레메트리-롤백-감사-운영서]], [[가격-AB-결정-매니페스트]]
