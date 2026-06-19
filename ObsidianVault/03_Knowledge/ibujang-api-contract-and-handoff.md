---
title: 이부장 API 계약 & 검증형 핸드오프 패턴
date: 2026-06-03
source: daily-plus/2026-06-03.md (Card 4, 5)
tags:
- ibujang
- api-contract
- handoff
- knowledge
- hmac
- idempotency
category: knowledge
status: distilled
graph_cluster: misc
---

# 이부장 최소 API 계약 & 검증형 핸드오프 흐름

> ChatGPT Pulse 2026-06-03 Card 4 + Card 5 증류

## 필수 HTTP 헤더 (서버 검증 필수)

```
Idempotency-Key: <uuid>
X-Timestamp: <ISO8601 UTC>
X-Signature: sha256=<hex-hmac>   ← HMAC-SHA256(body, secret)
Content-Type: application/json
Agent-Name: 이부장
```

## 최소 JSON 페이로드 3종

**예시 1 — 매니페스트 게시**
```json
{
  "manifest_id": "manifest-<uuid>",
  "action": "publish",
  "vault_path": "Jh/Agents/이부장/manifests/manifest-<uuid>.json",
  "idempotency_key": "<uuid>",
  "manifest_sha256": "<sha256-hex>",
  "allowed_actions": ["write", "publish_preview"],
  "require_human_approve": false
}
```

**예시 2 — 보호된 리포 패치 (사람 승인 필요)**
```json
{
  "action": "apply_patch",
  "allowed_actions": ["create_commit", "push"],
  "require_human_approve": true
}
```

**예시 3 — 드라이런 세이프티 게이트**
```json
{
  "action": "dry_run",
  "allowed_actions": ["validate_only"],
  "require_human_approve": true
}
```

## 서버 검증 순서 (의사코드)

```
1. X-Timestamp 스큐 ≤ 5분 확인
2. HMAC-SHA256(body, secret) == X-Signature
3. sha256(body) == payload.manifest_sha256
4. INSERT OR IGNORE INTO idempotency → 중복이면 200 OK 반환
5. 정책 엔진: vault_path + allowed_actions 화이트리스트 확인
6. 커밋/PR 실행 → 스모크 테스트 → 실패 시 롤백
7. 모든 분기 텔레메트리 로깅
```

## 허용 경로 화이트리스트

| 경로 | 허용 액션 |
|------|---------|
| `Jh/Agents/이부장/manifests` | publish_preview |
| `Jh/Services/claude-handler` | 디렉토리 하위 파일만 패치 |
| `Jh/Orders` | 주문 쓰기 액션만 (감사 로그 필수) |

## 커밋/롤백 원라인

```bash
# 커밋
git add Jh/Agents/이부장/manifests/manifest-<uuid>.json && \
git commit -m "이부장: apply manifest manifest-<uuid>" && \
git push origin main

# 롤백
git revert <commit_sha> --no-edit && git push origin main
```

## 멱등성 SQLite 스키마

```sql
CREATE TABLE IF NOT EXISTS idempotency(
  id TEXT PRIMARY KEY,
  manifest_sha256 TEXT,
  status TEXT,
  applied_at TEXT
);
```

## 관련 노트

- [[ibujang-stripe-webhook-handler]] — Stripe 웹훅 멱등성 구현
- [[webhook-vault-write-pattern]] — Vault 쓰기 패턴
