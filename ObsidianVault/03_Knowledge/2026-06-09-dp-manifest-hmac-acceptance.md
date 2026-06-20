---
title: 매니페스트 HMAC 수용 기준
date: 2026-06-09
source: daily-plus/2026-06-09.md (Card 2)
priority: P1
category: knowledge
status: distilled
tags:
- hmac
- manifest
- deployment-gate
- sha256
- key-rotation
- daily-plus
- knowledge
- source/today_plus
- type/reference
graph_cluster: daily-practice
---

# 매니페스트 HMAC 수용 기준

> ChatGPT Pulse 2026-06-09 Card 2 증류 (P1 · knowledge-candidate)

## 목적

배포 게이트를 명시적 수용 기준으로 잠그는 한 페이지 실행 가이드. 매니페스트 무결성(SHA), HMAC 서명/검증, 키 회전, 백업·롤백, 최소 감사로그를 포함한다.

## 수용 기준 체크리스트

- [ ] SHA256 체크섬 일치
- [ ] HMAC-SHA256 서명 검증 통과
- [ ] idempotency_key 미사용 상태 (신규 배포)
- [ ] 매니페스트 버전이 현재 배포 버전보다 높음
- [ ] 배포 전 백업 완료 확인
- [ ] 감사로그에 이전 배포 이력 존재

## HMAC 검증 코드

```python
import hmac
import hashlib

def verify_manifest(manifest_bytes: bytes, signature: str, secret_key: str) -> bool:
    expected = hmac.new(
        secret_key.encode(),
        manifest_bytes,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)

# 사용
with open('manifest.json', 'rb') as f:
    data = f.read()

is_valid = verify_manifest(data, received_signature, SECRET_KEY)
print("PASS" if is_valid else "FAIL — 배포 중단")
```

## HMAC 서명 생성

```python
def sign_manifest(manifest_bytes: bytes, secret_key: str) -> str:
    return hmac.new(
        secret_key.encode(),
        manifest_bytes,
        hashlib.sha256
    ).hexdigest()
```

## 키 회전 절차

1. 새 시크릿 키 생성: `python -c "import secrets; print(secrets.token_hex(32))"`
2. 구 키로 서명된 매니페스트 목록 조회 (감사로그 기준)
3. 새 키로 전체 매니페스트 재서명
4. 구 키 폐기 (환경변수 업데이트)
5. 키 회전 완료 후 검증 테스트 실행

## 감사로그 형식

```json
{
  "event": "manifest_deployed",
  "ts": "2026-06-09T10:00:00Z",
  "manifest_version": "1.3.0",
  "idempotency_key": "550e8400-...",
  "sha256": "abc123...",
  "hmac_verified": true,
  "operator": "ibujang-agent",
  "rollback_available": true
}
```

## 관련 컨텍스트

- [[agent-manifest-recovery]]
- [[ibujang-ops-report]]
- 키는 `.env` 또는 Secret Manager에 보관, 코드에 하드코딩 금지
