#!/usr/bin/env python3
"""채널에 Manage Webhooks 권한을 봇에게 부여."""
import json
import os
import sys
import urllib.request
import urllib.error
from pathlib import Path

ENV_FILE = Path(__file__).parent.parent / ".env"
CHANNEL_ID = "1517454174441181264"
MANAGE_WEBHOOKS = 536870912  # 1 << 29


def load_env(path: Path) -> dict:
    result = {}
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        result[k.strip()] = v.strip().strip('"').strip("'")
    return result


env = load_env(ENV_FILE)
TOKEN = env.get("DISCORD_BOT_TOKEN", "")

if not TOKEN:
    print("[ERROR] DISCORD_BOT_TOKEN 없음")
    sys.exit(1)


def api(method: str, path: str, body=None):
    url = f"https://discord.com/api/v10{path}"
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(
        url, data=data, method=method,
        headers={
            "Authorization": f"Bot {TOKEN}",
            "Content-Type": "application/json",
            "User-Agent": "DiscordBot (https://github.com/Rapptz/discord.py, 2.3.2) Python/3.11",
            "X-RateLimit-Precision": "millisecond",
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            raw = r.read()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        body_text = e.read().decode(errors="replace")
        print(f"[HTTP {e.code}] {method} {path}: {body_text}")
        raise


# 봇 ID 조회
me = api("GET", "/users/@me")
bot_id = me["id"]
print(f"Bot ID: {bot_id}")

# 채널 퍼미션 오버라이드 (type=1 → 특정 멤버, allow=Manage Webhooks)
try:
    api("PUT", f"/channels/{CHANNEL_ID}/permissions/{bot_id}", {
        "allow": str(MANAGE_WEBHOOKS),
        "deny": "0",
        "type": 1,
    })
    print("✅ 채널 레벨 Manage Webhooks 권한 부여 완료")
except urllib.error.HTTPError:
    print("❌ 채널 퍼미션 오버라이드 실패 — 봇 역할 권한 업데이트 시도")

    # 폴백: 봇 역할의 서버 레벨 권한에 Manage Webhooks 추가
    guild_id = env.get("DISCORD_GUILD_ID", "")
    member = api("GET", f"/guilds/{guild_id}/members/{bot_id}")
    roles = member.get("roles", [])
    print(f"봇 역할 목록: {roles}")

    guild_roles = api("GET", f"/guilds/{guild_id}/roles")
    for role in guild_roles:
        if role["id"] in roles:
            current_perms = int(role["permissions"])
            new_perms = current_perms | MANAGE_WEBHOOKS
            if new_perms != current_perms:
                try:
                    api("PATCH", f"/guilds/{guild_id}/roles/{role['id']}", {
                        "permissions": str(new_perms)
                    })
                    print(f"✅ 역할 '{role['name']}' 에 Manage Webhooks 추가")
                except urllib.error.HTTPError as e2:
                    print(f"  역할 업데이트 실패 (권한 부족): {e2}")
            else:
                print(f"  역할 '{role['name']}' 이미 Manage Webhooks 보유")
