---
title: 웹훅 & Vault 쓰기 패턴 (이부장)
date: 2026-06-03
source: daily-plus/2026-06-03.md (Card 7)
tags:
  - ibujang
  - webhook
  - vault
  - idempotency
  - obsidian
  - knowledge
category: knowledge
status: distilled
---

# 웹훅과 Vault 쓰기 패턴

> ChatGPT Pulse 2026-06-03 Card 7 증류

## 3가지 핵심 원칙

1. **중복 방지**: INSERT OR IGNORE로 같은 이벤트 1회만 처리
2. **변경 시에만 쓰기**: manifest_sha256 비교 → 동일하면 204 no_change
3. **Obsidian 트리아지 노트 자동 생성**: 변경 있을 때만 표준 포맷으로 기록

## 최소 웹훅 페이로드

```http
POST /triage HTTP/1.1
Content-Type: application/json
X-Signature: sha256=<hex>
X-Timestamp: 2026-06-02T08:00:00Z
```

```json
{
  "manifest_id": "dailyops-<uuid>",
  "triage": "approve",
  "idempotency_key": "<id>",
  "manifest_sha256": "<sha>"
}
```

## 멱등성 처리 (SQLite)

```sql
CREATE TABLE IF NOT EXISTS idempotency (
  id TEXT PRIMARY KEY,
  manifest_sha256 TEXT NOT NULL,
  status TEXT NOT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 처리 시작
INSERT OR IGNORE INTO idempotency(id, manifest_sha256, status)
VALUES (?, ?, 'applied');
-- 이미 있으면 → HTTP 200 {status:"duplicate"}
```

## 변경 감지 (Python)

```python
if existing_file.manifest_sha256 == payload.manifest_sha256:
    return HTTP 204  # no_change
# 다르면 처리 진행
```

## Obsidian 트리아지 노트 포맷

```yaml
---
title: 2026-06-02-오늘의_플러스
triage: approve
agent: ibujang
manifest_sha256: <sha>
created_at: 2026-06-02T08:00:00Z
---
Approved — created followups: Jh/Tasks/task-123.md
```

**Vault 경로 규칙**: `Jh/Daily/YYYY/YYYY-MM-DD-오늘의_플러스-<triage>.md`

## Dataview 쿼리

```dataview
TABLE created_at, triage, manifest_sha256
FROM "Jh/Daily"
WHERE agent = "ibujang" AND triage = "approve"
SORT created_at DESC
```

## Bucky 브리지 호출 원라인

```bash
curl -X POST https://bucky.internal/exec \
 -H 'X-Signature: sha256=<hex>' \
 --data '{"action":"write_note","vault_path":"Jh/Daily/2026/2026-06-03-오늘의_플러스-approve.md","content":"..."}'
```

## 빠른 체크리스트

- [ ] X-Signature HMAC 검증
- [ ] X-Timestamp ±5분 확인
- [ ] INSERT OR IGNORE 멱등성
- [ ] manifest_sha256 동일 시 204 반환
- [ ] 변경 시에만 Obsidian 노트 작성
- [ ] Dataview 쿼리로 결과 가시화

## 관련 노트

- [[ibujang-api-contract-and-handoff]] — API 계약 상세
- [[ibujang-pulse-manager-manifest]] — 펄스 매니저 HMAC 매니페스트
