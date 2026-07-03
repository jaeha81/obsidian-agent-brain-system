#!/usr/bin/env python3
"""
Video → Knowledge Pipeline
YouTube URL 또는 로컬 영상/오디오 파일 → Obsidian 지식 노트

Usage:
  python scripts/video_to_knowledge.py "https://youtu.be/xxxxx"
  python scripts/video_to_knowledge.py video.mp4
  python scripts/video_to_knowledge.py video.mp4 --lang en --deep

Deep mode(--deep): 트랜스크립트 전체 분석 → 핵심 개념/프레임워크/wikilink 자동 생성
"""

import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / ".env")
except ImportError:
    pass

ROOT = Path(__file__).parent.parent
VAULT = ROOT / "ObsidianVault"
KNOWLEDGE_DIR = VAULT / "03_Knowledge"
RAW_DIR = VAULT / "01_RAW"

YOUTUBE_PATTERNS = [
    r"youtu\.be/([a-zA-Z0-9_-]{11})",
    r"youtube\.com/watch\?.*v=([a-zA-Z0-9_-]{11})",
    r"youtube\.com/embed/([a-zA-Z0-9_-]{11})",
    r"youtube\.com/shorts/([a-zA-Z0-9_-]{11})",
]


# ── 입력 감지 ────────────────────────────────────────────────────────────────

def is_youtube_url(input_str: str) -> bool:
    return any(re.search(p, input_str) for p in YOUTUBE_PATTERNS)


def is_local_video(input_str: str) -> bool:
    p = Path(input_str)
    return p.exists() and p.suffix.lower() in {".mp4", ".mkv", ".avi", ".mov", ".webm", ".m4v",
                                                 ".mp3", ".wav", ".m4a", ".ogg", ".flac"}


# ── 로컬 영상 처리 ───────────────────────────────────────────────────────────

def extract_audio_from_video(video_path: Path, output_dir: Path) -> Path | None:
    """ffmpeg로 비디오에서 오디오 추출."""
    audio_path = output_dir / "audio.wav"
    try:
        result = subprocess.run(
            ["ffmpeg", "-y", "-i", str(video_path), "-vn", "-ac", "1", "-ar", "16000",
             "-acodec", "pcm_s16le", str(audio_path)],
            capture_output=True, text=True, timeout=300
        )
        if result.returncode == 0 and audio_path.exists():
            print(f"[Video] 오디오 추출 완료: {audio_path}", flush=True)
            return audio_path
        print(f"[Video] ffmpeg 오류: {result.stderr[-200:]}", flush=True)
    except FileNotFoundError:
        print("[Video] ffmpeg 미설치 — brew install ffmpeg 또는 PATH 확인", flush=True)
    except Exception as e:
        print(f"[Video] 오디오 추출 실패: {e}", flush=True)
    return None


def transcribe_audio(audio_path: Path, language: str = "ko") -> str:
    """openai-whisper로 오디오 전사."""
    try:
        import whisper
        print(f"[Whisper] 전사 시작 (model=base, lang={language})...", flush=True)
        model = whisper.load_model("base")
        opts = {}
        if language:
            opts["language"] = language
        result = model.transcribe(str(audio_path), **opts)
        text = result.get("text", "").strip()
        print(f"[Whisper] 전사 완료: {len(text)}자", flush=True)
        return text[:8000]
    except ImportError:
        print("[Whisper] openai-whisper 미설치 — pip install openai-whisper", flush=True)
    except Exception as e:
        print(f"[Whisper] 전사 실패: {e}", flush=True)
    return ""


def process_local_video(video_path: Path, language: str = "ko") -> dict:
    """로컬 영상 파일 → 메타데이터 + 트랜스크립트."""
    meta = {
        "title": video_path.stem,
        "source": str(video_path),
        "source_type": "local_video",
        "channel": "",
        "publish_date": datetime.fromtimestamp(video_path.stat().st_mtime).strftime("%Y-%m-%d"),
        "thumbnail": "",
        "video_id": "",
        "url": str(video_path),
    }

    transcript = ""
    suffix = video_path.suffix.lower()

    # 오디오 파일이면 직접 전사, 영상이면 오디오 추출 후 전사
    if suffix in {".mp3", ".wav", ".m4a", ".ogg", ".flac"}:
        transcript = transcribe_audio(video_path, language)
    else:
        with tempfile.TemporaryDirectory() as tmpdir:
            audio_path = extract_audio_from_video(video_path, Path(tmpdir))
            if audio_path:
                transcript = transcribe_audio(audio_path, language)

    return meta, transcript


# ── YouTube 처리 (bucky_youtube_capture 재사용) ───────────────────────────────

def _whisper_fallback_youtube(video_id: str, language: str = "ko") -> str:
    """yt-dlp로 오디오 다운로드 후 Whisper STT — 자막 없는 영상 폴백."""
    try:
        import yt_dlp
        import whisper as _whisper
    except ImportError as e:
        print(f"[Whisper/yt-dlp] 미설치: {e}", flush=True)
        return ""
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            ydl_opts = {
                "quiet": True,
                "no_warnings": True,
                "format": "bestaudio/best",
                "outtmpl": str(Path(tmpdir) / "audio.%(ext)s"),
                "postprocessors": [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "wav",
                    "preferredquality": "128",
                }],
            }
            url = f"https://www.youtube.com/watch?v={video_id}"
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

            audio_files = list(Path(tmpdir).glob("audio.*"))
            if not audio_files:
                print("[Whisper] 오디오 다운로드 실패", flush=True)
                return ""

            audio_path = audio_files[0]
            print(f"[Whisper] STT 시작 (model=base, lang={language}, file={audio_path.name})...", flush=True)
            model = _whisper.load_model("base")
            opts = {"language": language} if language else {}
            result = model.transcribe(str(audio_path), **opts)
            text = result.get("text", "").strip()
            print(f"[Whisper] STT 완료: {len(text)}자", flush=True)
            return text[:8000]
    except Exception as e:
        print(f"[Whisper] STT 폴백 실패: {e}", flush=True)
        return ""


def process_youtube(url: str, language: str = "ko") -> tuple[dict, str]:
    """YouTube URL → 메타데이터 + 트랜스크립트.

    자막 우선순위:
    1. youtube-transcript-api (한국어 → 영어 → 자동생성)
    2. yt-dlp VTT/SRT 자막 파일
    3. Whisper STT 폴백 (자막 없는 영상)
    """
    sys.path.insert(0, str(ROOT / "scripts"))
    meta = {"url": url, "title": "", "source_type": "youtube", "channel": "",
            "publish_date": "", "thumbnail": "", "video_id": ""}
    try:
        from bucky_youtube_capture import fetch_youtube_meta, fetch_transcript, extract_video_id
        video_id = extract_video_id(url)
        meta = fetch_youtube_meta(url)
        meta["url"] = url
        meta["source_type"] = "youtube"
        print(f"[YouTube] 메타: {meta.get('title', '?')}", flush=True)
        transcript = fetch_transcript(video_id, language)

        # 자막 없으면 Whisper STT 폴백
        if not transcript:
            print(f"[YouTube] 자막 없음 → Whisper STT 폴백", flush=True)
            transcript = _whisper_fallback_youtube(video_id, language)

        return meta, transcript
    except Exception as e:
        print(f"[YouTube] 처리 실패: {e}", flush=True)
        return meta, ""


# ── Bucky CLI(구독) 기반 지식 추출 ──────────────────────────────────────────

EXISTING_NODES = [
    "bucky-evolution-roadmap", "vibe-coding-pipeline", "AgentBus", "Graphify",
    "claude-code-web-delivery-pattern", "AI_BRAIN_LAYER_STRATEGY", "typeless-voice-stt-analysis",
    "github-catalog", "knowledge-distiller", "bucky-evolution-nlp-layer",
    "vault-galaxy-graph-bridge", "bucky-evolution-pipeline",
]


def _run_bucky_safe(prompt: str, timeout: int = 120) -> str:
    """Claude CLI 구독 경로로 프롬프트 실행. 실패 시 빈 문자열 반환."""
    try:
        sys.path.insert(0, str(ROOT / "scripts"))
        from bucky_client import run_bucky
        return run_bucky(prompt, timeout=timeout, task_type="summarize")
    except Exception as e:
        print(f"[Bucky] CLI 호출 실패: {e}", flush=True)
        return ""


_KNOWLEDGE_PROMPT_TEMPLATE = """\
당신은 JH의 지식 큐레이터 에이전트입니다.
다음 영상 내용을 분석하여 Obsidian 지식 노트로 구조화하세요.

영상 제목: {title}
채널: {channel}
내용 (트랜스크립트/설명):
{content}

JH 시스템 맥락:
- Bucky: AI 오케스트레이터 에이전트
- Obsidian Vault: 두뇌 지식 저장소
- AgentBus: 에이전트 통신 버스
- vibe-coding: AI 가속 개발 방법론
- 목표: 1인 창업자 레버리지 극대화

기존 지식 노트 (wikilink 후보): {existing_nodes}

아래 JSON 형식으로만 응답하세요 (코드블록 없이 순수 JSON, 반드시 한국어):
{{
  "summary": "3~5줄 핵심 요약",
  "key_concepts": ["개념1", "개념2"],
  "frameworks": ["도구1"],
  "jh_apply_points": ["적용 아이디어1", "적용 아이디어2"],
  "graph_cluster": "youtube-learning",
  "wikilinks": ["노트명1"],
  "tags": ["area/ai", "topic/llm"],
  "one_line": "15자 이내 핵심"
}}"""


def _extract_json(raw: str) -> dict | None:
    """응답에서 JSON 객체 추출."""
    try:
        m = re.search(r'\{[\s\S]+\}', raw)
        if m:
            return json.loads(m.group())
    except Exception:
        pass
    return None


def _call_claude_api(prompt: str, timeout: int = 120) -> str:
    """Anthropic API 직접 호출 — Bucky CLI 폴백."""
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        return ""
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1500,
            messages=[{"role": "user", "content": prompt}],
        )
        return msg.content[0].text if msg.content else ""
    except Exception as e:
        print(f"[Claude API] 직접 호출 실패: {e}", flush=True)
        return ""


def extract_knowledge_deep(title: str, transcript: str, description: str,
                            meta: dict, api_key: str = "") -> dict:
    """구조화된 지식 추출. Bucky CLI 우선, 실패 시 Claude API 직접 호출."""
    content = transcript or description or title
    prompt = _KNOWLEDGE_PROMPT_TEMPLATE.format(
        title=title,
        channel=meta.get("channel", ""),
        content=content[:5000],
        existing_nodes=", ".join(EXISTING_NODES),
    )

    # 1차: Bucky CLI (구독 경로)
    raw = _run_bucky_safe(prompt, timeout=180)
    if raw:
        parsed = _extract_json(raw)
        if parsed:
            return parsed
        print(f"[Bucky] JSON 파싱 실패, Claude API 폴백", flush=True)

    # 2차: Claude API 직접 호출
    raw = _call_claude_api(prompt, timeout=120)
    if raw:
        parsed = _extract_json(raw)
        if parsed:
            print(f"[Claude API] 지식 추출 성공", flush=True)
            return parsed

    return {
        "summary": description[:300] if description else "요약 없음",
        "key_concepts": [],
        "frameworks": [],
        "jh_apply_points": [],
        "graph_cluster": "youtube-learning",
        "wikilinks": [],
        "tags": ["youtube", "video-knowledge"],
        "one_line": title[:15]
    }


def simple_summary(title: str, content: str, api_key: str = "") -> str:
    """3줄 요약. Bucky CLI 우선, 실패 시 Claude API 직접 호출, 최후 content 앞부분."""
    if not content:
        return ""
    prompt = (
        f"다음 YouTube 영상 내용을 3줄로 요약하세요 (한국어):\n"
        f"제목: {title}\n내용: {content[:2000]}"
    )
    result = _run_bucky_safe(prompt, timeout=60)
    if result:
        return result
    result = _call_claude_api(prompt, timeout=60)
    return result if result else content[:300]


# ── 중복 체크 ────────────────────────────────────────────────────────────────

def check_duplicate(video_id: str, title: str) -> Path | None:
    """video_id 또는 유사 제목으로 기존 노트 검색."""
    KNOWLEDGE_DIR.mkdir(parents=True, exist_ok=True)

    if video_id:
        for existing in KNOWLEDGE_DIR.glob("*-yt-*.md"):
            try:
                header = existing.read_text(encoding="utf-8", errors="ignore")[:800]
                if (f"/{video_id}" in header or f"v={video_id}" in header
                        or f'"{video_id}"' in header or f"video_id: {video_id}" in header):
                    return existing
            except Exception:
                continue

    # 제목 유사도 체크 (슬러그 비교)
    if title:
        slug = re.sub(r"[^\w가-힣]", "", title.lower())[:20]
        for existing in KNOWLEDGE_DIR.glob("*.md"):
            if slug and slug in existing.stem.replace("-", "").replace("_", ""):
                return existing

    return None


# ── 노트 생성 ────────────────────────────────────────────────────────────────

def build_note(meta: dict, transcript: str, knowledge: dict, deep: bool) -> str:
    """Obsidian 지식 노트 생성."""
    date_str = datetime.now().strftime("%Y-%m-%d")
    title = meta.get("title", "Video") or "Video"
    source_type = meta.get("source_type", "video")
    tags = knowledge.get("tags", ["video-knowledge"])
    tags_yaml = "\n".join(f"  - {t}" for t in tags)
    graph_cluster = knowledge.get("graph_cluster", "youtube-learning")

    thumbnail = meta.get("thumbnail", "")
    thumb_md = f"![thumbnail]({thumbnail})" if thumbnail else ""

    # wikilinks 섹션
    wikilinks = knowledge.get("wikilinks", [])
    wikilink_section = ""
    if wikilinks:
        wikilink_section = "\n## 관련 허브\n\n" + "\n".join(f"- [[{w}]]" for w in wikilinks)

    # 핵심 개념 섹션
    key_concepts = knowledge.get("key_concepts", [])
    concepts_md = ""
    if key_concepts and deep:
        concepts_md = "\n## 핵심 개념\n\n" + "\n".join(f"- {c}" for c in key_concepts)

    # 프레임워크 섹션
    frameworks = knowledge.get("frameworks", [])
    frameworks_md = ""
    if frameworks and deep:
        frameworks_md = "\n## 언급된 도구/프레임워크\n\n" + "\n".join(f"- `{f}`" for f in frameworks)

    # 적용 포인트
    apply_points = knowledge.get("jh_apply_points", [])
    apply_md = "\n".join(f"- [ ] {p}" for p in apply_points) if apply_points else "- [ ] "

    # 트랜스크립트 발췌 (deep 모드에서만)
    transcript_md = ""
    if transcript and deep:
        transcript_md = f"""
## 트랜스크립트 발췌

> {transcript[:3000]}{'...' if len(transcript) > 3000 else ''}
"""

    frontmatter = f"""---
title: "{title}"
source: "{meta.get('url', '')}"
source_type: {source_type}
video_id: {meta.get('video_id', '')}
channel: "{meta.get('channel', '')}"
publish_date: "{meta.get('publish_date', '')}"
date: {date_str}
captured_at: {datetime.now().isoformat(timespec='seconds')}
one_line: "{knowledge.get('one_line', '')}"
tags:
{tags_yaml}
status: knowledge
has_transcript: {"true" if transcript else "false"}
graph_cluster: {graph_cluster}
deep_analyzed: {"true" if deep else "false"}
---"""

    body = f"""
# {title}

{thumb_md}

## 요약

{knowledge.get('summary', '요약 없음')}
{concepts_md}
{frameworks_md}

## 우리 시스템 적용 포인트

{apply_md}
{transcript_md}
## 원본 링크

- [{title}]({meta.get('url', '')})
{"- 채널: **" + meta.get('channel', '') + "**" if meta.get('channel') else ""}
{wikilink_section}
"""

    return (frontmatter + body).strip()


# ── 메인 파이프라인 ──────────────────────────────────────────────────────────

def process(input_str: str, language: str = "ko", deep: bool = False,
            tags: list = None) -> dict:
    """
    영상 → 지식 노트 전체 파이프라인.

    Returns:
        {"success": bool, "filepath": str, "title": str, "duplicate": bool, "error": str}
    """
    print(f"[V2K] 입력 분석: {input_str[:80]}", flush=True)

    # 1. 입력 타입 감지 및 처리
    if is_youtube_url(input_str):
        meta, transcript = process_youtube(input_str, language)
    elif is_local_video(input_str):
        meta, transcript = process_local_video(Path(input_str), language)
    else:
        return {"success": False, "error": f"지원하지 않는 입력: {input_str}",
                "filepath": "", "title": ""}

    title = meta.get("title") or Path(input_str).stem
    video_id = meta.get("video_id", "")

    # 2. 중복 체크
    dup = check_duplicate(video_id, title)
    if dup:
        print(f"[V2K] 중복 감지 → {dup.name}", flush=True)
        return {"success": True, "filepath": str(dup), "title": title,
                "duplicate": True, "has_transcript": bool(transcript)}

    # 3. 지식 추출 (Bucky CLI 구독 경로)
    print(f"[V2K] 지식 추출 중... (deep={deep})", flush=True)
    if deep:
        knowledge = extract_knowledge_deep(title, transcript, meta.get("description", ""), meta)
    else:
        summary = simple_summary(title, transcript or meta.get("description", ""))
        # one_line: 제목에서 의미있는 15자 핵심 추출 (전치사/조사 제거)
        one_line = re.sub(r"[\-_\[\]()（）]", " ", title).strip()
        one_line = re.sub(r"\s+", " ", one_line)[:30]
        knowledge = {
            "summary": summary,
            "key_concepts": [],
            "frameworks": [],
            "jh_apply_points": [],
            "graph_cluster": "youtube-learning",
            "wikilinks": [],
            "tags": (tags or []) + ["youtube", "knowledge", "auto-capture"],
            "one_line": one_line
        }

    if tags:
        knowledge["tags"] = list(set(knowledge.get("tags", []) + tags))

    # 4. 노트 생성
    note_content = build_note(meta, transcript, knowledge, deep)

    # 5. 저장
    KNOWLEDGE_DIR.mkdir(parents=True, exist_ok=True)
    slug = re.sub(r"[^\w가-힣\s-]", "", title)
    slug = re.sub(r"\s+", "-", slug.strip())[:40].lower() or "video"
    prefix = "yt" if meta.get("source_type") == "youtube" else "vid"
    date_str = datetime.now().strftime("%Y-%m-%d")
    filename = f"{date_str}-{prefix}-{slug}.md"
    filepath = KNOWLEDGE_DIR / filename

    if filepath.exists():
        vid_suf = video_id[:7] if video_id else "dup"
        filepath = KNOWLEDGE_DIR / f"{date_str}-{prefix}-{slug}-{vid_suf}.md"

    filepath.write_text(note_content, encoding="utf-8")
    print(f"[V2K] 저장 완료: {filepath}", flush=True)

    return {
        "success": True,
        "filepath": str(filepath),
        "title": title,
        "duplicate": False,
        "has_transcript": bool(transcript),
        "knowledge": knowledge,
        "deep": deep,
    }


# ── CLI ──────────────────────────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Video → Knowledge Pipeline")
    parser.add_argument("input", help="YouTube URL 또는 로컬 영상/오디오 파일 경로")
    parser.add_argument("--lang", default="ko", help="트랜스크립트 언어 (ko/en, 기본: ko)")
    parser.add_argument("--deep", action="store_true",
                        help="깊은 지식 추출 모드 (개념/프레임워크/wikilink 자동 생성)")
    parser.add_argument("--tags", default="", help="추가 태그 (쉼표 구분)")
    args = parser.parse_args()

    tags = [t.strip() for t in args.tags.split(",") if t.strip()]
    result = process(args.input, args.lang, args.deep, tags)

    if result["success"]:
        dup_str = " [중복 스킵]" if result.get("duplicate") else ""
        print(f"\n{'=' * 50}")
        print(f"{'중복' if result.get('duplicate') else '저장'} 완료{dup_str}: {result['filepath']}")
        print(f"제목: {result['title']}")
        print(f"트랜스크립트: {'있음' if result.get('has_transcript') else '없음'}")
        if result.get("knowledge") and not result.get("duplicate"):
            k = result["knowledge"]
            print(f"한 줄 핵심: {k.get('one_line', '')}")
            if k.get("key_concepts"):
                print(f"핵심 개념: {', '.join(k['key_concepts'][:5])}")
            if k.get("jh_apply_points"):
                print(f"\nJH 적용 포인트:")
                for p in k["jh_apply_points"][:3]:
                    print(f"  - {p}")
    else:
        print(f"\n실패: {result['error']}")
        sys.exit(1)


if __name__ == "__main__":
    main()
