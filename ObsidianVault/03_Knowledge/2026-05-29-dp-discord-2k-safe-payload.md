---
title: JH용 디스코드 2k 안전 페이로드
date: 2026-05-29
source: daily-plus/2026-05-29.md (Card 1)
priority: P1
category: knowledge
status: distilled
tags:
  - discord
  - payload
  - obsidian
  - bucky
  - idempotency
  - daily-plus
  - knowledge
---

# JH용 디스코드 2k 안전 페이로드

> ChatGPT Pulse 2026-05-29 Card 1 증류 (P1 · knowledge)

## 목적
오늘의 플러스를 디스코드→버키(브리지)→Obsidian(JH 경로)로 안전·중복없이 흡수시키는 플레이북. Discord 2000자 제한 내 페이로드 구조. 모든 daily-plus 노트를 신뢰할 수 있게 Vault로 전달하는 표준 방법.

## 핵심 내용
- **페이로드 포맷 (2000자 이내)**:
  ```json
  {
    "v": 1,
    "ikey": "dp-2026-05-29-001",
    "sha": "abc123...",
    "action": "vault_ingest",
    "path": "03_Knowledge/2026-05-29-dp-note.md",
    "content_b64": "<base64-encoded-content>",
    "ts": 1748476800,
    "hmac": "<HMAC-SHA256>"
  }
  ```
- **실제 값 교체 포인트**:
  - `ikey`: `dp-{날짜}-{순번}` 형식
  - `sha`: 콘텐츠 SHA256 앞 8자리
  - `content_b64`: 콘텐츠가 길면 분할 후 청크 번호 포함
- **분할 전략**: 단일 메시지 1800자 초과 시 `chunk: 1/3` 방식으로 분할, 수신측에서 재조합
- **2000자 한도 계산**: JSON 오버헤드 ~200자 고려, 실제 콘텐츠는 ~1600자 목표

## 구현 체크리스트
- [ ] 페이로드 빌더 함수 작성 (자동 분할 포함)
- [ ] ikey 자동 생성 (날짜+순번 조합)
- [ ] 수신측 청크 재조합 로직 구현
- [ ] HMAC 서명 생성/검증 함수
- [ ] Discord 봇 `/daily-plus` 명령 등록

## 관련 컨텍스트
- 버키용 최소 명령 페이로드: `2026-05-27-dp-bucky-min-command-payload.md`
- 버키용 초경량 명령 3종: `2026-05-29-dp-bucky-3-lightweight-commands.md`
- 웹훅 옵시디언 안전 전달: `2026-05-28-dp-webhook-to-obsidian-safe.md`
