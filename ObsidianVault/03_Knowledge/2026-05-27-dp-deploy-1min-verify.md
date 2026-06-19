---
title: 배포 전 1분 검증 체크
date: 2026-05-27
source: daily-plus/2026-05-27.md (Card 2)
priority: P1
category: knowledge
status: distilled
tags:
- deployment
- webhook
- signature
- idempotency
- checklist
- daily-plus
- knowledge
graph_cluster: daily-practice
---

# 배포 전 1분 검증 체크

> ChatGPT Pulse 2026-05-27 Card 2 증류 (P1 · knowledge)

## 목적
웹훅 서명·전송·중복검증까지 붙여넣기 한 번으로 점검할 수 있는 1분 체크리스트. HMAC+타임스탬프, 멱등성, 원자적 파일쓰기 검증 포함. 배포 직전 빠른 신뢰성 확인을 위한 표준 절차.

## 핵심 내용
- **무결성 체크**: 페이로드 SHA256 해시 계산 후 수신측 검증 결과 일치 여부 확인
- **출처 인증**: HMAC-SHA256 서명 + 타임스탬프 5분 유효 창 내 검증
- **재전송 방지**: idempotency_key 중복 여부 DB/캐시 조회
- **원자적 파일쓰기**: tmp 파일 쓰기 후 mv 명령으로 원자 이동, 부분쓰기 방지
- **스크립트 스니펫 활용**:
  ```bash
  # 1분 검증 스크립트
  PAYLOAD=$(cat payload.json)
  SHA=$(echo -n "$PAYLOAD" | sha256sum | cut -d' ' -f1)
  HMAC=$(echo -n "$PAYLOAD" | openssl dgst -sha256 -hmac "$SECRET" | cut -d' ' -f2)
  echo "SHA256: $SHA"
  echo "HMAC: $HMAC"
  echo "Timestamp drift: $(( $(date +%s) - $TS )) seconds"
  ```

## 구현 체크리스트
- [ ] 배포 전 HMAC 서명 검증 스크립트 실행
- [ ] idempotency_key 중복 체크 엔드포인트 테스트
- [ ] 원자적 파일쓰기 (tmp→mv) 패턴 적용 여부 확인
- [ ] 타임스탬프 유효 창(5분) 설정 확인
- [ ] 웹훅 재전송 시뮬레이션 테스트 실행

## 관련 컨텍스트
- 버키 최소 명령 페이로드: `2026-05-27-dp-bucky-min-command-payload.md`
- 웹훅 옵시디언 안전 전달: `2026-05-28-dp-webhook-to-obsidian-safe.md`
- JH 구매대행 출시 점검표: `2026-05-29-dp-sniper-launch-checklist.md`
