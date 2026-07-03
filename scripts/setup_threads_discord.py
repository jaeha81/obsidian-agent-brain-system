#!/usr/bin/env python3
"""
setup_threads_discord.py — #jh-쓰레드자동화 Discord 채널 + Webhook 자동 생성
기존 Bucky 봇 토큰(DISCORD_BOT_TOKEN)을 재사용하여 채널과 웹훅을 만든다.

실행:
  python -X utf8 scripts/setup_threads_discord.py

완료 후:
  - Bucky .env 에 JH_THREADS_CHANNEL_ID, THREADS_DISCORD_WEBHOOK 자동 추가
  - threads-monetization .env 에 DISCORD_THREADS_CHANNEL_ID 자동 추가
"""
import json
import os
import re
import sys
import urllib.request
import urllib.error
from pathlib import Path

ROOT = Path(__file__).parent.parent
ENV_FILE = ROOT / ".env"
THREADS_ENV_FILE = Path(r"D:\ai프로젝트\threads-monetization\.env")

CHANNEL_NAME  = "jh-쓰레드자동화"
CHANNEL_TOPIC = "🤖 쓰레드 수익화 자동화 — Bucky 에이전트 귀속 채널"
WEBHOOK_NAME  = "ThreadsAgent"


def _load_env(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        k = k.strip()
        v = v.strip().strip('"').strip("'")
        if k and k not in os.environ:
            os.environ[k] = v


_load_env(ENV_FILE)

BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN", "")
GUILD_ID  = os.getenv("DISCORD_GUILD_ID", "")

if not BOT_TOKEN or not GUILD_ID:
    print("[ERROR] DISCORD_BOT_TOKEN 또는 DISCORD_GUILD_ID가 .env에 없습니다.")
    sys.exit(1)


def discord_api(method: str, path: str, body: dict | None = None):
    url = f"https://discord.com/api/v10{path}"
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(
        url, data=data, method=method,
        headers={
            "Authorization": f"Bot {BOT_TOKEN}",
            "Content-Type": "application/json",
            "User-Agent": "ThreadsSetup/1.0",
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body_text = e.read().decode(errors="replace")
        print(f"[Discord API ERROR] {method} {path}: {e.code} — {body_text}")
        sys.exit(1)


def _persist_env(env_file: Path, key: str, value: str) -> None:
    """지정된 .env 파일에 키-값 추가 (이미 있으면 업데이트)."""
    text = env_file.read_text(encoding="utf-8-sig") if env_file.exists() else ""
    pattern = re.compile(rf"^{re.escape(key)}\s*=.*$", re.MULTILINE)
    new_line = f"{key}={value}"
    if pattern.search(text):
        text = pattern.sub(new_line, text)
    else:
        text = text.rstrip() + f"\n{new_line}\n"
    env_file.write_text(text, encoding="utf-8")
    print(f"  .env 업데이트 [{env_file.name}]: {key}=***")


def main():
    print(f"[setup] Guild {GUILD_ID} 에서 #{CHANNEL_NAME} 채널 확인 중...")

    channels = discord_api("GET", f"/guilds/{GUILD_ID}/channels")
    existing = next(
        (c for c in channels if c["type"] == 0 and c["name"] == CHANNEL_NAME), None
    )

    if existing:
        channel_id = str(existing["id"])
        print(f"  기존 채널 발견: #{CHANNEL_NAME} ({channel_id})")
    else:
        created = discord_api("POST", f"/guilds/{GUILD_ID}/channels", {
            "name": CHANNEL_NAME,
            "type": 0,
            "topic": CHANNEL_TOPIC,
        })
        channel_id = str(created["id"])
        print(f"  채널 생성 완료: #{CHANNEL_NAME} ({channel_id})")

    webhooks = discord_api("GET", f"/channels/{channel_id}/webhooks")
    existing_wh = next((w for w in webhooks if w.get("name") == WEBHOOK_NAME), None)

    if existing_wh:
        webhook_url = f"https://discord.com/api/webhooks/{existing_wh['id']}/{existing_wh['token']}"
        print(f"  기존 Webhook 재사용: {WEBHOOK_NAME}")
    else:
        wh = discord_api("POST", f"/channels/{channel_id}/webhooks", {"name": WEBHOOK_NAME})
        webhook_url = f"https://discord.com/api/webhooks/{wh['id']}/{wh['token']}"
        print(f"  Webhook 생성 완료: {WEBHOOK_NAME}")

    # Bucky .env 업데이트
    _persist_env(ENV_FILE, "JH_THREADS_CHANNEL_ID", channel_id)
    _persist_env(ENV_FILE, "THREADS_DISCORD_WEBHOOK", webhook_url)

    # threads-monetization .env 업데이트
    if THREADS_ENV_FILE.exists():
        _persist_env(THREADS_ENV_FILE, "DISCORD_THREADS_CHANNEL_ID", channel_id)
        _persist_env(THREADS_ENV_FILE, "DISCORD_BOT_TOKEN", os.getenv("DISCORD_BOT_TOKEN", ""))
        _persist_env(THREADS_ENV_FILE, "DISCORD_CLIENT_ID", os.getenv("DISCORD_CLIENT_ID", ""))
        _persist_env(THREADS_ENV_FILE, "DISCORD_GUILD_ID", GUILD_ID)
        print(f"  threads-monetization .env 업데이트 완료")
    else:
        print(f"  ⚠️  threads .env 없음: {THREADS_ENV_FILE}")
        print(f"     수동으로 추가하세요: DISCORD_THREADS_CHANNEL_ID={channel_id}")

    # 채널에 알림 메시지 전송
    payload = json.dumps({
        "embeds": [{
            "title": "✅ #jh-쓰레드자동화 채널 연동 완료",
            "description": (
                "이 채널은 **쓰레드 수익화 자동화** 전용 채널입니다.\n\n"
                "**Bucky 에이전트 귀속** — 동일 봇이 관리합니다.\n\n"
                "**명령어**\n"
                "`!threads status` — 서버 상태\n"
                "`!threads run` — 일일 자동화 실행\n"
                "`!threads dry-run` — 테스트 실행\n"
                "`!threads 수익` — 수익 현황\n"
                "`!threads 계정` — 계정 목록"
            ),
            "color": 0x5865f2,
            "fields": [
                {"name": "채널 ID", "value": channel_id, "inline": True},
                {"name": "Webhook", "value": "등록 완료", "inline": True},
            ],
        }]
    }).encode()
    try:
        req = urllib.request.Request(
            webhook_url + "?wait=true", data=payload,
            headers={"Content-Type": "application/json"}
        )
        urllib.request.urlopen(req, timeout=10)
        print("  Discord 알림 메시지 전송 완료")
    except Exception as e:
        print(f"  Discord 알림 전송 실패 (무시): {e}")

    print("\n" + "=" * 60)
    print("✅ 설정 완료!")
    print("=" * 60)
    print(f"채널 ID  : {channel_id}")
    print(f"Webhook  : {webhook_url[:60]}...")
    print()
    print("다음 단계:")
    print("1. Bucky 봇 재시작 → #jh-쓰레드자동화 자동 감시 시작")
    print("2. 채널에서 `!threads status` 테스트")
    print("3. threads-monetization에서 npm run dev 후 `!threads run` 테스트")


if __name__ == "__main__":
    main()
