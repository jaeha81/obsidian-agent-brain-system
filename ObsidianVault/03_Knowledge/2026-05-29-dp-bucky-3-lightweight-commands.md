---
title: 버키용 초경량 명령 3종
date: 2026-05-29
source: daily-plus/2026-05-29.md (Card 2)
priority: P1
category: knowledge
status: distilled
tags:
  - bucky
  - discord
  - command
  - idempotency
  - rollback
  - daily-plus
  - knowledge
---

# 버키용 초경량 명령 3종

> ChatGPT Pulse 2026-05-29 Card 2 증류 (P1 · knowledge)

## 목적
Discord에서 즉시 쓸 수 있는 버키 초경량 명령 3종: 일일저장, 실행요청, 긴급롤백. 각 명령에 idempotency_key + manifest_sha256 포함. 자주 사용하는 Bucky 작업을 최소한의 타이핑으로 안전하게 실행할 수 있는 표준 명령 포맷.

## 핵심 내용
- **명령 1: 일일저장** (`!daily-save`):
  ```json
  {"cmd":"daily_save","ikey":"ds-{YYYYMMDD}","sha":"{content_sha256}","ts":{unix}}
  ```
  - 오늘의 메모/노트를 Vault에 원자적으로 저장
  - 재실행 시 ikey 중복으로 자동 스킵
- **명령 2: 실행요청** (`!run`):
  ```json
  {"cmd":"run","task":"{task_id}","ikey":"run-{id}-{ts}","sha":"{plan_sha256}","ts":{unix}}
  ```
  - Bucky에게 특정 task_id 실행 요청
  - plan.json SHA256으로 계획 변조 여부 검증
- **명령 3: 긴급롤백** (`!rollback`):
  ```json
  {"cmd":"rollback","target":"{task_id}","reason":"...","ikey":"rb-{id}-{ts}","ts":{unix}}
  ```
  - 지정 task 즉시 롤백 트리거
  - reason 필드 필수 (감사 로그용)
- **재실행 안전 설계**: 모든 명령에 ikey 포함, 서버측 5분 내 중복 거부

## 구현 체크리스트
- [ ] 3종 명령 스키마 JSON Schema 정의
- [ ] Discord 봇 명령 핸들러 구현 (`!daily-save`, `!run`, `!rollback`)
- [ ] ikey 중복 체크 (Redis TTL 5분)
- [ ] 롤백 명령 감사 로그 기록
- [ ] 명령 실행 결과 Discord 응답 메시지

## 관련 컨텍스트
- JH용 디스코드 2k 안전 페이로드: `2026-05-29-dp-discord-2k-safe-payload.md`
- 검증자와 롤백 템플릿: `2026-05-27-dp-verifier-rollback-template.md`
- Bucky Discord 봇 구조: Vault Memory `project_discord_bucky.md`
