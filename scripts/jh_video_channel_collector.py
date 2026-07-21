#!/usr/bin/env python3
"""
JH-VIDEO Channel Collector — 디스코드 JH-VIDEO 채널을 폴링해 새 유튜브 영상을 큐에 적재.

봇과 독립된 읽기 전용 프로세스(stdlib만 사용). LLM 호출 없음 → 비용 0.
큐에 쌓인 영상은 정제 세션(Claude Code) 또는 video_to_knowledge.py가 소비한다.

상태:  data/memory/jh_video_collector_state.json  (마지막 처리 message_id)
큐:    data/memory/jh_video_queue.jsonl           (미정제 영상 1줄 1건)
정제 중복 방지: 03_Knowledge/*-yt-*.md 의 video_id 스캔

Usage:
  python scripts/jh_video_channel_collector.py            # 1회 폴링
  python scripts/jh_video_channel_collector.py --watch    # 주기 폴링 (기본 300초)
  python scripts/jh_video_channel_collector.py --poll 600 --watch
"""
import argparse
import json
import re
import sys
import time
import urllib.request
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent.parent
VAULT = ROOT / "ObsidianVault"
KNOWLEDGE_DIR = VAULT / "03_Knowledge"
STATE_FILE = ROOT / "data" / "memory" / "jh_video_collector_state.json"
QUEUE_FILE = ROOT / "data" / "memory" / "jh_video_queue.jsonl"

YT_RE = re.compile(
    r"(?:youtu\.be/|youtube\.com/watch\?[^ ]*v=|youtube\.com/shorts/|youtube\.com/embed/)"
    r"([a-zA-Z0-9_-]{11})"
)


def load_env() -> dict:
    """.env 를 utf-8-sig(BOM 제거)로 읽는다. 값은 반환만 하고 출력하지 않는다."""
    env = {}
    envfile = ROOT / ".env"
    if not envfile.exists():
        return env
    for line in envfile.read_text(encoding="utf-8-sig", errors="ignore").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            env[k.strip()] = v.strip()
    return env


def discord_get(path: str, token: str) -> list | dict:
    req = urllib.request.Request(
        f"https://discord.com/api/v10{path}",
        headers={"Authorization": f"Bot {token}", "User-Agent": "jh-video-collector/1.0"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def fetch_new_messages(channel: str, token: str, after_id: str | None) -> list:
    """after_id 이후 메시지를 오래된 순으로 모아 반환. after 미지정 시 최근 100개."""
    collected = []
    if after_id:
        # after 페이지네이션: 반환은 최신순 → 다 모은 뒤 오래된 순 정렬
        cursor = after_id
        for _ in range(30):
            batch = discord_get(
                f"/channels/{channel}/messages?limit=100&after={cursor}", token
            )
            if not batch:
                break
            collected.extend(batch)
            cursor = batch[0]["id"]  # 최신순 반환 → 첫 원소가 가장 최신
            if len(batch) < 100:
                break
            time.sleep(0.4)
    else:
        collected = discord_get(f"/channels/{channel}/messages?limit=100", token)
    collected.sort(key=lambda m: int(m["id"]))  # 오래된 순
    return collected


def extract_video_ids(msg: dict) -> list[str]:
    ids = list(YT_RE.findall(msg.get("content", "")))
    for e in msg.get("embeds", []):
        if e.get("url"):
            ids += YT_RE.findall(e["url"])
    return ids


def oembed_meta(video_id: str) -> dict:
    """oEmbed로 제목·채널만 조회 (API 키·yt-dlp 불필요)."""
    try:
        url = (
            "https://www.youtube.com/oembed?url="
            f"https://www.youtube.com/watch?v={video_id}&format=json"
        )
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as r:
            d = json.loads(r.read().decode("utf-8"))
        return {"title": d.get("title", ""), "channel": d.get("author_name", "")}
    except Exception:
        return {"title": "", "channel": ""}


def distilled_video_ids() -> set[str]:
    """이미 지식노트로 정제된 video_id 집합."""
    ids = set()
    if not KNOWLEDGE_DIR.exists():
        return ids
    for note in KNOWLEDGE_DIR.glob("*-yt-*.md"):
        try:
            head = note.read_text(encoding="utf-8", errors="ignore")[:800]
            m = re.search(r"video_id:\s*([a-zA-Z0-9_-]{11})", head)
            if m:
                ids.add(m.group(1))
        except Exception:
            continue
    return ids


def queued_video_ids() -> set[str]:
    ids = set()
    if QUEUE_FILE.exists():
        for line in QUEUE_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                ids.add(json.loads(line)["video_id"])
            except Exception:
                continue
    return ids


def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"last_message_id": None}


def save_state(state: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def append_queue(entries: list[dict]) -> None:
    QUEUE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with QUEUE_FILE.open("a", encoding="utf-8") as f:
        for e in entries:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")


def poll_once(channel: str, token: str, dry_run: bool = False) -> int:
    state = load_state()
    messages = fetch_new_messages(channel, token, state.get("last_message_id"))
    if not messages:
        print("[Collector] 새 메시지 없음", flush=True)
        return 0

    already = distilled_video_ids() | queued_video_ids()
    new_entries = []
    seen_this_run = set()
    for m in messages:
        for vid in extract_video_ids(m):
            if vid in already or vid in seen_this_run:
                continue
            seen_this_run.add(vid)
            meta = oembed_meta(vid)
            new_entries.append({
                "video_id": vid,
                "url": f"https://youtu.be/{vid}",
                "title": meta["title"],
                "channel": meta["channel"],
                "message_id": m["id"],
                "message_ts": m.get("timestamp", "")[:19],
                "discovered_at": datetime.now().isoformat(timespec="seconds"),
                "status": "pending",
            })

    if dry_run:
        print(f"[Collector][DRY-RUN] {len(messages)}메시지 | 신규 영상 {len(new_entries)}건 (큐·상태 미기록)", flush=True)
        for e in new_entries:
            print(f"[Collector][DRY-RUN] + {e['video_id']} | {e['title'][:50]}", flush=True)
        return len(new_entries)

    if new_entries:
        append_queue(new_entries)
        for e in new_entries:
            print(f"[Collector] + {e['video_id']} | {e['title'][:50]}", flush=True)

    state["last_message_id"] = messages[-1]["id"]
    save_state(state)
    print(f"[Collector] 처리 {len(messages)}메시지 | 신규 영상 {len(new_entries)}건 큐 적재", flush=True)
    return len(new_entries)


def main():
    parser = argparse.ArgumentParser(description="JH-VIDEO Channel Collector")
    parser.add_argument("--watch", action="store_true", help="주기 폴링 (기본 1회)")
    parser.add_argument("--poll", type=int, default=300, help="폴링 간격 초 (기본 300)")
    parser.add_argument("--dry-run", action="store_true", help="큐·상태 미기록 (collection_scheduler 계약)")
    args = parser.parse_args()

    env = load_env()
    token = env.get("DISCORD_BOT_TOKEN", "")
    channel = env.get("JH_VIDEO_CHANNEL_ID", "").strip()
    if not token or not channel:
        print("[Collector] DISCORD_BOT_TOKEN 또는 JH_VIDEO_CHANNEL_ID 없음 (.env 확인)", flush=True)
        sys.exit(1)

    if not args.watch:
        poll_once(channel, token, dry_run=args.dry_run)
        return

    print(f"[Collector] 감시 시작 | 채널 {channel} | 폴링 {args.poll}초 | Ctrl+C 종료", flush=True)
    while True:
        try:
            poll_once(channel, token, dry_run=args.dry_run)
            time.sleep(args.poll)
        except KeyboardInterrupt:
            print("\n[Collector] 종료", flush=True)
            break
        except Exception as e:
            print(f"[Collector] 폴링 오류: {e}", flush=True)
            time.sleep(args.poll)


if __name__ == "__main__":
    main()
