#!/usr/bin/env python3
"""
setup_shorts_discord.py — #jh-shorts Discord 채널 + Webhook 자동 생성
기존 Bucky 봇 토큰(DISCORD_BOT_TOKEN)을 재사용하여 채널과 웹훅을 만든다.

실행:
  python -X utf8 scripts/setup_shorts_discord.py

완료 후:
  - .env 에 JH_SHORTS_CHANNEL_ID, SHORTS_DISCORD_WEBHOOK 자동 추가
  - Vercel 대시보드에 SHORTS_DISCORD_WEBHOOK 환경변수 추가 필요 (출력 참고)
"""
import json
import os
import sys
import urllib.request
import urllib.error
from pathlib import Path

ROOT = Path(__file__).parent.parent
ENV_FILE = ROOT / ".env"

# ── .env 로드 ─────────────────────────────────────────────────────────────────
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

CHANNEL_NAME  = "jh-shorts"
CHANNEL_TOPIC = "🤖 쇼핑 숏츠 수익화 자동화 — Vercel 대시보드 버튼 → 이 채널 → 로컬 스킬 실행"
WEBHOOK_NAME  = "ShortsAgent"


def discord_api(method: str, path: str, body: dict | None = None):
    url = f"https://discord.com/api/v10{path}"
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(
        url, data=data, method=method,
        headers={
            "Authorization": f"Bot {BOT_TOKEN}",
            "Content-Type": "application/json",
            "User-Agent": "ShortsSetup/1.0",
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body_text = e.read().decode(errors="replace")
        print(f"[Discord API ERROR] {method} {path}: {e.code} — {body_text}")
        sys.exit(1)


def _persist_env(key: str, value: str) -> None:
    """Bucky .env에 키-값 추가 (이미 있으면 업데이트)."""
    text = ENV_FILE.read_text(encoding="utf-8-sig") if ENV_FILE.exists() else ""
    import re
    pattern = re.compile(rf"^{re.escape(key)}\s*=.*$", re.MULTILINE)
    new_line = f"{key}={value}"
    if pattern.search(text):
        text = pattern.sub(new_line, text)
    else:
        text = text.rstrip() + f"\n{new_line}\n"
    ENV_FILE.write_text(text, encoding="utf-8")
    print(f"  .env 업데이트: {key}=***")


def main():
    print(f"[setup] Guild {GUILD_ID} 에서 #{CHANNEL_NAME} 채널 확인 중...")

    # 기존 채널 확인
    channels = discord_api("GET", f"/guilds/{GUILD_ID}/channels")
    existing = next((c for c in channels if c["type"] == 0 and c["name"] == CHANNEL_NAME), None)

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

    # Webhook 확인/생성
    webhooks = discord_api("GET", f"/channels/{channel_id}/webhooks")
    existing_wh = next((w for w in webhooks if w.get("name") == WEBHOOK_NAME), None)

    if existing_wh:
        webhook_url = f"https://discord.com/api/webhooks/{existing_wh['id']}/{existing_wh['token']}"
        print(f"  기존 Webhook 재사용: {WEBHOOK_NAME}")
    else:
        wh = discord_api("POST", f"/channels/{channel_id}/webhooks", {"name": WEBHOOK_NAME})
        webhook_url = f"https://discord.com/api/webhooks/{wh['id']}/{wh['token']}"
        print(f"  Webhook 생성 완료: {WEBHOOK_NAME}")

    # .env 업데이트
    _persist_env("JH_SHORTS_CHANNEL_ID", channel_id)
    _persist_env("SHORTS_DISCORD_WEBHOOK", webhook_url)

    # 채널에 알림 메시지 전송
    payload = json.dumps({
        "embeds": [{
            "title": "✅ #jh-shorts 채널 연동 완료",
            "description": (
                "이 채널은 **쇼핑숏츠 수익화 자동화** 전용 채널입니다.\n\n"
                "**동작 방식**\n"
                "1️⃣ Vercel 대시보드 버튼 클릭\n"
                "2️⃣ `[SHORTS_CMD]` 명령이 이 채널로 전송\n"
                "3️⃣ 홈 PC Bucky 봇이 수신 → 로컬 스킬 실행\n"
                "4️⃣ 결과가 Turso DB에 기록 → 대시보드 표시\n\n"
                "**수동 명령**: `!shorts status` / `!shorts run_pipeline`"
            ),
            "color": 0x57f287,
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

    print("\n" + "="*60)
    print("✅ 설정 완료!")
    print("="*60)
    print(f"채널 ID  : {channel_id}")
    print(f"Webhook  : {webhook_url[:60]}...")
    print()
    print("다음 단계:")
    print("1. Vercel 대시보드에서 환경변수 추가:")
    print(f"   SHORTS_DISCORD_WEBHOOK = {webhook_url}")
    print("2. Bucky 봇 재시작 (watchdog이 자동 재시작):")
    print("   봇은 .env 재로드 후 #jh-shorts를 감시하기 시작합니다.")
    print("3. Windows Task Scheduler 등록:")
    print("   python -X utf8 shorts-local-agent\\setup_scheduler.ps1")


if __name__ == "__main__":
    main()
