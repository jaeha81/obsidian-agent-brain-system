#!/usr/bin/env python3
"""Create or discover the #jh-charlie Discord channel.

This script reads DISCORD_BOT_TOKEN and DISCORD_GUILD_ID from .env, creates
the channel if missing, persists JH_CHARLIE_CHANNEL_ID, and prints only the
channel name/id. It never prints secrets.
"""

from __future__ import annotations

import asyncio
import os
import re
from pathlib import Path

import discord
from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = ROOT / ".env"
CHANNEL_NAME = "jh-charlie"
ENV_KEY = "JH_CHARLIE_CHANNEL_ID"
TOPIC = "Charlie system audit, home PC continuity, drift warnings, and user confirmations"


def persist_env_key(key: str, value: str) -> None:
    text = ENV_PATH.read_text(encoding="utf-8-sig") if ENV_PATH.exists() else ""
    line = f"{key}={value}"
    if re.search(rf"^{re.escape(key)}=.*$", text, flags=re.MULTILINE):
        text = re.sub(rf"^{re.escape(key)}=.*$", line, text, flags=re.MULTILINE)
    else:
        if text and not text.endswith("\n"):
            text += "\n"
        text += line + "\n"
    ENV_PATH.write_text(text, encoding="utf-8")


class CharlieChannelClient(discord.Client):
    async def on_ready(self) -> None:
        guild_id = os.getenv("DISCORD_GUILD_ID", "").strip()
        guild = self.get_guild(int(guild_id)) if guild_id else (self.guilds[0] if self.guilds else None)
        if guild is None:
            print("CHARLIE_CHANNEL_ERROR=no_guild")
            await self.close()
            return

        channel = discord.utils.get(guild.text_channels, name=CHANNEL_NAME)
        created = False
        if channel is None:
            channel = await guild.create_text_channel(CHANNEL_NAME, topic=TOPIC)
            created = True
            await channel.send(
                "**Charlie channel initialized**\n"
                "- Purpose: system audit, home PC continuity, drift warnings, and user confirmations.\n"
                "- Charlie does not replace Bucky or auto-assign Claude Code work.\n"
                "- Reports must include completed/open/next directive/do-not-do-without-approval."
            )

        persist_env_key(ENV_KEY, str(channel.id))
        print(f"CHARLIE_CHANNEL_NAME={channel.name}")
        print(f"CHARLIE_CHANNEL_ID={channel.id}")
        print(f"CHARLIE_CHANNEL_CREATED={str(created).lower()}")
        await self.close()


async def main() -> int:
    load_dotenv(ENV_PATH, encoding="utf-8-sig")
    token = os.getenv("DISCORD_BOT_TOKEN", "").strip()
    if not token:
        print("CHARLIE_CHANNEL_ERROR=missing_DISCORD_BOT_TOKEN")
        return 1
    intents = discord.Intents.default()
    client = CharlieChannelClient(intents=intents)
    await client.start(token)
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
