---
title: 음성에서 의도로 바로 넘기기
date: 2026-05-28
source: daily-plus/2026-05-28.md (Card 11)
priority: P1
category: knowledge
status: distilled
tags:
- stt
- whisper
- voice
- intent
- pipeline
- obsidian
- daily-plus
- knowledge
graph_cluster: daily-practice
---

# 음성에서 의도로 바로 넘기기

> ChatGPT Pulse 2026-05-28 Card 11 증류 (P1 · knowledge)

## 목적
디스코드-음성→텍스트 파이프라인의 최소 구성 청사진. 음성은 로컬 우선(whisper.cpp), 장애·지연 시 원격 STT 폴백, 웹훅 HMAC+idempotency 강제. 음성 입력을 즉시 실행 가능한 Bucky 명령이나 Obsidian 노트로 변환하는 전체 흐름 설계.

## 핵심 내용
- **아키텍처 1줄 설계**:
  ```
  Discord Voice → VAD → whisper.cpp → Intent Parser → Bucky / Obsidian
  ```
- **whisper.cpp 설정**:
  ```bash
  ./main -m models/ggml-medium.bin \
    --language ko \
    --output-json \
    --word-thold 0.01 \
    -f input.wav
  ```
- **폴백 트리거**: whisper.cpp 응답 3초 초과 시 OpenAI Whisper API 또는 Google STT로 전환
- **Intent Parser 로직**:
  - 키워드 매칭: "버키 저장해", "노트", "실행해" 등
  - JSON 출력: `{"intent": "save_note", "content": "...", "confidence": 0.95}`
- **보안 설정**:
  - 웹훅 HMAC-SHA256 서명 강제
  - idempotency_key: 오디오 청크 SHA256
  - 원본 오디오 처리 후 즉시 삭제

## 구현 체크리스트
- [ ] whisper.cpp 로컬 빌드 및 한국어 모델 다운로드
- [ ] VAD 설정 (침묵 감지 임계값)
- [ ] Intent Parser 키워드 사전 구축
- [ ] 폴백 STT API 연동 (OpenAI Whisper)
- [ ] Bucky 명령 전달 웹훅 구현

## 관련 컨텍스트
- 음성 파이프라인 운영 기준표: `2026-05-27-dp-voice-pipeline-ops-standard.md`
- 음성노트 저장 안전 템플릿: `2026-05-27-dp-voice-note-safe-template.md`
- 로컬 우선 음성 전사 플레이북: `2026-05-29-dp-local-first-voice-playbook.md`

## 관련 노트
- [[hubs/JH System]]
