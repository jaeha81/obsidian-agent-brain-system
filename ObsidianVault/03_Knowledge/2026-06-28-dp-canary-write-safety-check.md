---
title: 안전 쓰기용 캐나리 점검 계획
date: 2026-06-28
source: daily-plus/2026-06-28.md (Card 3)
priority: P1
category: knowledge
status: distilled
tags:
- canary-write
- safe-write
- hmac
- webhook
- s3-receipt
- data-integrity
- daily-plus
- knowledge
- source/today_plus
- type/reference
graph_cluster: data-integrity
---

# 안전 쓰기용 캐나리 점검 계획

> ChatGPT Pulse 2026-06-28 Card 3 증류 (P1 · verification)

## 목적

대량 재수집(auto-write) 전에 안전한 쓰기 경로를 5분 안에 검증하는 카나리아(canary) 체크리스트.

## 전체 흐름

```
합성 카나리아 노트 생성 (고유 ID 발급)
  → sha256 + HMAC 생성
  → 멱등키 포함 웹훅 POST
  → S3 영수증 검증 (120초 내)
  → 성공: "safe_for_auto_writes" 30분 태깅
  → 실패: 원인별 차단 (TIMEOUT / HMAC_FAIL / CHECKSUM_FAIL)
```

## 카나리아 노트 규칙

- 프론트매터가 본문보다 반드시 먼저
- 줄바꿈: LF(Unix)만, 행 끝 공백 제거
- `canary_id`: `canary-YYYYMMDD-{{rand8}}` (고유값)

## 해시·서명 생성 (셸 원라이너)

```bash
TS=$(date -u +%Y-%m-%dT%H:%M:%SZ)
BODY=$(cat canary.md | sed -e 's/\r//g')
SHA=$(printf '%s' "$BODY" | openssl dgst -sha256 -binary | xxd -p -c 256)
SIG=$(printf '%s.%s' "$TS" "$BODY" | openssl dgst -sha256 -hmac "$WEBHOOK_SECRET" -binary | xxd -p -c 256)
```

## 웹훅 POST 헤더

| 헤더 | 값 |
|------|----|
| `Idempotency-Key` | `canary.<SHA>` (중복 방지) |
| `X-Timestamp` | `$TS` |
| `X-Signature` | `sha256=$SIG` |

## 성공 기준

- 120초 내 S3 영수증 존재: `s3://audit/canaries/<canary_id>.receipt.json`
- 영수증 HMAC 검증 통과
- S3 `full_sha256 == $SHA`

## 실패 모드와 대응

| 실패 | 표시 | 대응 |
|------|------|------|
| 120초 내 영수증 없음 | `FAILURE_TIMEOUT` | reconcile 실행 |
| 영수증 있음 + HMAC 불일치 | `FAILURE_HMAC` | 운영자 에스컬레이션 |
| HMAC 정상 + 체크섬 불일치 | `FAILURE_CHECKSUM` | 자동 재조정 |

## 승인 라인 형식

실패 시 에이전트 정지:

```
HOLD_CANARY(<canary_id>): reason=<HMAC|CHECKSUM>, operator=<NAME>
```

성공 시: `canary_passed` 이벤트 방출 + `safe_for_auto_writes(30분)` 태그

## 체크리스트

- [ ] LF 정규화, 행 끝 공백 제거
- [ ] `canary_id` 고유값 사용
- [ ] `$SHA/$SIG` 계산 및 헤더 포함
- [ ] 120초 타이머 시작
- [ ] S3 영수증 존재·서명·체크섬 확인
- [ ] 결과에 따라 HOLD 또는 safe 태그 처리

## 연결 노트

- [[2026-06-28-dp-s3-reconciliation-audit-schema]]
- [[2026-06-28-dp-replay-dryrun-approval-protocol]]
