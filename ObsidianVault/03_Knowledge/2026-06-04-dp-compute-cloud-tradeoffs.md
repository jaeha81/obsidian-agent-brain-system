---
type: knowledge-note
date: 2026-06-04
source: daily-plus
category: knowledge-candidate
tags:
- area/ai_automation
- status/active
summary: 영상/전사 워크플로우 컴퓨트 옵션 비교 — 로컬 vs 클라우드 비용, GPU 렌탈, 배치 처리 전략
status: applied
applied_at: 2026-06-11
graph_cluster: daily-practice
---

# Compute and Cloud Tradeoffs

## 개요

JH 영상 파이프라인(전사, 숏츠 클리핑, AI 처리)을 위한 **컴퓨트 환경 선택 가이드**. 로컬 GPU 대비 클라우드 비용, GPU 렌탈 옵션, 배치 처리 전략을 비교한다.

## 워크로드 분류

| 워크로드 | 연산 강도 | 지연 허용 | 권장 환경 |
|----------|---------|---------|---------|
| whisper 전사 (small) | 낮음 | 수 분 OK | 로컬 CPU |
| whisper 전사 (large) | 중간 | 수 분 OK | 로컬 GPU / 렌탈 |
| 영상 클리핑 (ffmpeg) | 낮음 | 실시간 불필요 | 로컬 CPU |
| AI 하이라이트 감지 | 중간 | 수 분 OK | 로컬 GPU |
| 영상 생성 (Sora 등) | 매우 높음 | 분~시간 OK | 클라우드 전용 |

## 로컬 환경 비용 분석

### JH 현재 장비 추정 (RTX 3080 기준)
```
전기 소모: ~320W (GPU 풀로드)
1시간 전기 비용: 320W × 1h × ₩200/kWh = ₩64
1시간 whisper large 처리: 약 60시간 오디오 분량
→ 오디오 1시간당 전기비: ₩1.07
```

### OpenAI Whisper API 비교
```
OpenAI Whisper API: $0.006/분 = ₩8.4/분
오디오 1시간: ₩504

로컬 절약: ₩504 - ₩1.07 = ₩503/시간 (500배 절감)
```

## GPU 렌탈 옵션 비교

| 서비스 | GPU | 시간당 비용 | 한국 접근성 | 권장 용도 |
|--------|-----|-----------|-----------|---------|
| Vast.ai | RTX 4090 | $0.35~0.60 | 보통 | 배치 처리 |
| RunPod | RTX A6000 | $0.49 | 좋음 | 중간 규모 |
| Lambda Labs | A100 | $1.10 | 좋음 | 대규모 모델 |
| Google Colab Pro | T4/A100 | $9.99/월 정액 | 최고 | 테스트/개발 |
| Ncloud (NCP) | V100 | ₩3,000~8,000/h | 최고 | 국내 서비스 |

## 배치 처리 전략

### 전략 1: 야간 배치 (비용 최적)
```python
import schedule
from datetime import time

def setup_batch_schedule():
    """자정~새벽 5시 배치 실행 (전기요금 낮은 시간대)"""
    schedule.every().day.at("00:00").do(run_nightly_batch)
    
def run_nightly_batch():
    """
    1. 당일 수집된 오디오/영상 전사
    2. AI 하이라이트 분석
    3. 숏츠 클리핑
    4. Vault 업데이트
    """
    audio_queue = get_pending_audio_files()
    for audio in audio_queue:
        transcript = transcribe_batch(audio)
        highlights = analyze_highlights(transcript)
        create_short(highlights)
        log_to_vault(audio, transcript, highlights)
```

### 전략 2: 큐 기반 처리 (확장성)
```python
# Redis 큐 사용
import redis
import json

def enqueue_video(video_path: str, priority: int = 1):
    r = redis.Redis()
    r.lpush("video_queue", json.dumps({
        "path": video_path,
        "priority": priority,
        "enqueued_at": datetime.now().isoformat()
    }))

def process_queue():
    r = redis.Redis()
    while True:
        item = r.brpop("video_queue", timeout=5)
        if item:
            task = json.loads(item[1])
            process_video(task["path"])
```

## 비용 최적화 결정 트리

```
요청 발생
    ↓
실시간 필요? → Yes → 클라우드 API (Whisper API, etc.)
    ↓ No
1시간 이내 처리 OK? → Yes → 로컬 GPU (있다면)
    ↓ No (대규모 배치)
로컬 GPU 있음? → Yes → 야간 배치 스케줄
    ↓ No
월 처리량 계산
    ↓
< 100시간/월 → OpenAI API ($60 이하)
> 100시간/월 → GPU 렌탈 검토 (Vast.ai)
```

## JH 추천 설정

1. **일반 전사 (Discord 음성메시지)**: 로컬 whisper small (실시간)
2. **영상 하이라이트 추출**: 야간 배치 + 로컬 GPU
3. **대규모 영상 처리**: Vast.ai RTX 4090 (배치)
4. **긴급 처리**: OpenAI Whisper API (비용 감수)

## 참고

- whisper.cpp 설치: `2026-06-04-dp-whisper-cpp-transcription-mvp.md`
- 숏츠 파이프라인: `2026-06-04-dp-three-step-shorts-pipeline.md`
- AI 과금 정책: `feedback_no_api_billing.md`

## 관련 노트
- [[hubs/JH System]]
