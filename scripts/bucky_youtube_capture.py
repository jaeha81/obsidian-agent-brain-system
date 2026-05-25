#!/usr/bin/env python3
"""
Bucky YouTube 지식 캡처 모듈

YouTube URL → 영상 메타데이터 + 트랜스크립트 + 요약 → Obsidian 저장

사용:
  python bucky_youtube_capture.py "https://youtu.be/xxxxx"
  from bucky_youtube_capture import capture_youtube
"""

import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from urllib.request import urlopen, Request
from urllib.error import URLError

ROOT = Path(__file__).parent.parent
VAULT = ROOT / "ObsidianVault"
KNOWLEDGE_DIR = VAULT / "03_Knowledge"
RAW_DIR = VAULT / "01_RAW"


# ── YouTube ID 추출 ──────────────────────────────────────────────────────────

def extract_video_id(url: str) -> str:
    """YouTube URL에서 video ID 추출."""
    patterns = [
        r"youtu\.be/([a-zA-Z0-9_-]{11})",
        r"youtube\.com/watch\?.*v=([a-zA-Z0-9_-]{11})",
        r"youtube\.com/embed/([a-zA-Z0-9_-]{11})",
        r"youtube\.com/shorts/([a-zA-Z0-9_-]{11})",
    ]
    for pattern in patterns:
        m = re.search(pattern, url)
        if m:
            return m.group(1)
    return ""


# ── YouTube 메타데이터 수집 ──────────────────────────────────────────────────

def fetch_youtube_meta(url: str) -> dict:
    """YouTube 페이지에서 제목·설명·채널·길이 추출."""
    result = {
        "url": url,
        "video_id": extract_video_id(url),
        "title": "",
        "description": "",
        "channel": "",
        "duration": "",
        "thumbnail": "",
        "publish_date": "",
    }

    try:
        req = Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (BuckyBot/1.0)"},
        )
        with urlopen(req, timeout=12) as resp:
            html = resp.read(65536).decode("utf-8", errors="replace")

        # 제목 추출 (og:title)
        m = re.search(r'<meta[^>]+property="og:title"[^>]+content="([^"]+)"', html)
        if m:
            result["title"] = m.group(1)
        if not result["title"]:
            m = re.search(r'"title":"([^"]+)"', html)
            if m:
                result["title"] = m.group(1).replace("\\u0026", "&")

        # 설명 추출
        m = re.search(r'<meta[^>]+name="description"[^>]+content="([^"]+)"', html)
        if m:
            result["description"] = m.group(1)[:500]

        # 채널명
        m = re.search(r'"ownerChannelName":"([^"]+)"', html)
        if m:
            result["channel"] = m.group(1)
        if not result["channel"]:
            m = re.search(r'"author":"([^"]+)"', html)
            if m:
                result["channel"] = m.group(1)

        # 썸네일
        vid = result["video_id"]
        if vid:
            result["thumbnail"] = f"https://img.youtube.com/vi/{vid}/mqdefault.jpg"

        # 게시일
        m = re.search(r'"publishDate":"([^"]+)"', html)
        if m:
            result["publish_date"] = m.group(1)[:10]

    except Exception as e:
        result["_error"] = str(e)

    return result


# ── 트랜스크립트 수집 ────────────────────────────────────────────────────────

def fetch_transcript(video_id: str, lang: str = "ko") -> str:
    """
    youtube-transcript-api 사용 (설치된 경우).
    미설치 시 자막 없음 메시지 반환.
    """
    if not video_id:
        return ""

    # youtube-transcript-api 사용 (pip install youtube-transcript-api)
    try:
        from youtube_transcript_api import YouTubeTranscriptApi  # type: ignore
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)

        # 한국어 우선, 없으면 영어, 없으면 자동
        transcript = None
        for try_lang in [lang, "en", None]:
            try:
                if try_lang:
                    transcript = transcript_list.find_transcript([try_lang])
                else:
                    transcript = transcript_list.find_generated_transcript(["ko", "en"])
                break
            except Exception:
                continue

        if transcript:
            entries = transcript.fetch()
            full_text = " ".join(e["text"] for e in entries)
            return full_text[:6000]  # 최대 6000자

    except ImportError:
        pass
    except Exception as e:
        print(f"[YouTube] 트랜스크립트 수집 실패: {e}", flush=True)

    return ""


# ── Claude API 요약 ──────────────────────────────────────────────────────────

def summarize_with_claude(title: str, transcript: str, description: str) -> str:
    """Claude API로 영상 내용 요약 (선택적)."""
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        return description[:300] if description else ""

    content_text = transcript or description
    if not content_text or len(content_text) < 50:
        return content_text

    prompt = f"""다음 YouTube 영상 내용을 3~5줄로 요약해주세요. 핵심 인사이트와 우리 시스템에 적용할 수 있는 점을 포함해주세요.

영상 제목: {title}
내용:
{content_text[:3000]}

요약 (한국어, 3~5줄):"""

    try:
        import urllib.request as _urllib
        body = json.dumps({
            "model": "claude-haiku-4-5-20251001",
            "max_tokens": 400,
            "messages": [{"role": "user", "content": prompt}],
        }).encode("utf-8")
        req = _urllib.Request(
            "https://api.anthropic.com/v1/messages",
            data=body,
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            method="POST",
        )
        with _urllib.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data["content"][0]["text"].strip()
    except Exception as e:
        print(f"[YouTube] 요약 실패: {e}", flush=True)
        return description[:300] if description else ""


# ── Obsidian 저장 ────────────────────────────────────────────────────────────

def save_to_obsidian(meta: dict, transcript: str, summary: str, tags: list) -> Path:
    """YouTube 영상 → Obsidian 지식 노트 저장."""
    KNOWLEDGE_DIR.mkdir(parents=True, exist_ok=True)

    date_str = datetime.now().strftime("%Y-%m-%d")
    title = meta.get("title", "YouTube Video") or "YouTube Video"
    slug = re.sub(r"[^\w가-힣\s-]", "", title)
    slug = re.sub(r"\s+", "-", slug.strip())[:40].lower() or "video"

    filename = f"{date_str}-yt-{slug}.md"
    filepath = KNOWLEDGE_DIR / filename
    if filepath.exists():
        ts = datetime.now().strftime("%H%M%S")
        filepath = KNOWLEDGE_DIR / f"{date_str}-yt-{slug}-{ts}.md"

    tags_yaml = "\n".join(f"  - {t}" for t in (tags or ["youtube", "video-knowledge"]))
    channel = meta.get("channel", "")
    publish_date = meta.get("publish_date", "")
    thumbnail = meta.get("thumbnail", "")

    # 트랜스크립트 섹션 (있을 경우)
    transcript_section = ""
    if transcript:
        transcript_section = f"""
## 트랜스크립트 (발췌)

> {transcript[:2000]}{'...' if len(transcript) > 2000 else ''}
"""

    note = f"""---
title: "{title}"
source: "{meta.get('url', '')}"
source_type: youtube
channel: "{channel}"
publish_date: "{publish_date}"
date: {date_str}
captured_at: {datetime.now().isoformat(timespec='seconds')}
tags:
{tags_yaml}
status: knowledge
has_transcript: {"true" if transcript else "false"}
---

# {title}

{'![thumbnail](' + thumbnail + ')' if thumbnail else ''}

## 요약

{summary or '요약 없음'}

## 원본 링크

- [YouTube 영상 보기]({meta.get('url', '')})
{'- 채널: **' + channel + '**' if channel else ''}
{transcript_section}

## 우리 시스템 적용 포인트

> 이 노트는 Bucky가 자동 캡처했습니다. 적용 아이디어를 아래에 추가하세요.

- [ ]
"""

    filepath.write_text(note.strip(), encoding="utf-8")
    return filepath


# ── 메인 캡처 함수 ───────────────────────────────────────────────────────────

def capture_youtube(
    url: str,
    tags: list = None,
    lang: str = "ko",
    summarize: bool = True,
) -> dict:
    """
    YouTube URL → Obsidian 저장. Discord 봇에서 호출.

    Returns:
        {
            "success": bool,
            "filepath": str,
            "title": str,
            "summary": str,
            "has_transcript": bool,
            "error": str (실패 시)
        }
    """
    print(f"[YouTube] 캡처 시작: {url}", flush=True)

    video_id = extract_video_id(url)
    if not video_id:
        return {"success": False, "error": "YouTube URL에서 video ID를 추출하지 못했습니다.", "filepath": ""}

    # 1. 메타데이터
    print(f"[YouTube] 메타데이터 수집 중... (video_id: {video_id})", flush=True)
    meta = fetch_youtube_meta(url)
    meta["url"] = url

    # 2. 트랜스크립트
    print(f"[YouTube] 트랜스크립트 수집 중...", flush=True)
    transcript = fetch_transcript(video_id, lang)
    has_transcript = bool(transcript)

    # 3. 요약 (Claude API)
    summary = ""
    if summarize:
        print(f"[YouTube] 요약 생성 중...", flush=True)
        summary = summarize_with_claude(
            meta.get("title", ""),
            transcript,
            meta.get("description", ""),
        )

    # 4. Obsidian 저장
    filepath = save_to_obsidian(meta, transcript, summary, tags or ["youtube", "knowledge", "auto-capture"])
    print(f"[YouTube] 저장 완료: {filepath}", flush=True)

    return {
        "success": True,
        "filepath": str(filepath),
        "title": meta.get("title", ""),
        "summary": summary,
        "has_transcript": has_transcript,
        "video_id": video_id,
        "channel": meta.get("channel", ""),
    }


# ── CLI ─────────────────────────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser(description="YouTube → Obsidian 지식 캡처")
    parser.add_argument("url", help="YouTube URL")
    parser.add_argument("--tags", default="", help="쉼표 구분 태그")
    parser.add_argument("--lang", default="ko", help="트랜스크립트 언어 (ko/en)")
    parser.add_argument("--no-summary", action="store_true", help="요약 생략")
    args = parser.parse_args()

    tags = [t.strip() for t in args.tags.split(",") if t.strip()]
    result = capture_youtube(args.url, tags, args.lang, not args.no_summary)

    if result["success"]:
        print(f"\n✅ 저장 완료: {result['filepath']}")
        print(f"제목: {result['title']}")
        print(f"트랜스크립트: {'있음' if result['has_transcript'] else '없음'}")
        if result["summary"]:
            print(f"\n요약:\n{result['summary']}")
    else:
        print(f"\n❌ 실패: {result['error']}")
        sys.exit(1)


if __name__ == "__main__":
    main()
