---
title: 버키용 최소 명령 페이로드
date: 2026-05-27
source: daily-plus/2026-05-27.md (Card 1)
priority: P1
category: knowledge
status: distilled
tags:
- bucky
- discord
- idempotency
- hmac
- command-payload
- daily-plus
- knowledge
graph_cluster: daily-practice
---

# 버키용 최소 명령 페이로드

> ChatGPT Pulse 2026-05-27 Card 1 증류 (P1 · knowledge)

## 목적
디스코드에서 한 번에 복붙·즉시 실행되는 버키 단일 명령 템플릿. 재시도 중복 방지(idempotency key), SHA256 콘텐츠 무결성, HMAC-SHA256 서명 검증을 한 줄에 포함. Discord 2000자 제한 내에서 안전하게 운영 가능한 최소 구조.

## 핵심 내용
- **idempotency_key 포함 페이로드 구조**: UUID v4 또는 날짜+액션 해시 조합으로 재실행 시 중복 방지
- **sha256 필드**: 페이로드 콘텐츠의 SHA256 해시를 포함하여 전송 중 변조 감지
- **HMAC 서명 방식**: HMAC-SHA256으로 발신자 인증, 타임스탬프 포함으로 재전송 공격 방지
- **Discord 2000자 제한 고려**: 핵심 필드만 포함한 최소 구조, 추가 데이터는 참조 링크로 분리
- **페이로드 예시**:
  ```json
  {
    "idempotency_key": "jh-2026-05-27-save-001",
    "action": "daily_save",
    "sha256": "<content-hash>",
    "hmac": "<HMAC-SHA256-signature>",
    "ts": 1748390400
  }
  ```

## 구현 체크리스트
- [ ] idempotency_key 생성 로직 구현 (UUID v4 또는 날짜+액션 조합)
- [ ] SHA256 콘텐츠 해시 계산 함수 추가
- [ ] HMAC-SHA256 서명 생성/검증 모듈 작성
- [ ] Discord 2000자 제한 내 페이로드 크기 검증 로직
- [ ] 서버측 idempotency_key 중복 체크 (DB 또는 인메모리 캐시)

## 관련 컨텍스트
- Bucky Discord 봇 구조: `ObsidianVault/03_Projects/agents/bucky.md`
- 웹훅 브리지 안전 전달: `2026-05-28-dp-webhook-to-obsidian-safe.md`
- 배포 전 검증 체크: `2026-05-27-dp-deploy-1min-verify.md`

## 관련 노트
- [[hubs/JH System]]
