---
title: "Video → Knowledge 자동화 파이프라인"
date: 2026-06-23
type: system-knowledge
graph_cluster: automation
tags:
  - area/ai_automation
  - topic/knowledge-pipeline
  - topic/video-processing
  - status/active
status: knowledge
---

# Video → Knowledge 자동화 파이프라인

## 개요

YouTube URL 또는 로컬 영상/오디오 파일 → Obsidian 지식 노트 자동 생성 시스템.

## 진입점 3가지

### 1. Claude Code 스킬 (대화형)

```
/jh-video-to-knowledge <url>
/jh-video-to-knowledge https://youtu.be/xxx --deep
```

### 2. CLI 직접 실행

```powershell
# YouTube URL
python -X utf8 scripts/video_to_knowledge.py "https://youtu.be/xxx"
python -X utf8 scripts/video_to_knowledge.py "https://youtu.be/xxx" --deep

# 로컬 영상 파일
python -X utf8 scripts/video_to_knowledge.py video.mp4 --lang ko
python -X utf8 scripts/video_to_knowledge.py recording.mp3 --deep
```

### 3. 폴더 감시 (자동)

`ObsidianVault/00_System/video-inbox/` 폴더에 파일 드롭 → 자동 처리

```powershell
# 백그라운드 감시 시작
python -X utf8 scripts/video_inbox_watcher.py --deep

# 현재 있는 파일만 처리
python -X utf8 scripts/video_inbox_watcher.py --once
```

### 4. Discord 자동 캡처

YouTube URL을 Discord에 공유하면 자동으로 지식 노트 생성 (기존 봇 연동).

## 처리 흐름

```
입력 (URL / 로컬파일)
    ↓
[중복 체크] — video_id 또는 제목 유사도 → 기존 파일 반환
    ↓
[메타데이터 수집]
  YouTube: yt-dlp (제목, 채널, 날짜, 썸네일)
  로컬: 파일 속성
    ↓
[트랜스크립트 추출]
  YouTube: youtube-transcript-api → yt-dlp 자막 폴백
  로컬: ffmpeg 오디오 추출 → whisper.cpp 전사
    ↓
[지식 추출] (Claude Haiku API)
  기본: 3줄 요약
  --deep: 핵심개념 + 프레임워크 + JH 적용포인트 + wikilink 자동생성
    ↓
[Obsidian 노트 저장]
  위치: ObsidianVault/03_Knowledge/YYYY-MM-DD-yt-<slug>.md
```

## --deep 모드 추가 출력

```yaml
key_concepts: ["개념1", "개념2", ...]
frameworks: ["도구1", "프레임워크2"]
jh_apply_points:
  - "Bucky 에이전트에 적용할 수 있는 아이디어"
  - "Obsidian 볼트 구조 개선 방향"
wikilinks: ["bucky-evolution-roadmap", "AgentBus"]
graph_cluster: "youtube-learning"
one_line: "15자 핵심 메시지"
```

## 파일 위치

| 파일 | 역할 |
|------|------|
| `scripts/video_to_knowledge.py` | 핵심 파이프라인 |
| `scripts/video_inbox_watcher.py` | 폴더 감시자 |
| `scripts/bucky_youtube_capture.py` | YouTube 전용 (레거시, 내부 재사용) |
| `scripts/whisper_transcribe.py` | 로컬 오디오 전사 모듈 |
| `ObsidianVault/00_System/video-inbox/` | 자동 처리 인박스 폴더 |

## 의존성

```
yt-dlp                  # YouTube 다운로드 (선택)
youtube-transcript-api  # YouTube 자막 (선택)
openai-whisper          # 로컬 파일 전사 (로컬만 필요)
ffmpeg                  # 로컬 영상 오디오 추출 (로컬만 필요)
ANTHROPIC_API_KEY       # 요약/deep 분석 (없으면 설명 텍스트 사용)
```

## 관련 허브

- [[bucky-evolution-roadmap]] — 지식 진화 로드맵
- [[vibe-coding-pipeline]] — 자동화 파이프라인 패턴
- [[AI_BRAIN_LAYER_STRATEGY]] — 두뇌 레이어 전략
- [[AgentBus]] — 에이전트 버스
