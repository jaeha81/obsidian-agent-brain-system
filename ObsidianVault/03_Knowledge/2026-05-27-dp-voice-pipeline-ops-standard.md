---
title: 음성 파이프라인 운영 기준표
date: 2026-05-27
source: daily-plus/2026-05-27.md (Card 4)
priority: P1
category: knowledge
status: distilled
tags:
- voice
- stt
- discord
- privacy
- pipeline
- daily-plus
- knowledge
graph_cluster: daily-practice
---

# 음성 파이프라인 운영 기준표

> ChatGPT Pulse 2026-05-27 Card 4 증류 (P1 · knowledge)

## 목적
디스코드 음성→텍스트(STT) 파이프라인 운영 체크카드. 낮은 지연, 안정적 전송, 프라이버시 준수 3원칙. 로컬 우선 STT, 저장 옵트인, VAD 발화 감지 기반 운영으로 신뢰할 수 있는 음성 처리 시스템 구축.

## 핵심 내용
- **로컬 우선 원칙**: whisper.cpp 또는 유사 로컬 모델 기본 사용, 네트워크 장애 시 무중단
- **저장 = 명시적 옵트인**: 사용자가 저장 명령을 내리지 않으면 버퍼에만 유지, 자동 저장 금지
- **VAD(Voice Activity Detection) 설정**:
  - 침묵 임계값: 500ms 이상 묵음 시 세그먼트 분리
  - 에너지 임계값: 환경 노이즈 대비 +15dB 이상만 처리
  - 최소 발화 길이: 0.3초 이하 무시
- **재전송 체크**: 각 세그먼트에 SHA256 해시, 중복 수신 시 무시
- **지연 목표**: 발화 종료 후 2초 이내 텍스트 출력
- **프라이버시 준수**:
  - 원본 오디오는 처리 후 즉시 삭제 (메모리/디스크 모두)
  - 전사 텍스트만 옵트인 시 보관
  - 제3자 STT API 사용 시 사용자 명시 동의 필수

## 구현 체크리스트
- [ ] VAD 파라미터 설정 (침묵 임계값, 에너지 임계값, 최소 발화 길이)
- [ ] whisper.cpp 로컬 설치 및 모델 선택 (medium/large)
- [ ] 세그먼트 SHA256 중복 방지 캐시 구현
- [ ] 원본 오디오 자동 삭제 로직 (처리 후 즉시)
- [ ] 저장 명령 수신 전 버퍼 only 모드 확인
- [ ] 지연 모니터링 (발화 종료 → 텍스트 출력 시간 측정)

## 관련 컨텍스트
- 음성노트 저장 안전 템플릿: `2026-05-27-dp-voice-note-safe-template.md`
- 음성에서 의도로 바로 넘기기: `2026-05-28-dp-voice-to-intent-pipeline.md`
- 디스코드 음성 API 변화 체크: `2026-05-29-dp-discord-voice-api-changes.md`

## 관련 노트
- [[hubs/JH System]]
