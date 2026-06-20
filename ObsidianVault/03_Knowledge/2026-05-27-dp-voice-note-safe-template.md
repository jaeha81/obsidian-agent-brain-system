---
title: 음성노트 저장 안전 템플릿
date: 2026-05-27
source: daily-plus/2026-05-27.md (Card 3)
priority: P1
category: knowledge
status: distilled
tags:
- voice
- obsidian
- yaml-frontmatter
- stt
- privacy
- daily-plus
- knowledge
- source/today_plus
- type/reference
- area/obsidian_brain
graph_cluster: daily-practice
---

# 음성노트 저장 안전 템플릿

> ChatGPT Pulse 2026-05-27 Card 3 증류 (P1 · knowledge)

## 목적
Obsidian에 음성 전사 노트를 안전하게 쌓고 브리지로 전송·중복검사하는 최소 템플릿. 세그먼트 타임스탬프, STT 엔진, 신뢰도, 동의 플래그 포함 YAML 프런트매터. 프라이버시를 보장하면서 검색 가능한 구조적 음성 기록 유지.

## 핵심 내용
- **YAML 음성 메타 필드 구조**:
  ```yaml
  ---
  title: 음성노트 {날짜} {시간}
  date: 2026-05-27T14:30:00
  type: voice-note
  stt_engine: whisper.cpp
  stt_model: medium
  confidence: 0.92
  duration_sec: 45
  idempotency_key: voice-2026-05-27-143000
  consent_flag: true
  segments:
    - start: 0.0
      end: 5.2
      text: "첫 번째 세그먼트 텍스트"
    - start: 5.2
      end: 12.8
      text: "두 번째 세그먼트 텍스트"
  ---
  ```
- **브리지 전송 구조**: 음성 → STT → YAML 노트 생성 → idempotency 체크 → Obsidian Vault 저장
- **idempotency 체크**: 같은 오디오 파일의 SHA256이 이미 처리됐으면 스킵
- **동의 플래그**: `consent_flag: true` 필드로 명시적 저장 동의 기록

## 구현 체크리스트
- [ ] YAML 프런트매터 스키마 확정 및 검증 함수 작성
- [ ] 오디오 파일 SHA256 기반 idempotency 체크 구현
- [ ] whisper.cpp 세그먼트 타임스탬프 파싱 → YAML 변환
- [ ] Obsidian 볼트 음성노트 폴더 구조 설정 (`03_Knowledge/voice/`)
- [ ] consent_flag 없는 노트 저장 거부 로직

## 관련 컨텍스트
- 음성 파이프라인 운영 기준: `2026-05-27-dp-voice-pipeline-ops-standard.md`
- 음성에서 의도로 넘기기: `2026-05-28-dp-voice-to-intent-pipeline.md`
- 로컬 우선 음성 전사 플레이북: `2026-05-29-dp-local-first-voice-playbook.md`

## 관련 노트
- [[hubs/JH System]]
