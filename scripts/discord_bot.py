#!/usr/bin/env python3
"""
Discord Real-Time Bot — AgentBus inbox writer

Listens for Discord messages in configured channels and writes each one to
ObsidianVault/10_AgentBus/inbox/ as a markdown file (same format as discord_intake.py).

Requirements:
    pip install discord.py>=2.3 python-dotenv>=1.0

Setup:
    1. Copy .env.example → .env and fill in tokens/IDs
    2. python scripts/discord_bot.py

Commands available in monitored channels:
    !status   — bot replies with "running" confirmation
    !help     — bot replies with command list

Messages shorter than MIN_LENGTH chars are silently ignored (noise filter).
"""

import os
from datetime import datetime
from pathlib import Path

import discord
from discord import Intents, Message
from dotenv import load_dotenv

load_dotenv()

TOKEN: str = os.getenv("DISCORD_BOT_TOKEN", "")
GUILD_ID: str = os.getenv("DISCORD_GUILD_ID", "")
_raw_channels: str = os.getenv("DISCORD_CHANNEL_IDS", "")
ALLOWED_CHANNELS: set[str] = {c.strip() for c in _raw_channels.split(",") if c.strip()}
VAULT = Path(os.getenv("VAULT_PATH", Path(__file__).parent.parent / "ObsidianVault"))
INBOX = VAULT / "10_AgentBus" / "inbox"
MIN_LENGTH: int = int(os.getenv("DISCORD_MIN_LENGTH", "10"))


def write_discord_message(message: Message) -> Path:
    """Persist a Discord message to the AgentBus inbox."""
    now = datetime.now()
    ts = now.strftime("%Y%m%d_%H%M%S")
    iso = now.isoformat(timespec="seconds")
    channel_name = getattr(message.channel, "name", str(message.channel.id))
    safe_author = message.author.name.replace(" ", "_")

    INBOX.mkdir(parents=True, exist_ok=True)
    out_path = INBOX / f"{ts}_discord_{channel_name}_{safe_author}.md"

    content = f"""---
type: discord_intake
source: realtime_bot
channel: {channel_name}
author: {message.author.name}
author_id: {message.author.id}
message_id: {message.id}
created: {iso}
status: pending
---

# Discord: #{channel_name} — {message.author.name}

> {iso}

{message.content}
"""
    out_path.write_text(content, encoding="utf-8")
    return out_path


class AgentBusBot(discord.Client):
    async def on_ready(self) -> None:
        print(f"✅ Bot ready: {self.user} (guild filter: {GUILD_ID or 'all'})")
        print(f"   Watching channels: {ALLOWED_CHANNELS or 'ALL'}")
        print(f"   Inbox: {INBOX}")

    async def on_message(self, message: Message) -> None:
        # Ignore own messages
        if message.author == self.user:
            return

        # Guild filter (optional)
        if GUILD_ID and str(getattr(message.guild, "id", "")) != GUILD_ID:
            return

        # Channel filter (empty = monitor all channels in guild)
        if ALLOWED_CHANNELS and str(message.channel.id) not in ALLOWED_CHANNELS:
            return

        content = message.content.strip()

        # Built-in commands
        if content == "!status":
            await message.channel.send("✅ AgentBus bot running.")
            return
        if content == "!help":
            await message.channel.send(
                "**AgentBus Bot Commands**\n"
                "`!status` — confirm bot is alive\n"
                "`!help` — show this help\n"
                "_All other messages (≥10 chars) are saved to Obsidian inbox._"
            )
            return

        # Ignore very short messages
        if len(content) < MIN_LENGTH:
            return

        out_path = write_discord_message(message)
        print(f"📥 Saved: {out_path.name}")


def main() -> None:
    if not TOKEN:
        print("❌ DISCORD_BOT_TOKEN not set. Copy .env.example → .env and fill in your token.")
        raise SystemExit(1)

    intents = Intents.default()
    intents.message_content = True  # required to read message body (Privileged Intent)

    client = AgentBusBot(intents=intents)
    client.run(TOKEN)


if __name__ == "__main__":
    main()
