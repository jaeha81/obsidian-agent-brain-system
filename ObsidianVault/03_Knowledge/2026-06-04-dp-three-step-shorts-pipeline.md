---
type: knowledge-note
date: 2026-06-04
source: daily-plus
category: command-payload
tags:
  - "#area/ai_automation"
  - "#status/active"
summary: Extract→Clip→Publish 3단계 숏츠 자동화 파이프라인 — Discord 커맨드 트리거, Vault 로깅 포함
status: applied
applied_at: 2026-06-11
---

# Three-Step Shorts Pipeline

## 개요

원본 영상에서 수익화 가능한 숏츠를 자동 생성하는 **Extract → Clip → Publish** 3단계 파이프라인. Bucky/Obsidian 셋업과 Discord 커맨드 트리거로 동작한다.

## 파이프라인 아키텍처

```
원본 영상 (YouTube URL / 로컬 파일)
    ↓
[Step 1] Extract — 하이라이트 구간 감지
    ↓
[Step 2] Clip — 숏츠 규격 클리핑 (9:16, 60초 이하)
    ↓
[Step 3] Publish — 플랫폼별 자동 업로드
    ↓
Vault 로그 기록
```

## Step 1: Extract (하이라이트 감지)

```python
import yt_dlp
from transformers import pipeline

def extract_highlights(video_url: str, top_n: int = 3) -> list:
    """영상에서 상위 N개 하이라이트 구간 추출"""
    
    # 1. 자막/음성 텍스트 추출
    ydl_opts = {
        "writesubtitles": True,
        "writeautomaticsub": True,
        "subtitleslangs": ["ko", "en"],
        "skip_download": True
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(video_url, download=False)
        transcript = extract_transcript(info)
    
    # 2. 감정/관심도 분석
    classifier = pipeline("text-classification", model="snunlp/KR-FinBert-SC")
    segments = split_into_segments(transcript, duration=60)
    
    scores = []
    for seg in segments:
        score = classifier(seg["text"])[0]["score"]
        scores.append({"segment": seg, "score": score})
    
    # 3. 상위 구간 반환
    return sorted(scores, key=lambda x: x["score"], reverse=True)[:top_n]
```

## Step 2: Clip (숏츠 규격 클리핑)

```python
import ffmpeg

def clip_to_shorts(input_path: str, start: float, end: float, 
                    output_path: str) -> str:
    """숏츠 규격으로 클리핑 (9:16 비율, 60초 이하)"""
    
    duration = min(end - start, 60.0)  # 최대 60초
    
    # 9:16 크롭 + 리사이즈
    (
        ffmpeg
        .input(input_path, ss=start, t=duration)
        .filter("crop", "in_h*9/16", "in_h")
        .filter("scale", 1080, 1920)
        .output(output_path, 
                vcodec="libx264",
                acodec="aac",
                crf=23)
        .run(overwrite_output=True)
    )
    
    return output_path
```

## Step 3: Publish (플랫폼 업로드)

```python
def publish_shorts(clip_path: str, metadata: dict, 
                    platforms: list = ["youtube_shorts"]) -> dict:
    """플랫폼별 숏츠 업로드"""
    results = {}
    
    for platform in platforms:
        if platform == "youtube_shorts":
            result = upload_youtube_shorts(clip_path, metadata)
        elif platform == "tiktok":
            result = upload_tiktok(clip_path, metadata)
        
        results[platform] = result
    
    return results
```

## Discord 커맨드 트리거

```
# 기본 실행
/bucky shorts
  --url "https://youtube.com/watch?v=..."
  --count 3
  --publish youtube_shorts

# 로컬 파일
/bucky shorts
  --file "recordings/2026-06-04.mp4"
  --count 5
  --publish tiktok,youtube_shorts
```

## Vault 로깅

```python
def log_to_vault(results: dict, vault_path: str):
    """Obsidian에 숏츠 생성 기록"""
    log_entry = f"""
## Shorts Pipeline — {date.today()}
- 원본: {results['source']}
- 생성 수: {len(results['clips'])}개
- 업로드: {', '.join(results['platforms'])}
- 상태: {results['status']}
    """
    
    log_file = Path(vault_path) / "00_System" / "shorts_log.md"
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(log_entry)
```

## 전체 실행 스크립트

```python
def run_shorts_pipeline(source: str, count: int = 3, 
                          platforms: list = ["youtube_shorts"]) -> dict:
    highlights = extract_highlights(source, top_n=count)
    clips = [clip_to_shorts(source, h["start"], h["end"], 
                             f"output/clip_{i}.mp4")
             for i, h in enumerate(highlights)]
    results = publish_shorts(clips, platforms=platforms)
    log_to_vault(results, VAULT_PATH)
    return results
```

## 참고

- 관련 노트: `2026-05-27-dp-voice-pipeline-ops-standard.md`
- TikTok 분석 워크플로우: `project_session_2026-06-06b.md`
