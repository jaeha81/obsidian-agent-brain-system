---
type: knowledge-note
date: 2026-06-03
source: daily-plus
category: knowledge-candidate
tags:
- '#area/ai_automation'
- '#status/active'
summary: 가벼운 영상 도구체인 프롬프트 — ffmpeg, PySceneDetect, whisper.cpp, pyannote를 사용해 NDJSON
  매니페스트 출력하는 오프라인 영상 분석 파이프라인
status: applied
applied_at: 2026-06-11
graph_cluster: daily-practice
---

# 가벼운 영상 도구체인 프롬프트

> **주의**: 이 노트는 에이전트 프롬프트 변경을 포함하므로 staged knowledge note로만 보관.
> 구현 전 사용자 승인 필요.

## 도구체인 개요

오프라인 영상 분석 파이프라인. 외부 API 없이 로컬에서 전체 처리.

```
입력: 영상 파일 (mp4/mkv/avi)
출력: NDJSON 매니페스트 (events.ndjson)
```

## 도구 스택

| 도구 | 역할 | 설치 |
|------|------|------|
| ffmpeg | 영상 디코딩, 프레임 추출, VAD | 시스템 패키지 |
| PySceneDetect | 씬 경계 감지 | `pip install scenedetect` |
| whisper.cpp | 오프라인 STT | 별도 빌드 |
| pyannote/audio | 화자 분리 | `pip install pyannote.audio` |

## 실행 프롬프트 (에이전트용)

```
주어진 영상 파일에 대해 다음 단계를 순서대로 실행하고
결과를 NDJSON 형식으로 events.ndjson에 저장하라.

[Step 1] ffmpeg로 오디오 추출
  ffmpeg -i {input} -vn -ac 1 -ar 16000 audio.wav

[Step 2] PySceneDetect로 씬 경계 감지
  scenedetect -i {input} detect-content list-scenes
  → {"type":"scene","start":..,"end":..,"scene_id":..}

[Step 3] ffmpeg VAD로 음성 구간 감지
  → {"type":"vad","start":..,"end":..,"has_speech":..}

[Step 4] whisper.cpp STT (오프라인)
  ./whisper.cpp/main -m models/ggml-medium.bin -f audio.wav --output-json
  → {"type":"transcript","start":..,"end":..,"text":..}

[Step 5] pyannote 화자 분리
  from pyannote.audio import Pipeline
  pipeline = Pipeline.from_pretrained("pyannote/speaker-diarization")
  → {"type":"diarization","start":..,"end":..,"speaker":..}

[Step 6] ffmpeg 키프레임 추출 (씬 경계 기준)
  ffmpeg -i {input} -vf "select=..." frames/s{:03d}_t{:06.3f}.jpg
  → {"type":"keyframe","time":..,"scene_id":..,"path":..}

모든 이벤트를 타임스탬프 순으로 정렬하여 events.ndjson에 저장.
```

## NDJSON 매니페스트 스키마

```json
{
  "type": "scene|vad|transcript|diarization|keyframe",
  "start": 0.0,
  "end": 12.3,
  "scene_id": 1,
  "has_speech": true,
  "speaker": "SPEAKER_00",
  "text": "전사된 텍스트",
  "path": "frames/s001_t006.000.jpg",
  "confidence": 0.95
}
```

## 성능 가이드라인

| 영상 길이 | 예상 처리 시간 (CPU) |
|-----------|---------------------|
| 1분 | ~2분 |
| 10분 | ~15분 |
| 60분 | ~90분 |

whisper.cpp medium 모델 기준 (GPU 사용 시 3~5배 빠름)

## 출력 활용

생성된 `events.ndjson`은:
- TikTok/YouTube 콘텐츠 분석에 직접 사용
- Obsidian 영상 분석 노트 자동 생성 입력
- A/B 콘텐츠 비교 파이프라인 기초 데이터

## 관련 노트

- [[2026-06-03-dp-video-extraction-checklist]]
