#!/usr/bin/env python3
"""
Video Inbox Watcher — 폴더를 감시하다가 영상/오디오 파일이 생기면 자동으로 지식 노트로 변환.

감시 폴더: ObsidianVault/00_System/video-inbox/
처리 후:  파일을 processed/ 하위로 이동

Usage:
  python scripts/video_inbox_watcher.py           # 기본 감시 시작
  python scripts/video_inbox_watcher.py --once    # 현재 있는 파일만 처리 후 종료
  python scripts/video_inbox_watcher.py --deep    # deep 모드로 처리 (Claude 지식 추출)
  python scripts/video_inbox_watcher.py --inbox C:/custom/path  # 감시 폴더 지정
"""

import argparse
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent.parent
VAULT = ROOT / "ObsidianVault"
DEFAULT_INBOX = VAULT / "00_System" / "video-inbox"
PROCESSED_DIR_NAME = "processed"

VIDEO_EXTENSIONS = {".mp4", ".mkv", ".avi", ".mov", ".webm", ".m4v",
                    ".mp3", ".wav", ".m4a", ".ogg", ".flac"}


def process_file(video_path: Path, deep: bool = False, lang: str = "ko") -> bool:
    """단일 파일 처리. 성공 시 True 반환."""
    sys.path.insert(0, str(ROOT / "scripts"))
    try:
        from video_to_knowledge import process
        print(f"\n[Watcher] 처리 시작: {video_path.name}", flush=True)
        result = process(str(video_path), language=lang, deep=deep)

        if result["success"]:
            status = "중복 스킵" if result.get("duplicate") else "저장 완료"
            print(f"[Watcher] {status}: {result['filepath']}", flush=True)
            k = result.get("knowledge") or {}
            if k.get("one_line"):
                print(f"[Watcher] 핵심: {k['one_line']}", flush=True)
            return True
        else:
            print(f"[Watcher] 처리 실패: {result.get('error')}", flush=True)
            return False
    except Exception as e:
        print(f"[Watcher] 예외: {e}", flush=True)
        return False


def move_to_processed(video_path: Path) -> Path:
    """처리 완료 파일을 processed/ 하위로 이동."""
    processed_dir = video_path.parent / PROCESSED_DIR_NAME
    processed_dir.mkdir(exist_ok=True)
    dest = processed_dir / video_path.name
    if dest.exists():
        ts = datetime.now().strftime("%H%M%S")
        dest = processed_dir / f"{video_path.stem}_{ts}{video_path.suffix}"
    shutil.move(str(video_path), str(dest))
    print(f"[Watcher] 이동: {video_path.name} → processed/", flush=True)
    return dest


def scan_and_process(inbox: Path, deep: bool, lang: str) -> int:
    """인박스 폴더에서 처리할 파일 스캔 및 처리. 처리된 파일 수 반환."""
    count = 0
    for f in sorted(inbox.iterdir()):
        if f.is_file() and f.suffix.lower() in VIDEO_EXTENSIONS:
            success = process_file(f, deep, lang)
            if success:
                move_to_processed(f)
                count += 1
            else:
                # 실패한 파일은 그대로 두어 재처리 가능하게 함
                err_marker = f.parent / f"{f.stem}.error"
                err_marker.write_text(f"처리 실패: {datetime.now().isoformat()}", encoding="utf-8")
    return count


def watch(inbox: Path, deep: bool, lang: str, poll_secs: int = 10):
    """폴더를 주기적으로 감시. Ctrl+C로 종료."""
    inbox.mkdir(parents=True, exist_ok=True)
    print(f"[Watcher] 감시 시작: {inbox}", flush=True)
    print(f"[Watcher] Deep mode: {deep} | 언어: {lang} | 폴링: {poll_secs}초", flush=True)
    print("[Watcher] Ctrl+C로 종료\n", flush=True)

    seen: set[str] = set()
    while True:
        try:
            for f in sorted(inbox.iterdir()):
                if f.is_file() and f.suffix.lower() in VIDEO_EXTENSIONS and str(f) not in seen:
                    seen.add(str(f))
                    # 파일이 완전히 쓰여질 때까지 잠시 대기
                    time.sleep(1)
                    if f.exists():
                        success = process_file(f, deep, lang)
                        if success:
                            move_to_processed(f)
                        else:
                            err_marker = f.parent / f"{f.stem}.error"
                            err_marker.write_text(
                                f"처리 실패: {datetime.now().isoformat()}", encoding="utf-8"
                            )
            time.sleep(poll_secs)
        except KeyboardInterrupt:
            print("\n[Watcher] 종료", flush=True)
            break
        except Exception as e:
            print(f"[Watcher] 감시 오류: {e}", flush=True)
            time.sleep(poll_secs)


def main():
    parser = argparse.ArgumentParser(description="Video Inbox Watcher")
    parser.add_argument("--inbox", type=Path, default=DEFAULT_INBOX,
                        help=f"감시할 폴더 경로 (기본: {DEFAULT_INBOX})")
    parser.add_argument("--deep", action="store_true",
                        help="Claude deep 분석 모드 (개념/프레임워크/wikilink 자동 생성)")
    parser.add_argument("--lang", default="ko", help="트랜스크립트 언어 (ko/en, 기본: ko)")
    parser.add_argument("--once", action="store_true",
                        help="현재 파일만 처리 후 종료 (감시 안 함)")
    parser.add_argument("--poll", type=int, default=10,
                        help="폴링 간격 초 (기본: 10)")
    args = parser.parse_args()

    inbox = args.inbox
    inbox.mkdir(parents=True, exist_ok=True)

    # README 생성 (처음 실행 시)
    readme = inbox / "README.md"
    if not readme.exists():
        readme.write_text(
            "# Video Inbox\n\n"
            "이 폴더에 영상/오디오 파일을 넣으면 자동으로 Obsidian 지식 노트로 변환됩니다.\n\n"
            "## 지원 형식\n"
            "- 영상: `.mp4` `.mkv` `.avi` `.mov` `.webm`\n"
            "- 오디오: `.mp3` `.wav` `.m4a` `.ogg` `.flac`\n\n"
            "## 처리 후\n"
            "파일은 `processed/` 하위 폴더로 이동됩니다.\n\n"
            "## 실행\n"
            "```\n"
            "python scripts/video_inbox_watcher.py\n"
            "python scripts/video_inbox_watcher.py --deep  # 깊은 분석\n"
            "```\n",
            encoding="utf-8"
        )
        print(f"[Watcher] README 생성: {readme}", flush=True)

    if args.once:
        n = scan_and_process(inbox, args.deep, args.lang)
        print(f"\n[Watcher] 처리 완료: {n}개 파일", flush=True)
    else:
        watch(inbox, args.deep, args.lang, args.poll)


if __name__ == "__main__":
    main()
