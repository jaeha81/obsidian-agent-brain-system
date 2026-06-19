---
title: HMAC·중복방지 인간 검수 체크리스트
date: 2026-06-05
source: daily-plus/2026-06-05.md (Card 5)
priority: P1
category: knowledge
status: distilled
tags:
- hmac
- idempotency
- security
- reviewer
- ci
- daily-plus
- knowledge
graph_cluster: daily-practice
---

# HMAC·중복방지 인간 검수 체크리스트

> ChatGPT Pulse 2026-06-05 Card 5 증류 (P1 · knowledge-candidate)

## 목적

안전하게 자동 승인/적용하기 위한 HMAC + 타임스탬프 + 멱등성 기본 개념. PR 설명이나 에이전트 메시지에 붙여쓸 리뷰어 체크리스트 + CI 스모크 명령.

## HMAC 검증 절차

HMAC(Hash-based Message Authentication Code)은 메시지 무결성과 발신자 인증을 동시에 제공한다.

```python
import hmac, hashlib, time

def sign_payload(payload: bytes, secret: str) -> str:
    """요청 서명 생성"""
    return hmac.new(
        secret.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()

def verify_signature(payload: bytes, signature: str, secret: str) -> bool:
    """서명 검증 (타이밍 안전 비교)"""
    expected = sign_payload(payload, secret)
    return hmac.compare_digest(expected, signature)
```

**검증 순서**:
1. `X-Signature` 헤더 존재 여부 확인
2. HMAC-SHA256 재계산
3. `hmac.compare_digest()` 로 타이밍 안전 비교 (단순 `==` 금지)
4. 서명 불일치 시 즉시 `403 Forbidden`

## 타임스탬프 윈도우

리플레이 공격 방지를 위해 타임스탬프 허용 윈도우 설정:

```python
MAX_TIMESTAMP_DRIFT_SECONDS = 300  # ±5분

def validate_timestamp(ts: int) -> bool:
    now = int(time.time())
    return abs(now - ts) <= MAX_TIMESTAMP_DRIFT_SECONDS
```

- 요청 헤더에 `X-Timestamp` 포함 필수
- 5분 초과 요청은 거부
- 서버 시간 동기화(NTP) 확인 필수

## idempotency_key 처리

동일 요청의 중복 실행을 막는 멱등성 키:

```python
# Redis 기반 멱등성 처리
def idempotent_execute(key: str, ttl: int = 86400):
    if redis.exists(f"idem:{key}"):
        return redis.get(f"idem:{key}")  # 캐시된 결과 반환
    result = execute_operation()
    redis.setex(f"idem:{key}", ttl, result)
    return result
```

**키 생성 규칙**:
- 형식: `{service}:{operation}:{hash(payload)}`
- TTL: 24시간 (재처리 허용 기간)
- 저장소: Redis 또는 DB 전용 테이블

## 리뷰어 체크리스트 (PR/에이전트 메시지용)

```markdown
## HMAC·멱등성 검수 체크리스트

- [ ] HMAC 서명 검증 로직이 `hmac.compare_digest()` 사용
- [ ] 타임스탬프 ±5분 윈도우 적용
- [ ] `idempotency_key` 생성 및 저장 로직 존재
- [ ] 중복 요청 시 동일 결과 반환 (부작용 없음)
- [ ] 서명 키가 환경변수로 주입됨 (하드코딩 금지)
- [ ] 오류 응답이 상세 내부 정보를 노출하지 않음
```

## CI 스모크 명령 예시

```bash
# HMAC 서명 검증 테스트
pytest tests/test_hmac.py -v

# 멱등성 테스트 (동일 키 2회 요청)
python scripts/smoke_idempotency.py --key test-001 --repeat 2

# 타임스탬프 만료 테스트
python scripts/smoke_timestamp.py --drift 400  # 400초 → 거부 확인
```

## 관련 컨텍스트

- Stripe 웹훅, 에이전트 IPC, 외부 API 연동 시 공통 적용
- [[stripe-webhook-metadata]], [[rbac-secrets-handoff]]
