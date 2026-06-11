---
title: 로컬 우선 음성 전사 플레이북
date: 2026-05-29
source: daily-plus/2026-05-29.md (Card 4)
priority: P1
category: knowledge
status: distilled
tags:
  - stt
  - local-first
  - whisper
  - privacy
  - obsidian
  - daily-plus
  - knowledge
---

# 로컬 우선 음성 전사 플레이북

> ChatGPT Pulse 2026-05-29 Card 4 증류 (P1 · knowledge)

## 목적
프라이버시를 지키면서 음성→의도로 바꾸는 로컬-퍼스트 파이프라인. 네트워크 장애와 무관하게 PC 한 대로 즉시 텍스트/명령 변환 후 Obsidian 자동 기록. 클라우드 의존 없이 개인 정보를 완전히 통제하는 음성 입력 시스템.

## 핵심 내용
- **아키텍처 설계**:
  ```
  마이크 → VAD(silero-vad) → 청크 → whisper.cpp(로컬)
       ↓ 장애 시
  → whisper API(원격 폴백)
       ↓
  → Intent Parser → Bucky 명령 / Obsidian 노트
  ```
- **폴백 경로**:
  1. whisper.cpp 타임아웃 3초 → OpenAI Whisper API
  2. 네트워크 없음 → 큐에 오디오 저장, 온라인 복귀 시 처리
- **Obsidian 연동 방식**:
  - Local REST API 플러그인 사용 (포트 27124)
  - 직접 파일시스템 쓰기 (REST API 없을 때 폴백)
- **프라이버시 보호**:
  - 원본 오디오: 전사 완료 후 즉시 삭제
  - 전사 텍스트: 명시적 저장 명령 시에만 Vault에 기록
  - 원격 폴백 사용 시 사용자 알림

## 구현 체크리스트
- [ ] whisper.cpp 설치 및 ko 모델 준비 (medium.ko)
- [ ] silero-vad 또는 WebRTC VAD 설정
- [ ] 오프라인 큐 구현 (SQLite, 오디오 파일 경로 저장)
- [ ] Obsidian REST API 플러그인 설치 및 인증 토큰 설정
- [ ] 프라이버시 보호 로직 (오디오 자동 삭제 확인)

## 관련 컨텍스트
- 음성에서 의도로 바로 넘기기: `2026-05-28-dp-voice-to-intent-pipeline.md`
- 음성 파이프라인 운영 기준표: `2026-05-27-dp-voice-pipeline-ops-standard.md`
- 로컬 에이전트 오프라인 우선 경로: `2026-05-28-dp-local-agent-offline-first.md`
