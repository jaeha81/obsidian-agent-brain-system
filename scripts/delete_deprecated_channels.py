#!/usr/bin/env python3
"""Delete deprecated Discord channels approved for removal.

Channels to delete: jh-tasks, jh-status, jh-results, jh-briefing
Approved by user: 2026-06-09
"""

from __future__ import annotations

import asyncio
import os
import pathlib
import sys

import discord

ROOT = pathlib.Path(__file__).resolve().parent.parent
ENV = ROOT / ".env"

CHANNELS_TO_DELETE = ["jh-tasks", "jh-status", "jh-results", "jh-briefing"]


def load_env() -> dict[str, str]:
    values: dict[str, str] = {}
    if ENV.exists():
        for line in ENV.read_text(encoding="utf-8", errors="replace").splitlines():
            if not line or line.lstrip().startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            values[k.strip()] = v.strip().strip('"')
    return values


async def delete_channels(token: str, dry_run: bool = False) -> None:
    intents = discord.Intents.default()
    client = discord.Client(intents=intents)

    @client.event
    async def on_ready():
        try:
            if not client.guilds:
                print("ERROR: 봇이 어떤 서버에도 없습니다.")
                return

            guild = client.guilds[0]
            print(f"서버: {guild.name} ({guild.id})")
            print(f"모드: {'DRY-RUN (실제 삭제 없음)' if dry_run else '실제 삭제'}")
            print()

            found = []
            for ch_name in CHANNELS_TO_DELETE:
                ch = discord.utils.get(guild.text_channels, name=ch_name)
                if ch:
                    found.append(ch)
                    print(f"  발견: #{ch_name} (ID: {ch.id})")
                else:
                    print(f"  없음: #{ch_name}")

            if not found:
                print("\n삭제 대상 채널이 서버에 존재하지 않습니다.")
                return

            if dry_run:
                print(f"\n[DRY-RUN] 삭제 예정 채널 {len(found)}개 — 실제 삭제 없음")
                return

            print(f"\n채널 {len(found)}개 삭제 중...")
            for ch in found:
                try:
                    await ch.delete(reason="Approved deprecation: consolidated into new channel structure 2026-06-09")
                    print(f"  삭제 완료: #{ch.name} ({ch.id})")
                except discord.Forbidden:
                    print(f"  삭제 실패: #{ch.name} — 권한 없음")
                except discord.HTTPException as e:
                    print(f"  삭제 실패: #{ch.name} — {e}")

            print(f"\n완료: {len(found)}개 채널 삭제됨")

        finally:
            await client.close()

    await client.start(token)


def main() -> None:
    dry_run = "--dry-run" in sys.argv
    env = load_env()
    token = env.get("DISCORD_BOT_TOKEN", "")
    if not token:
        print("ERROR: DISCORD_BOT_TOKEN이 .env에 없습니다.")
        sys.exit(1)

    asyncio.run(delete_channels(token, dry_run=dry_run))


if __name__ == "__main__":
    main()
