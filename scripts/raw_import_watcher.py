#!/usr/bin/env python3
"""
RAW Import Watcher — RAW_IMPORT/ 폴더 자동 감시 → 파일 타입 분류 → AgentBus inbox 라우팅

Vision (stpe1.md):
  "모든 데이터/자료/영상/음성을 한 폴더에 넣으면
   Obsidian 에이전트가 자동 정리 → 지식베이스 관리"

Flow:
  RAW_IMPORT/ (새 파일 감지)
    → 파일 타입 분류
        .wav/.mp3/.m4a/.ogg/.flac      → Whisper 전사 → inbox (voice_transcript)
        .mp4/.mov/.avi/.mkv            → ffmpeg 오디오 추출 → Whisper → inbox (video_transcript)
        .url / youtube_urls.txt        → yt-dlp 오디오 추출 → Whisper → inbox (video_transcript)
        .txt/.md (YouTube URL 포함 시) → URL 추출 → yt-dlp 처리
        .txt/.md (일반)                → 직접 inbox 저장 (raw_text)
        .pdf/.docx/.xlsx               → inbox 등록 (document_review)
        .jpg/.jpeg/.png/.webp          → inbox 등록 (image_review)
        .json                          → Discord export 처리 (discord_intake)
    → 원본 01_RAW/{category}/ 로 이동
    → 처리 완료 기록 (.processed_files.json)

Usage:
    python scripts/raw_import_watcher.py
    python scripts/raw_import_watcher.py --once       # 단발 스캔 후 종료
    python scripts/raw_import_watcher.py --interval 30
"""

import argparse
import json
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
import urllib.parse

from dotenv import load_dotenv

ROOT = Path(__file__).parent.parent
load_dotenv(ROOT / ".env", encoding="utf-8-sig", override=True)

import os

VAULT = Path(os.getenv("VAULT_PATH", str(ROOT / "ObsidianVault")))
RAW_IMPORT = ROOT / "RAW_IMPORT"
RAW_VAULT = VAULT / "01_RAW"
INBOX = VAULT / "10_AgentBus" / "inbox"
STATE_FILE = ROOT / ".raw_watcher_state.json"

POLL_INTERVAL = int(os.getenv("RAW_WATCHER_INTERVAL", "10"))

# ── 파일 타입 분류 ─────────────────────────────────────────────────────────────

AUDIO_EXTS = {".wav", ".mp3", ".m4a", ".ogg", ".flac"}
VIDEO_EXTS = {".mp4", ".mov", ".avi", ".mkv", ".webm"}
TEXT_EXTS  = {".txt", ".md"}
DOC_EXTS   = {".pdf", ".docx", ".xlsx", ".pptx", ".hwp"}
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"}
JSON_EXTS  = {".json"}
URL_EXTS   = {".url"}

YOUTUBE_URL_RE = re.compile(
    r"https?://(?:www\.)?(?:youtube\.com/watch\?[^\s]*v=|youtu\.be/)[\w\-]+"
)

CATEGORY_MAP = {
    **{e: "Voice"    for e in AUDIO_EXTS},
    **{e: "Video"    for e in VIDEO_EXTS},
    **{e: "Notes"    for e in TEXT_EXTS},
    **{e: "Docs"     for e in DOC_EXTS},
    **{e: "Images"   for e in IMAGE_EXTS},
    **{e: "Discord"  for e in JSON_EXTS},
    **{e: "YouTube"  for e in URL_EXTS},
}

ALL_SUPPORTED = AUDIO_EXTS | VIDEO_EXTS | TEXT_EXTS | DOC_EXTS | IMAGE_EXTS | JSON_EXTS | URL_EXTS


# ── 상태 관리 ──────────────────────────────────────────────────────────────────

def load_state() -> set:
    if STATE_FILE.exists():
        try:
            data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
            return set(data.get("processed", []))
        except Exception:
            return set()
    return set()


def save_state(processed: set) -> None:
    STATE_FILE.write_text(
        json.dumps({"processed": sorted(processed)}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


# ── 헬퍼 ───────────────────────────────────────────────────────────────────────

def ts() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def write_inbox(filename_prefix: str, msg_type: str, source: Path, body: str, extra_fm: str = "") -> Path:
    INBOX.mkdir(parents=True, exist_ok=True)
    out = INBOX / f"{ts()}_{filename_prefix}_{source.stem}.md"
    content = (
        f"---\n"
        f"type: {msg_type}\n"
        f"source_file: {source.name}\n"
        f"source_category: {CATEGORY_MAP.get(source.suffix.lower(), 'Unknown')}\n"
        f"created: {iso()}\n"
        f"{extra_fm}"
        f"status: pending\n"
        f"---\n\n"
        f"{body}\n"
    )
    out.write_text(content, encoding="utf-8")
    return out


def move_to_raw(source: Path) -> Path:
    category = CATEGORY_MAP.get(source.suffix.lower(), "Misc")
    dest_dir = RAW_VAULT / category
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / source.name
    # 동명 파일 충돌 방지
    if dest.exists():
        dest = dest_dir / f"{source.stem}_{ts()}{source.suffix}"
    shutil.move(str(source), str(dest))
    return dest


# ── 파일 타입별 처리기 ─────────────────────────────────────────────────────────

def handle_audio(path: Path) -> Path:
    """음성 파일 → Whisper 전사 → inbox"""
    try:
        sys.path.insert(0, str(ROOT))
        from scripts.whisper_transcribe import transcribe  # type: ignore
        text = transcribe(path, model_name="base", language="ko")
    except Exception as e:
        print(f"  [Watcher] Whisper 실패 ({e}) — 수동 전사 대기")
        text = None

    if text:
        body = f"## 음성 전사 결과\n\n{text}"
        out = write_inbox("voice", "voice_transcript", path, body,
                          extra_fm="transcription_model: base\n")
        print(f"  [Watcher] 음성 전사 완료 → {out.name}")
    else:
        body = (
            f"## 음성 파일 수신 — 수동 전사 필요\n\n"
            f"원본: `{path.name}`\n\n"
            f"전사 명령: `python scripts/whisper_transcribe.py \"{path}\"`"
        )
        out = write_inbox("voice_pending", "voice_pending_transcription", path, body)
        print(f"  [Watcher] 수동 전사 대기 → {out.name}")
    return out


def handle_video(path: Path) -> Path:
    """영상 파일 → ffmpeg 오디오 추출 → Whisper → inbox"""
    audio_out = RAW_IMPORT / f"_tmp_{path.stem}.mp3"
    extracted = False

    try:
        result = subprocess.run(
            ["ffmpeg", "-i", str(path), "-vn", "-acodec", "mp3", "-y", str(audio_out)],
            capture_output=True, timeout=120,
        )
        if result.returncode == 0 and audio_out.exists():
            extracted = True
            print(f"  [Watcher] ffmpeg 오디오 추출 완료: {audio_out.name}")
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        print(f"  [Watcher] ffmpeg 없음 또는 타임아웃 ({e})")

    if extracted:
        out = handle_audio(audio_out)
        audio_out.unlink(missing_ok=True)
        # inbox 파일의 source_file을 원본 영상으로 업데이트
        txt = out.read_text(encoding="utf-8")
        txt = txt.replace(f"source_file: {audio_out.name}", f"source_file: {path.name}")
        out.write_text(txt, encoding="utf-8")
    else:
        body = (
            f"## 영상 파일 수신 — 수동 처리 필요\n\n"
            f"원본: `{path.name}`\n\n"
            f"ffmpeg 설치 후: `ffmpeg -i \"{path}\" -vn -acodec mp3 audio.mp3`\n"
            f"그 다음: `python scripts/voice_intake.py --file audio.mp3`"
        )
        out = write_inbox("video_pending", "video_pending_processing", path, body)
        print(f"  [Watcher] 영상 수동 처리 대기 → {out.name}")
    return out


def handle_text(path: Path) -> Path:
    """텍스트/마크다운 → YouTube URL 포함 시 yt-dlp 처리, 아니면 inbox 직접 저장"""
    content = path.read_text(encoding="utf-8", errors="ignore")
    urls = _extract_youtube_urls(content)
    if urls:
        print(f"  [Watcher] 텍스트 파일에서 YouTube URL {len(urls)}개 감지")
        results = [handle_youtube_url(u, path) for u in urls]
        return results[0]
    if len(content) > 8000:
        content = content[:8000] + "\n\n[... 이하 생략 — 원본 파일 참조]"
    body = f"## 텍스트 파일 내용\n\n{content}"
    out = write_inbox("text", "raw_text", path, body)
    print(f"  [Watcher] 텍스트 → inbox: {out.name}")
    return out


def handle_document(path: Path) -> Path:
    """문서 파일 → inbox 등록 (검토 요청)"""
    body = (
        f"## 문서 파일 수신\n\n"
        f"파일명: `{path.name}`\n"
        f"크기: {path.stat().st_size // 1024} KB\n"
        f"보관 위치: `01_RAW/Docs/{path.name}`\n\n"
        f"이 문서를 요약하고 관련 지식베이스 항목에 연결해 주세요."
    )
    out = write_inbox("doc", "document_review", path, body)
    print(f"  [Watcher] 문서 → inbox 등록: {out.name}")
    return out


def handle_image(path: Path) -> Path:
    """이미지 파일 → inbox 등록"""
    body = (
        f"## 이미지 파일 수신\n\n"
        f"파일명: `{path.name}`\n"
        f"크기: {path.stat().st_size // 1024} KB\n"
        f"보관 위치: `01_RAW/Images/{path.name}`\n\n"
        f"이 이미지의 내용을 분석하고 관련 프로젝트 또는 위키에 연결해 주세요."
    )
    out = write_inbox("image", "image_review", path, body)
    print(f"  [Watcher] 이미지 → inbox 등록: {out.name}")
    return out


def _extract_youtube_urls(text: str) -> list[str]:
    """텍스트에서 YouTube URL을 모두 추출한다."""
    return YOUTUBE_URL_RE.findall(text)


def handle_youtube_url(url: str, source_path: Path) -> Path:
    """YouTube URL → yt-dlp 오디오 추출 → Whisper 전사 → inbox"""
    video_id = re.search(r"(?:v=|youtu\.be/)([\w\-]+)", url)
    stem = video_id.group(1) if video_id else "youtube"
    audio_out = RAW_IMPORT / f"_tmp_{stem}.mp3"

    extracted = False
    try:
        result = subprocess.run(
            [
                "yt-dlp", "-x", "--audio-format", "mp3",
                "-o", str(audio_out),
                "--no-playlist", url,
            ],
            capture_output=True, timeout=300,
        )
        if result.returncode == 0 and audio_out.exists():
            extracted = True
            print(f"  [Watcher] yt-dlp 다운로드 완료: {audio_out.name}")
        else:
            print(f"  [Watcher] yt-dlp 실패: {result.stderr.decode(errors='ignore')[:200]}")
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        print(f"  [Watcher] yt-dlp 없음 또는 타임아웃 ({e})")

    if extracted:
        out = handle_audio(audio_out)
        audio_out.unlink(missing_ok=True)
        # source_file을 YouTube URL로 교체
        txt = out.read_text(encoding="utf-8")
        txt = txt.replace(f"source_file: {audio_out.name}", f"source_file: {url}")
        out.write_text(txt, encoding="utf-8")
        return out
    else:
        body = (
            f"## YouTube URL 수신 — 수동 처리 필요\n\n"
            f"URL: {url}\n\n"
            f"yt-dlp 설치 후:\n"
            f"`yt-dlp -x --audio-format mp3 -o audio.mp3 \"{url}\"`\n"
            f"그 다음: `python scripts/whisper_transcribe.py audio.mp3`"
        )
        out = write_inbox("youtube_pending", "video_transcript", source_path, body,
                          extra_fm=f"youtube_url: {url}\n")
        print(f"  [Watcher] YouTube 수동 처리 대기 → {out.name}")
        return out


def handle_url_file(path: Path) -> list[Path]:
    """.url 파일 또는 YouTube URL이 포함된 텍스트 파일 처리."""
    content = path.read_text(encoding="utf-8", errors="ignore")
    urls = _extract_youtube_urls(content)

    # .url 파일 형식 (Windows Internet Shortcut) — URL= 라인 파싱
    if path.suffix.lower() == ".url":
        for line in content.splitlines():
            if line.strip().upper().startswith("URL="):
                candidate = line.split("=", 1)[1].strip()
                if YOUTUBE_URL_RE.match(candidate) and candidate not in urls:
                    urls.append(candidate)

    if not urls:
        body = f"## URL 파일 — YouTube URL 없음\n\n원본:\n```\n{content[:500]}\n```"
        return [write_inbox("url_noyoutube", "raw_text", path, body)]

    results = []
    for url in urls:
        print(f"  [Watcher] YouTube URL 감지: {url}")
        results.append(handle_youtube_url(url, path))
    return results


def handle_discord_json(path: Path) -> Path:
    """Discord JSON export → discord_intake 파이프라인"""
    try:
        sys.path.insert(0, str(ROOT))
        from scripts.discord_intake import parse_json_export, write_inbox_message  # type: ignore
        content = parse_json_export(path)
        out = write_inbox_message(path, channel="raw_import", content=content)
        print(f"  [Watcher] Discord JSON → inbox: {out.name}")
        return out
    except Exception as e:
        print(f"  [Watcher] discord_intake 실패 ({e}) — 일반 텍스트로 처리")
        return handle_text(path)


# ── 단일 파일 처리 ─────────────────────────────────────────────────────────────

def process_file(path: Path) -> bool:
    ext = path.suffix.lower()
    print(f"[Watcher] 처리 중: {path.name}  ({ext})")

    try:
        if ext in AUDIO_EXTS:
            handle_audio(path)
        elif ext in VIDEO_EXTS:
            handle_video(path)
        elif ext in URL_EXTS:
            handle_url_file(path)
        elif ext in TEXT_EXTS:
            handle_text(path)
        elif ext in DOC_EXTS:
            handle_document(path)
        elif ext in IMAGE_EXTS:
            handle_image(path)
        elif ext in JSON_EXTS:
            handle_discord_json(path)
        else:
            print(f"  [Watcher] 지원하지 않는 확장자 — 건너뜀: {ext}")
            return False

        # 원본을 01_RAW/{category}/ 로 이동
        dest = move_to_raw(path)
        print(f"  [Watcher] 원본 이동: {dest}")
        return True

    except Exception as e:
        print(f"  [Watcher] ERROR ({path.name}): {e}")
        return False


# ── 메인 루프 ──────────────────────────────────────────────────────────────────

def scan_once(processed: set) -> set:
    new_processed = set()
    if not RAW_IMPORT.exists():
        RAW_IMPORT.mkdir(parents=True, exist_ok=True)
        return new_processed

    for fp in sorted(RAW_IMPORT.iterdir()):
        if not fp.is_file():
            continue
        if fp.name.startswith(".") or fp.name.startswith("_tmp_"):
            continue
        if fp.suffix.lower() not in ALL_SUPPORTED:
            continue
        key = f"{fp.name}:{fp.stat().st_size}"
        if key in processed:
            continue
        success = process_file(fp)
        if success:
            new_processed.add(key)

    return new_processed


def watch(once: bool = False, interval: int = POLL_INTERVAL) -> None:
    processed = load_state()
    print(f"[RAW Watcher] 시작 - 감시 대상: {RAW_IMPORT}")
    print(f"  poll_interval={interval}s  지원 확장자: {len(ALL_SUPPORTED)}종")
    print(f"  기존 처리 기록: {len(processed)}개")

    while True:
        new = scan_once(processed)
        if new:
            processed |= new
            save_state(processed)
            print(f"[RAW Watcher] {len(new)}개 처리 완료 (누적: {len(processed)}개)")

        if once:
            print("[RAW Watcher] --once 모드 종료")
            break

        time.sleep(interval)


# ── 진입점 ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="RAW_IMPORT 폴더 자동 감시 → AgentBus inbox 라우팅")
    parser.add_argument("--once", action="store_true", help="단발 스캔 후 종료")
    parser.add_argument("--interval", type=int, default=POLL_INTERVAL,
                        help=f"폴링 간격(초) (기본: {POLL_INTERVAL})")
    args = parser.parse_args()
    watch(once=args.once, interval=args.interval)
