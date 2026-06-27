---
title: 리플레이 드라이런과 승인 라인 프로토콜
date: 2026-06-28
source: daily-plus/2026-06-28.md (Card 4)
priority: P1
category: knowledge
status: distilled
tags:
- replay
- dry-run
- approval-line
- idempotent
- webhook
- data-integrity
- daily-plus
- knowledge
- source/today_plus
- type/reference
graph_cluster: data-integrity
---

# 리플레이 드라이런과 승인 라인 프로토콜

> ChatGPT Pulse 2026-06-28 Card 4 증류 (P1 · command-payload)

## 목적

스냅샷에서 재현(replay) 웹훅을 안전하게 수행하기 위한 흐름:
- 네트워크 전송 없이 서명/타임스탬프/멱등키 검증 (dry-run)
- 인간 1줄 승인 후에만 실제 POST 실행

## 핵심 원칙

| 원칙 | 설명 |
|------|------|
| 멱등성 | 동일 스냅샷 → 동일 `Idempotency-Key` → 중복 처리 방지 |
| 드라이런 | 실제 POST 전, 헤더/본문을 로컬에서 완전히 검증 |
| 인간 승인 | `APPROVE_REPLAY(...)` 한 줄이 있을 때만 에이전트가 실제 POST 실행 |

## 드라이런 흐름

```
스냅샷 파일 (.ndjson)
  → compact JSON payload 생성
  → sha256(snapshot) → RUN_ID
  → TS + BODY → HMAC 서명 (SIG)
  → 헤더/본문을 dryrun-{DAY}.txt에 출력 (네트워크 없음)
```

## 의사결정 헬퍼 (jq)

```bash
jq -r '
  if .snapshot_sha256 != null and .receipt_hmac_verified==true
  then "REPLAY_OK"
  elif .snapshot_sha256 != null and .receipt_hmac_verified==false
  then "REVIEW_HOLD"
  else "FORENSIC_HOLD" end
' ./evidence/evidence-YYYY-MM-DD.json
```

## 승인 라인 형식

### 재현 승인 (조건: snapshot_sha256 != null AND receipt_hmac_verified == true)

```
APPROVE_REPLAY(DAY=YYYY-MM-DD, RUN_ID=<run_id>, OPERATOR="<name>", REASON="snapshot+HMAC verified", TS="<ts>")
```

### 포렌식 홀드 (영수증/HMAC 실패)

```
HOLD_FORENSIC(DAYS=YYYY-MM-DD,..., OPERATOR="<name>", REASON="missing_receipt_or_hmac_failed")
```

## 최종 안전 절차

1. 드라이런으로 헤더/본문 확보 (`dryrun-{DAY}.txt`)
2. 증적 JSON의 sha256/receipt와 대조
3. 조건 충족 시 `APPROVE_REPLAY(...)` 한 줄을 오케스트레이터에 전달
4. 에이전트는 정확한 승인 라인이 있을 때만 실제 POST 수행

> 주의: Bucky 명령 규칙에 APPROVE_REPLAY/HOLD_FORENSIC 포맷을 통합하려면 별도 사용자 승인 필요.

## 연결 노트

- [[2026-06-28-dp-s3-reconciliation-audit-schema]]
- [[2026-06-28-dp-canary-write-safety-check]]
