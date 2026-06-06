---
title: 영상 파이프라인 체크리스트 & 도구체인
date: 2026-06-03
source: daily-plus/2026-06-03.md (Card 8, 9)
tags:
  - video
  - pipeline
  - content-automation
  - whisper
  - ffmpeg
  - knowledge
category: knowledge
status: distilled
---

# 영상 추출 파이프라인 & 도구체인

> ChatGPT Pulse 2026-06-03 Card 8 + Card 9 증류

## 3단계 우선순위

### 1단계 — 필수 (Mandatory)

- **샷 경계 감지**: start/end, 전환 타입 (컷/페이드/디졸브)
- **VAD (음성 활동 감지)**: 말소리 구간만 표시 → STT 비용 절감
- **STT + 타임스탬프**: whisper.cpp 또는 WhisperX
- **화자 분리**: pyannote — 화자 라벨과 턴 타임스탬프
- **키프레임 추출**: 샷 대표 1장 + SHA-256 해시
- **NDJSON 매니페스트**: type/start/end/lang/confidence/text/speaker

### 2단계 — 있으면 좋은 것 (Helpful)

- 장면 메타데이터: 카메라 움직임, 지배 색상, 평균 휘도
- OCR: Tesseract로 화면 텍스트 추출
- 언어 감지, ASR 세부 신뢰도, 겹침 발화 플래그

### 3단계 — Phase-2로 미루기

- 얼굴 검출/클러스터링 (개인정보 고려)
- 객체 검출 (YOLO), 감정 점수, CLIP 시맨틱 태깅

## 파이프라인 순서

```
입력 → 샷 경계(PySceneDetect) → VAD → STT(WhisperX)
     → 화자 분리(pyannote) → 키프레임(ffmpeg) → OCR(Tesseract)
     → NDJSON 내보내기
```

## 경량 스택

| 역할 | 도구 |
|------|------|
| 장면 분할 | PySceneDetect + ffmpeg |
| ASR | whisper.cpp / WhisperX (오프라인) |
| 화자 분리 | pyannote.audio + Silero VAD |
| OCR | Tesseract |
| 결과 포맷 | NDJSON |

## NDJSON 예시

```jsonl
{"type":"shot","start":0.00,"end":3.21,"transition":"cut","keyframe":"kf/0001.jpg","keyframe_sha256":"..."}
{"type":"speech","start":0.98,"end":2.85,"lang":"ko","confidence":0.91,"text":"안녕하세요.","speaker":"S1"}
{"type":"vad","start":0.90,"end":3.00}
{"type":"ocr","start":1.10,"end":1.40,"text":"SALE 50%","bbox":[100,200,300,50]}
```

## 에이전트 실행 프롬프트 (Claude/Codex/이부장용)

```
Task: analyze <VIDEO_URL> and return a single NDJSON manifest + artifact URLs.
Tools allowed: ffmpeg, PySceneDetect, whisper.cpp/WhisperX, pyannote.
Deliverables:
  1) shots[] with {id,start_s,end_s,cut_type,keyframe_url,keyframe_sha256}
  2) audio_tracks[] with segments {start_s,end_s,speaker_label,transcript,asr_confidence}
  3) scene_metadata {dominant_color,avg_luminance,camera_motion_label}
  4) quick_summary: 3줄 요약 (KOR/ENG)
  5) artifacts: {thumbnails[], transcripts[], diarization_rttm}
Output: NDJSON to /outputs/<video_id>.ndjson + {"manifest_url":"...","status":"completed"}
```

## 설치 (초간단)

```bash
pip install scenedetect pyannote.audio torch pytesseract
# OS: brew install ffmpeg tesseract  /  apt install ffmpeg tesseract-ocr
# whisper.cpp: 빌드 후 ./main -m models/ggml-base.en.bin -f audio.wav
```

## 비용 관리 팁

- VAD로 말소리 구간만 STT → 처리 비용 대폭 절감
- 샷 단위 병렬 처리
- 키프레임 해시로 중복 처리 방지

## 관련 허브

- [[vibe-coding-pipeline]] — AI 서비스 24분 파이프라인
- [[vault-galaxy-graph-bridge]] — 전체 지식 허브
- [[jh-system]] — JH 통합 시스템
