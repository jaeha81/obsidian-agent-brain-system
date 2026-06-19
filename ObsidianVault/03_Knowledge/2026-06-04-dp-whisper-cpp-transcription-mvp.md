---
type: knowledge-note
date: 2026-06-04
source: daily-plus
category: knowledge-candidate
tags:
- '#area/ai_automation'
- '#status/active'
summary: whisper.cpp 온디바이스 STT 엔진 실용 가이드 — 한국어 지원, Discord 봇 통합, 성능 벤치마크
status: applied
applied_at: 2026-06-11
graph_cluster: daily-practice
---

# whisper.cpp Transcription MVP

## 개요

whisper.cpp는 OpenAI Whisper를 C++로 재구현한 **자체 호스팅 STT 엔진**이다. 클라우드 없이 온디바이스/서버에서 실행 가능하며, Discord 봇 통합과 한국어 지원이 검증된 실용 도구다.

## 모델 사이즈별 사양

| 모델 | 크기 | VRAM | 속도(RTX 3080) | 한국어 정확도 |
|------|------|------|---------------|-------------|
| tiny | 39MB | ~1GB | 32x 실시간 | 낮음 |
| base | 74MB | ~1GB | 16x 실시간 | 보통 |
| small | 244MB | ~2GB | 6x 실시간 | 양호 |
| medium | 769MB | ~5GB | 2x 실시간 | 우수 |
| large-v3 | 1.5GB | ~10GB | 1x 실시간 | 최우수 |

**JH 권장**: `small` (균형) 또는 `medium` (한국어 정밀도)

## 설치 및 기본 사용

```bash
# 빌드
git clone https://github.com/ggerganov/whisper.cpp
cd whisper.cpp
make

# 모델 다운로드
bash ./models/download-ggml-model.sh small

# 기본 변환
./main -m models/ggml-small.bin -l ko -f audio.wav
```

## 한국어 지원 설정

```bash
# 한국어 강제 지정 (자동 감지보다 정확도 높음)
./main -m models/ggml-medium.bin \
  -l ko \
  -f input.wav \
  --output-txt \
  --output-file transcript
```

## Python 바인딩 (Discord 봇 통합)

```python
import whisper_cpp

def transcribe_voice_message(audio_path: str, language: str = "ko") -> str:
    """Discord 음성 메시지 변환"""
    model = whisper_cpp.Whisper("models/ggml-small.bin")
    result = model.transcribe(
        audio_path,
        language=language,
        temperature=0.0,  # 결정론적 출력
        no_speech_threshold=0.6
    )
    return result["text"].strip()

# Discord 봇 핸들러
@bot.event
async def on_message(message):
    if message.attachments:
        for attachment in message.attachments:
            if attachment.content_type and "audio" in attachment.content_type:
                audio_path = await download_attachment(attachment)
                transcript = transcribe_voice_message(audio_path)
                await message.reply(f"변환 결과:\n{transcript}")
```

## JH 시스템 통합 포인트

### 음성 노트 → Vault 파이프라인
```
Discord 음성 메시지
    ↓ whisper.cpp transcribe
텍스트 변환
    ↓ Bucky 파싱
Obsidian 노트 생성 (03_Knowledge/)
```

### Voice → Intent 파이프라인 연동
- 관련 노트: `2026-05-28-dp-voice-to-intent-pipeline.md`
- whisper.cpp 출력을 Intent 파이프라인 입력으로 직접 연결 가능

## 성능 최적화

```python
# 배치 처리 (여러 파일 동시 변환)
import concurrent.futures

def batch_transcribe(audio_files: list, model_path: str) -> list:
    model = whisper_cpp.Whisper(model_path)
    results = []
    for audio in audio_files:
        results.append(model.transcribe(audio, language="ko"))
    return results
```

## 비용 비교

| 방식 | 1시간 오디오 비용 |
|------|----------------|
| OpenAI Whisper API | ~$0.36 |
| whisper.cpp (로컬 GPU) | ~$0.01 전기료 |
| whisper.cpp (CPU only) | ~$0.05 전기료 |

## 다음 단계

- [ ] Discord 봇에 whisper.cpp Python 바인딩 통합
- [ ] `2026-05-27-dp-voice-note-safe-template.md` 파이프라인과 연결
- [ ] 한국어 음성 정확도 테스트 실행
