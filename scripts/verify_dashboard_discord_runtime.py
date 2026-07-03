#!/usr/bin/env python3
"""Runtime verification for OABS dashboard -> Bucky Discord routing.

This script sends harmless health-check intake payloads through the same local
`/intake` endpoint used by dashboards, then verifies:

- the queue file is processed,
- the intended Discord channel received the request id,
- the Bucky memory DB activated a per-dashboard-item session.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sqlite3
import sys
import time
import uuid
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import discord


ROOT = Path(__file__).resolve().parent.parent
ENV = ROOT / ".env"
QUEUE = ROOT / "data" / "intake_queue"
MEMORY_DB = ROOT / "ObsidianVault" / "10_AgentBus" / "tasks" / "bucky_memory.db"


def load_env() -> dict[str, str]:
    values: dict[str, str] = {}
    if ENV.exists():
        for line in ENV.read_text(encoding="utf-8", errors="replace").splitlines():
            if not line or line.lstrip().startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip().strip('"')
    return values


@dataclass(frozen=True)
class Target:
    name: str
    dashboard_type: str
    env_key: str
    target_channel: str
    extra: dict[str, str] | None = None


def build_targets(env: dict[str, str]) -> list[Target]:
    return [
        Target("repo", "repo", "JH_REPO_DASHBOARD_CHANNEL_ID", "jh-repo-dashboard"),
        Target("wishket", "wishket", "JH_WISHKET_CHANNEL_ID", "jh-wishket"),
        Target("daily_plus", "daily_plus", "JH_DAILYPLUS_CHANNEL_ID", "jh-daily-plus"),
        Target("task_board", "task_board", "JH_TASKBOARD_CHANNEL_ID", "jh-taskboard"),
        Target("checklist", "checklist", "JH_TASKBOARD_CHANNEL_ID", "jh-taskboard"),
        Target(
            "app_session_claude",
            "app_session",
            "JH_CLAUDE_CODE_CHANNEL_ID",
            "jh-claude-code-app",
            {"target_app": "claude_code"},
        ),
        Target(
            "app_session_codex",
            "app_session",
            "JH_CODEX_CHANNEL_ID",
            "jh-codex-app",
            {"target_app": "codex"},
        ),
    ]


def post_intake(endpoint: str, payload: dict) -> dict:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        endpoint.rstrip("/") + "/intake",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            result = json.loads(body) if body else {}
            result["_status"] = resp.status
            return result
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code}: {body}") from exc


def find_processed_file(request_id: str) -> str:
    short = request_id[:8]
    for folder in (QUEUE / "processed", QUEUE / "failed", QUEUE):
        if not folder.exists():
            continue
        matches = sorted(folder.glob(f"*{short}*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        if matches:
            rel = matches[0].relative_to(ROOT)
            return str(rel)
    return ""


def memory_session_exists(channel_id: str, session_key: str) -> bool:
    if not MEMORY_DB.exists():
        return False
    conn = sqlite3.connect(str(MEMORY_DB))
    try:
        row = conn.execute(
            "SELECT id FROM sessions WHERE channel=? AND external_key=? ORDER BY id DESC LIMIT 1",
            (channel_id, session_key),
        ).fetchone()
        return bool(row)
    finally:
        conn.close()


async def channel_has_request(token: str, guild_id: str, channel_ids: dict[str, str], request_ids: dict[str, str]) -> dict[str, bool]:
    intents = discord.Intents.default()
    client = discord.Client(intents=intents)
    results: dict[str, bool] = {}

    @client.event
    async def on_ready():
        try:
            guild = client.get_guild(int(guild_id)) if guild_id else None
            if not guild and client.guilds:
                guild = client.guilds[0]
            for name, channel_id in channel_ids.items():
                found = False
                channel = client.get_channel(int(channel_id))
                if channel is None and guild:
                    channel = guild.get_channel(int(channel_id))
                if channel is not None:
                    needle = request_ids[name][:8]
                    async for msg in channel.history(limit=25):
                        if needle in (msg.content or ""):
                            found = True
                            break
                results[name] = found
        finally:
            await client.close()

    await client.start(token)
    return results


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--endpoint", default="http://127.0.0.1:8765")
    parser.add_argument("--wait", type=float, default=8.0)
    args = parser.parse_args()

    env = load_env()
    token = env.get("DISCORD_BOT_TOKEN", "")
    guild_id = env.get("DISCORD_GUILD_ID", "")
    if not token:
        print("FAIL missing DISCORD_BOT_TOKEN")
        return 2

    run_id = datetime.now().strftime("%Y%m%d%H%M%S")
    targets = build_targets(env)
    request_ids: dict[str, str] = {}
    channel_ids: dict[str, str] = {}
    payloads: dict[str, dict] = {}
    post_results: dict[str, dict] = {}

    for target in targets:
        channel_id = env.get(target.env_key, "")
        if not channel_id:
            print(f"FAIL {target.name} missing {target.env_key}")
            return 2
        request_id = f"{target.name[:3]}{uuid.uuid4().hex[:8]}-{run_id}"
        payload = {
            "type": "runtime_verify",
            "dashboard_type": target.dashboard_type,
            "target_channel": target.target_channel,
            "source": "verify_dashboard_discord_runtime",
            "source_dashboard_url": "runtime://verify-dashboard-discord-routing",
            "action": "health_check",
            "request_id": request_id,
            "item_id": f"verify-{target.name}",
            "session_id": f"verify-session-{run_id}-{target.name}",
            "title": f"Runtime verify {target.name}",
            "summary": "Verify dashboard intake reaches the intended Discord channel and session memory.",
            "createdAt": datetime.now().isoformat(timespec="seconds"),
        }
        if target.extra:
            payload.update(target.extra)
        response = post_intake(args.endpoint, payload)
        if response.get("_status") != 202:
            print(f"FAIL {target.name} intake status={response.get('_status')}")
            return 1
        request_ids[target.name] = request_id
        channel_ids[target.name] = channel_id
        payloads[target.name] = payload
        post_results[target.name] = response
        print(f"POST {target.name} status=202 request_id={request_id[:8]} channel={channel_id}")

    time.sleep(args.wait)

    discord_results = asyncio.run(channel_has_request(token, guild_id, channel_ids, request_ids))
    failures: list[str] = []
    for target in targets:
        payload = payloads[target.name]
        request_id = request_ids[target.name]
        channel_id = channel_ids[target.name]
        processed = find_processed_file(request_id)
        session_key = f"{payload['dashboard_type']}:{payload['session_id']}"
        session_ok = memory_session_exists(channel_id, session_key)
        discord_ok = discord_results.get(target.name, False)
        state = "PASS" if processed and discord_ok and session_ok else "FAIL"
        print(
            f"{state} {target.name} processed={processed or 'missing'} "
            f"discord={discord_ok} session={session_ok}"
        )
        if state != "PASS":
            failures.append(target.name)

    if failures:
        print("FAIL targets=" + ",".join(failures))
        return 1
    print("PASS dashboard Discord runtime verification")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
