---
title: 디스코드 음성 API 변화 체크
date: 2026-05-29
source: daily-plus/2026-05-29.md (Card 5)
priority: P3
category: knowledge
status: distilled
tags:
- discord
- voice-api
- spatial-audio
- bot
- monitoring
- daily-plus
- knowledge
- source/today_plus
- type/reference
- source/discord
graph_cluster: daily-practice
---

# 디스코드 음성 API 변화 체크

> ChatGPT Pulse 2026-05-29 Card 5 증류 (P3 · knowledge)

## 목적
Discord의 실험적 공간 오디오 기능 및 음성 API 변화 모니터링. 향후 봇·녹음·캡처 설계에 영향. 주요 변화 감시 전략. Discord 음성 API 변경이 Bucky 봇의 음성 캡처 기능에 미치는 영향을 사전에 파악.

## 핵심 내용
- **변화 감시 소스**:
  - Discord 공식 개발자 블로그: https://discord.com/developers
  - discord.py 라이브러리 CHANGELOG
  - Discord Developer Server (공식 Discord)
  - GitHub: discord/discord-api-docs
- **봇 설계 영향 포인트**:
  - 공간 오디오(Spatial Audio): 사용자별 3D 위치 정보 포함 가능 → 발화자 분리 개선
  - Voice Gateway 버전 변경: 연결 코드 하위호환성 체크 필요
  - 오디오 코덱 변경: Opus 설정 재확인
- **호환성 체크리스트**:
  - [ ] discord.py 최신 버전으로 업데이트 후 음성 연결 테스트
  - [ ] Voice Gateway v4/v8 지원 여부 확인
  - [ ] 오디오 수신 패킷 포맷 변경 여부 확인
  - [ ] 음성 캡처 봇 재연결 로직 안정성 테스트

## 구현 체크리스트
- [ ] Discord API 변경 RSS 또는 GitHub Watch 설정
- [ ] 분기별 호환성 테스트 스크립트 작성
- [ ] 공간 오디오 기능 릴리즈 시 봇 업데이트 계획 수립

## 관련 컨텍스트
- 음성 파이프라인 운영 기준표: `2026-05-27-dp-voice-pipeline-ops-standard.md`
- Discord Bucky 봇 구조: Vault Memory `project_discord_bucky.md`
- 이 항목은 P3(낮은 우선순위)이므로 정기 모니터링 항목으로 관리

## 관련 노트
- [[hubs/JH System]]
