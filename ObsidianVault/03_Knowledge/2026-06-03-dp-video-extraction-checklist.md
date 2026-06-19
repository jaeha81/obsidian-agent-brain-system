---
graph_cluster: daily-practice
---

# 영상 추출 우선순위 체크리스트

## 파이프라인 설계 원칙

단계를 분리하여 각 단계가 완료된 후 다음으로 진행한다.
무거운 작업(OCR, 메타데이터 확장)은 경량 단계 완료 후에 실행한다.

## Stage 1: 기초 추출 (먼저 실행)

우선순위 순서대로 실행:

- [ ] **샷 경계 감지** — PySceneDetect로 씬 전환 타임스탬프 추출
- [ ] **VAD (음성 활동 감지)** — 음성 구간과 무음 구간 분리
- [ ] **STT (음성→텍스트)** — whisper.cpp로 전사 (오프라인)
- [ ] **화자 분리 (Diarization)** — pyannote로 화자별 구간 태깅
- [ ] **키프레임 추출** — 씬당 대표 프레임 1~3장 저장

## Stage 2: 보완 추출 (Stage 1 완료 후)

- [ ] **메타데이터 추가** — 영상 속성, 코덱, 해상도, fps
- [ ] **OCR** — 키프레임에서 텍스트 추출 (tesseract)
- [ ] **썸네일 생성** — 대표 키프레임 → 썸네일 저장

## Stage 1 출력 형식 (NDJSON)

각 라인이 독립적인 이벤트로 구성:

```ndjson
{"type":"scene","start":0.0,"end":12.3,"scene_id":1}
{"type":"vad","start":2.1,"end":11.8,"has_speech":true}
{"type":"transcript","start":2.1,"end":11.8,"speaker":"S1","text":"안녕하세요."}
{"type":"keyframe","time":6.0,"scene_id":1,"path":"frames/s001_t006.jpg"}
{"type":"diarization","start":2.1,"end":5.3,"speaker":"SPEAKER_00"}
```

## 도구 체인

| 단계 | 도구 | 오프라인 여부 |
|------|------|--------------|
| 샷 경계 | PySceneDetect | 오프라인 |
| VAD | ffmpeg + silero-vad | 오프라인 |
| STT | whisper.cpp | 오프라인 |
| 화자 분리 | pyannote/audio | 오프라인 (모델 캐시) |
| 키프레임 | ffmpeg | 오프라인 |
| OCR | tesseract | 오프라인 |

## 실행 순서 이유

1. 샷 경계가 있어야 키프레임 위치를 결정할 수 있음
2. VAD가 있어야 STT 구간을 정확히 분리할 수 있음
3. STT + 화자 분리는 동시에 실행 가능 (독립적)
4. OCR은 키프레임이 준비된 후에만 실행 가능

## 관련 노트

- [[2026-06-03-dp-lightweight-video-toolchain]]
