#!/usr/bin/env python3
"""
Discord Real-Time Bot — AgentBus inbox writer + Hermes Agent 실시간 대화

Discord 메시지 → Hermes Agent 응답 → Discord 채널에 답장
동시에 ObsidianVault/10_AgentBus/inbox/ 에 대화 기록 저장

Requirements:
    pip install discord.py>=2.3 python-dotenv>=1.0

Setup:
    1. Copy .env.example -> .env and fill in tokens/IDs
    2. Install and configure Hermes Agent
    3. python scripts/discord_bot.py

Commands:
    !status   - 봇 상태 확인
    !help     - 명령어 목록
    !reset    - 현재 채널 대화 기록 초기화
"""

import asyncio
import os
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import discord
from discord import Intents, Message
from dotenv import load_dotenv
from hermes_client import run_hermes

load_dotenv(Path(__file__).parent.parent / '.env', encoding='utf-8')

TOKEN: str = os.getenv("DISCORD_BOT_TOKEN", "")
GUILD_ID: str = os.getenv("DISCORD_GUILD_ID", "")
_raw_channels: str = os.getenv("DISCORD_CHANNEL_IDS", "")
ALLOWED_CHANNELS: set[str] = {c.strip() for c in _raw_channels.split(",") if c.strip()}
VAULT = Path(os.getenv("VAULT_PATH", Path(__file__).parent.parent / "ObsidianVault"))
INBOX = VAULT / "10_AgentBus" / "inbox"
MIN_LENGTH: int = int(os.getenv("DISCORD_MIN_LENGTH", "1"))
HERMES_ENABLED: bool = os.getenv("HERMES_ENABLED", "1").strip().lower() not in {"0", "false", "no"}
HERMES_MODEL: str = os.getenv("HERMES_MODEL", "default")
SYSTEM_PROMPT: str = os.getenv(
    "HERMES_SYSTEM_PROMPT",
    "당신은 Obsidian 지식 관리 시스템과 연결된 AI 에이전트입니다. "
    "사용자의 질문에 간결하고 정확하게 한국어로 답변하세요."
)

# 채널별 대화 기록 (channel_id -> list of messages)
conversation_history: dict[str, list[dict]] = defaultdict(list)
MAX_HISTORY = 20  # 채널당 최대 보관 메시지 수


def write_discord_message(message: Message, reply: str = "") -> Path:
    now = datetime.now()
    ts = now.strftime("%Y%m%d_%H%M%S")
    iso = now.isoformat(timespec="seconds")
    channel_name = getattr(message.channel, "name", str(message.channel.id))
    channel_id = str(message.channel.id)
    author_id_str = str(message.author.id)

    INBOX.mkdir(parents=True, exist_ok=True)
    out_path = INBOX / f"{ts}_discord_{channel_id}_{author_id_str}.md"

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

**User:** {message.content}
"""
    if reply:
        content += f"\n**Hermes:** {reply}\n"

    out_path.write_text(content, encoding="utf-8")
    return out_path


async def ask_hermes(channel_id: str, user_message: str) -> str:
    history = conversation_history[channel_id]
    history.append({"role": "user", "content": user_message})

    # 기록이 너무 길면 앞부분 제거
    if len(history) > MAX_HISTORY:
        conversation_history[channel_id] = history[-MAX_HISTORY:]
        history = conversation_history[channel_id]

    transcript = "\n".join(
        f"{item['role'].title()}: {item['content']}" for item in history
    )
    prompt = (
        "# Discord conversation\n\n"
        f"{SYSTEM_PROMPT}\n\n"
        "Answer the latest user message in Korean unless the user asks otherwise.\n\n"
        f"{transcript}"
    )
    reply = await asyncio.to_thread(run_hermes, prompt)
    history.append({"role": "assistant", "content": reply})
    return reply


def split_message(text: str, limit: int = 1900) -> list[str]:
    """Discord 2000자 제한 대응 - 줄 단위로 분할."""
    if len(text) <= limit:
        return [text]
    chunks, current = [], ""
    for line in text.splitlines(keepends=True):
        if len(current) + len(line) > limit:
            if current:
                chunks.append(current)
            current = line
        else:
            current += line
    if current:
        chunks.append(current)
    return chunks


class AgentBusBot(discord.Client):
    async def on_ready(self) -> None:
        guilds = [f"{g.name}({g.id})" for g in self.guilds]
        mode = f"Hermes Agent ({HERMES_MODEL})" if HERMES_ENABLED else "inbox-only"
        print(f"Bot ready: {self.user} [{mode}]", flush=True)
        print(f"Guilds: {guilds}", flush=True)
        print(f"Channels: {ALLOWED_CHANNELS or 'ALL'}", flush=True)

    async def on_message(self, message: Message) -> None:
        if message.author == self.user:
            return
        if GUILD_ID and str(getattr(message.guild, "id", "")) != GUILD_ID:
            return
        if ALLOWED_CHANNELS and str(message.channel.id) not in ALLOWED_CHANNELS:
            return

        content = message.content.strip()
        channel_id = str(message.channel.id)

        if content == "!status":
            mode = "Hermes Agent 대화 모드" if HERMES_ENABLED else "inbox 저장 모드"
            await message.channel.send(f"✅ 실행 중 ({mode})")
            return
        if content == "!help":
            await message.channel.send(
                "**명령어**\n"
                "`!status` — 봇 상태\n"
                "`!reset` — 대화 기록 초기화\n"
                "`!help` — 도움말\n"
                "_그 외 메시지는 Hermes Agent가 답변합니다._"
            )
            return
        if content == "!reset":
            conversation_history[channel_id].clear()
            await message.channel.send("🔄 대화 기록을 초기화했습니다.")
            return

        if len(content) < MIN_LENGTH:
            return

        # Hermes Agent 응답
        if HERMES_ENABLED:
            async with message.channel.typing():
                try:
                    reply = await ask_hermes(channel_id, content)
                except Exception as e:
                    reply = f"⚠️ 오류: {e}"
                    print(f"Hermes error: {e}", flush=True)

            for chunk in split_message(reply):
                await message.channel.send(chunk)

            out_path = write_discord_message(message, reply)
        else:
            out_path = write_discord_message(message)

        print(f"Saved: {out_path.name}", flush=True)


def main() -> None:
    if not TOKEN:
        print("DISCORD_BOT_TOKEN not set.")
        raise SystemExit(1)
    if not HERMES_ENABLED:
        print("HERMES_ENABLED=0 — inbox-only mode.")

    intents = Intents.default()
    intents.message_content = True
    AgentBusBot(intents=intents).run(TOKEN)


if __name__ == "__main__":
    main()
