---
type: knowledge-note
date: 2026-06-04
source: daily-plus
category: obsidian-queue
tags:
- '#area/ai_automation'
- '#status/active'
summary: 오늘의_플러스 트리아지 정책 — vault 텔레메트리 기반 실행 게이트, HMAC + 멱등성 키 적용
status: applied
applied_at: 2026-06-11
graph_cluster: daily-practice
---

# 오늘의_플러스 Triage Policy

## 개요

Vault 텔레메트리 데이터를 실행 가능한 게이트로 전환하는 compact triage 정책. Safe ops, idempotency, audit trail을 최소 사양으로 구현한다.

## 핵심 원칙

1. **Safe by default**: 모든 실행은 검증 후 진행
2. **Idempotent**: 동일 요청 중복 실행 방지
3. **Auditable**: 모든 게이트 통과/차단 기록 보존

## 최소 사양 (Min Spec)

### HMAC 서명 검증
```python
import hmac
import hashlib

def verify_gate_request(payload: str, signature: str, secret: str) -> bool:
    """게이트 요청 서명 검증"""
    expected = hmac.new(
        secret.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)
```

### 멱등성 키 처리
```python
import redis
from datetime import timedelta

IDEMPOTENCY_TTL = timedelta(hours=24)

def check_idempotency(idempotency_key: str, redis_client) -> bool:
    """중복 실행 방지 — True면 이미 처리됨"""
    key = f"gate:idem:{idempotency_key}"
    if redis_client.exists(key):
        return True
    redis_client.setex(key, IDEMPOTENCY_TTL, "processed")
    return False
```

## 트리아지 게이트 플로우

```
입력 요청
    ↓
[1] HMAC 서명 검증 → 실패 시 401 반환
    ↓
[2] 멱등성 키 확인 → 중복 시 200 (이미 처리됨) 반환
    ↓
[3] Vault 상태 확인 → 잠금 상태 시 423 반환
    ↓
[4] 실행 + Obsidian 감사 기록
    ↓
완료
```

## Obsidian 감사 기록 형식

```markdown
## Gate Log — {{date}}
- key: {{idempotency_key}}
- action: {{action_type}}
- status: {{passed|blocked|duplicate}}
- reason: {{reason}}
- ts: {{timestamp}}
```

## 오늘의_플러스 Vault 텔레메트리 연동

Vault의 파일 변경 이벤트를 트리거로 사용:
- 새 파일 생성 → 자동 분류 게이트
- 태그 변경 → 상태 전환 게이트
- 링크 추가 → 지식 연결 게이트

## 참고

- 관련 노트: `2026-05-30-dp-obsidian-agent-bridge.md`
- 구현 시 `bucky_chat_server.py` IPC 채널 활용
