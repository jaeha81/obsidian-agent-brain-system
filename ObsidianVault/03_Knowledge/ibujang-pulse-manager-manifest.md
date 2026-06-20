---
title: 이부장 펄스 매니저 매니페스트
date: 2026-06-03
source: daily-plus/2026-06-03.md (Card 6)
tags:
- ibujang
- pulse
- manifest
- hmac
- daily-plus
- knowledge
- source/today_plus
- type/reference
category: knowledge
status: distilled
graph_cluster: misc
---

# 이부장 펄스 매니저 매니페스트

> ChatGPT Pulse 2026-06-03 Card 6 증류

## 목적

오늘의_플러스 triage를 위한 초소형 매니페스트.
HMAC 검증 + 변경 감지 + 4가지 CTA(승인/구현/대기/보관)만 포함.

## 최소 매니페스트 JSON

```json
{
  "agent": "ibujang",
  "idempotency_key": "<id>",
  "hmac_kid": "hk1",
  "vault_path": "Jh/Daily/2026/2026-06-03-오늘의_플러스.md",
  "emit_on_change": true,
  "sig_hdr": "X-Signature",
  "ts_hdr": "X-Timestamp",
  "state": "idle",
  "actions": ["approve", "implement", "queue", "archive"]
}
```

## 수신 측 구현 포인트

1. `hmac_kid`로 키 조회 → X-Signature 검증 (±5분 스큐 허용)
2. `vault_path` 파일 존재 시 현재 내용 해시와 비교
3. 최초 저장/갱신 시 YAML front-matter에 `manifest_sha256` 기록
4. `actions` → UI/에이전트 라우팅에 직접 매핑

## Vault 경로 자동화

날짜를 자동으로 오늘 날짜로 변경:
```
vault_path: Jh/Daily/YYYY/YYYY-MM-DD-오늘의_플러스.md
```

## 관련 노트

- [[webhook-vault-write-pattern]] — Vault 쓰기 패턴 상세
- [[ibujang-api-contract-and-handoff]] — API 계약 전체
