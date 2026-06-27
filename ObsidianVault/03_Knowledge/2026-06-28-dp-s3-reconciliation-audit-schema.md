---
title: S3 재조정 스크립트와 감사 스키마
date: 2026-06-28
source: daily-plus/2026-06-28.md (Card 2)
priority: P1
category: knowledge
status: distilled
tags:
- s3-audit
- reconciliation
- sha256
- data-integrity
- audit-schema
- daily-plus
- knowledge
- source/today_plus
- type/reference
graph_cluster: data-integrity
---

# S3 재조정 스크립트와 감사 스키마

> ChatGPT Pulse 2026-06-28 Card 2 증류 (P1 · verification)

## 목적

S3에 쌓이는 데이터 스냅샷/로그가 "제대로 써졌는지"를 자동으로 검증·증거화하는 재조정(reconciliation) 패턴.

## 핵심 흐름

```
S3 객체 목록 (사전식 순서)
  → 연결(concat) → sha256 계산
  → 기록된 감사 해시와 비교
  → checksum_drift 판정
  → 결과를 S3 JSON 증적으로 저장
```

## 최소 구현 (~100줄, idempotent)

Python, ~100줄. 핵심 단계:

1. `s3.list_objects_v2` → 사전식 정렬
2. 파일들을 concat → `sha256` 계산
3. `audit.json`에서 기록된 해시 로드 → `checksum_drift` 판정 (0 = 정상, 1 = 드리프트)
4. `reconcile.json`으로 결과 저장 (idempotent)

필요 권한: `s3:ListObjectsV2`, `s3:GetObject`, `s3:PutObject`

## S3 감사 증적 스키마 (권장)

경로: `s3://audit/writes/<write_id>.json`

| 필드 | 설명 |
|------|------|
| `write_id` | uuid 또는 `canary.<sha>` |
| `intent` | `day-snapshot / chunked-stream / canary-write` |
| `full_sha256` | 전체 concat 해시 |
| `frontmatter_hash` | 프론트매터 정규화 해시 |
| `body_hash` | 본문 정규화 해시 |
| `receipt_signature` | `sha256=<hex>` |
| `hmac_verified` | `true / false` |
| `reconcile_status` | `ok / drift / missing` |
| `checksum_drift_bytes` | 드리프트 바이트 수 |
| `idempotency_key` | `canary.<full_sha>` |

## 대시보드 핵심 지표

| 지표 | 설명 |
|------|------|
| `last_sync_ts` | 볼트/프리픽스별 최신 동기화 시각 |
| `checksum_drift_count` | 최근 7일 중 drift>0 일수 |
| `missing_day_count` | 빠진 일자 수 |
| `reconcile_last_run` | 마지막 대조 실행 시각 |
| `orphan_receipt_count` | 고아 영수증 수 (receipt는 있으나 실제 객체 없음) |

## 운영 조치 매핑

| 조건 | 조치 |
|------|------|
| `checksum_drift>0` + `hmac_verified==true` | REVIEW 티켓 + 단일 일자 인가 리플레이 (APPROVE_REPLAY) |
| `missing_day_count>0` | forensic_hold 마킹 + DENY_AND_HOLD (수동 복구 전까지 재생성 금지) |

## 연결 노트

- [[2026-06-28-dp-canary-write-safety-check]]
- [[2026-06-28-dp-replay-dryrun-approval-protocol]]
