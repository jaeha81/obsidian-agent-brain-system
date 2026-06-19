---
title: 프라이버시 우선 STT 운영안
date: 2026-06-09
source: daily-plus/2026-06-09.md (Card 4)
priority: P2
category: knowledge
status: distilled
tags:
- stt
- vosk
- whisper
- privacy
- local-first
- daily-plus
- knowledge
graph_cluster: daily-practice
---

# 프라이버시 우선 STT 운영안

> ChatGPT Pulse 2026-06-09 Card 4 증류 (P2 · knowledge-candidate)

## 목적

태블릿/PC 로컬에서 동작하는 음성 인식(STT) 파일럿 설계. 외부 클라우드 전송 없이 현장 음성 데이터를 처리한다.

## 기본 설정 — VOSK small-ko

```python
from vosk import Model, KaldiRecognizer
import wave

model = Model("vosk-model-small-ko-0.22")  # ~50-100MB

def transcribe(wav_path: str) -> str:
    wf = wave.open(wav_path, "rb")
    rec = KaldiRecognizer(model, wf.getframerate())
    result = []
    while True:
        data = wf.readframes(4000)
        if len(data) == 0:
            break
        if rec.AcceptWaveform(data):
            result.append(rec.Result())
    result.append(rec.FinalResult())
    return " ".join(r for r in result if r)
```

- 모델 크기: ~50-100MB (소형 모델)
- 처리 속도: 실시간의 약 0.5x (음성 1분 → 처리 30초)
- 정확도: 건설/인테리어 전문용어 인식 시 사전 추가 필요

## 폴백 — whisper.cpp + 클라우드

| 단계 | 조건 | 방법 |
|------|------|------|
| 1차 | 항상 | VOSK 로컬 처리 |
| 2차 | 정확도 < 85% | whisper.cpp 로컬 (larger 모델) |
| 3차 | 긴급/오프라인 불가 | OpenAI Whisper API (클라우드) |

whisper.cpp 설정:
```bash
./whisper -m models/ggml-small.bin -l ko -f input.wav
```

## 프라이버시 설계 원칙

1. **로컬 우선**: 음성 데이터는 기기 밖으로 전송하지 않음 (1·2차)
2. **클라우드 폴백 명시 동의**: 3차 클라우드 처리 시 사용자 확인 필요
3. **파일 즉시 삭제**: 변환 완료 후 원본 WAV 파일 삭제 옵션
4. **로그 최소화**: 변환 텍스트만 보관, 음성 파일 미보관

## 처리 흐름

```
현장 녹음 (WAV 16kHz Mono)
    ↓
VOSK 로컬 변환
    ↓ (신뢰도 < 85%)
whisper.cpp 재처리
    ↓
텍스트 출력 → 템플릿 적용
    ↓
원본 WAV 삭제 (설정 시)
```

## 관련 컨텍스트

- [[samsung-tablet-voice-setup]]
- [[samsung-tablet-oneclick-install]]
- [[korean-tts-pricing-2026]]
