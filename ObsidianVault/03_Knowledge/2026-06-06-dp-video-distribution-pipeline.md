---
title: 영상→배포 자동화 파이프라인 스케치
date: 2026-06-06
source: daily-plus/2026-06-06.md (Card 7)
priority: P1
category: knowledge
status: distilled
tags:
- video
- distribution
- stt
- editing
- tiktok
- daily-plus
- knowledge
graph_cluster: daily-practice
---

# 영상→배포 자동화 파이프라인 스케치

> ChatGPT Pulse 2026-06-06 Card 7 증류 (P1 · knowledge-candidate)

## 목적

원본 영상을 분석(STT+토픽)→편집(장면 감지+템플릿)→메타데이터(자막/제목) 3개 라인으로 병렬 처리. project.json 제어 파일로 에이전트 협력.

## 3라인 병렬 구조

```
원본 영상 (mp4/mov)
    ↓
┌───────────────────────────────────────────────┐
│                  병렬 처리                     │
│                                               │
│  Line A: 분석         Line B: 편집            │
│  STT 전사             장면 감지               │
│  토픽 추출            클립 분할               │
│  감정 분석            템플릿 적용             │
│                                               │
│                  Line C: 메타데이터           │
│                  자막 SRT 생성               │
│                  제목/설명 생성              │
│                  해시태그 생성               │
└───────────────────────────────────────────────┘
    ↓
project.json (결과 통합 + 에이전트 조율)
    ↓
플랫폼별 인코딩 (TikTok / Reels / YouTube / X)
    ↓
자동 업로드 + 예약
```

## project.json 스키마

```json
{
  "project_id": "VID-2026-001",
  "source_file": "original.mp4",
  "status": "processing",
  "created_at": "2026-06-06T09:00:00Z",

  "analysis": {
    "transcript": "...",
    "topics": ["인테리어", "AI", "견적"],
    "duration_seconds": 180,
    "language": "ko",
    "sentiment": "positive"
  },

  "editing": {
    "scenes": [
      {"start": 0, "end": 15, "type": "hook"},
      {"start": 15, "end": 90, "type": "main"},
      {"start": 90, "end": 180, "type": "cta"}
    ],
    "clips": ["clip_01.mp4", "clip_02.mp4", "clip_03.mp4"],
    "template": "talking_head_v2"
  },

  "metadata": {
    "title": "AI로 인테리어 견적 5분 만에 완성하는 법",
    "description": "...",
    "tags": ["인테리어", "AI견적", "자동화"],
    "thumbnail": "thumb_01.jpg",
    "subtitles_srt": "subtitles_ko.srt"
  },

  "distribution": {
    "platforms": ["youtube", "tiktok", "reels"],
    "schedule": "2026-06-07T18:00:00+09:00",
    "status": {
      "youtube": "pending",
      "tiktok": "pending",
      "reels": "pending"
    }
  }
}
```

## 플랫폼 프리셋

| 플랫폼 | 화면비 | 최대 길이 | 최적 길이 | 해상도 |
|-------|------|---------|---------|------|
| TikTok | 9:16 | 10분 | 15~60초 | 1080×1920 |
| Instagram Reels | 9:16 | 90초 | 15~30초 | 1080×1920 |
| YouTube Shorts | 9:16 | 60초 | 15~60초 | 1080×1920 |
| YouTube | 16:9 | 12시간 | 7~15분 | 1920×1080 |
| X (Twitter) | 16:9 / 1:1 | 2분20초 | 30~60초 | 1280×720 |

```python
PLATFORM_PRESETS = {
    "tiktok": {"ratio": "9:16", "max_sec": 600, "resolution": "1080x1920"},
    "reels": {"ratio": "9:16", "max_sec": 90, "resolution": "1080x1920"},
    "youtube_shorts": {"ratio": "9:16", "max_sec": 60, "resolution": "1080x1920"},
    "youtube": {"ratio": "16:9", "max_sec": None, "resolution": "1920x1080"},
    "x": {"ratio": "16:9", "max_sec": 140, "resolution": "1280x720"},
}
```

## 에이전트 협력 구조

```
Bucky (오케스트레이터)
    ├── Line A Agent: Whisper STT + GPT-4o 토픽 추출
    ├── Line B Agent: FFmpeg 장면 감지 + 템플릿 렌더링
    └── Line C Agent: Claude 메타데이터 생성

모든 에이전트가 project.json을 공유 상태로 사용
완료 시 Discord 알림 발송
```

## 관련 컨텍스트

- [[youtube-automation-package]], [[landing-onboarding-checklist]]
- [[prosutech-youtube-hooks]]
