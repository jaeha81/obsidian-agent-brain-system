#!/usr/bin/env python3
"""
Discord Real-Time Bot — Bucky Agent 구독 전용

Discord 메시지 → Bucky Agent (Claude CLI 구독) → Discord 채널 답장
동시에 ObsidianVault/10_AgentBus/inbox/ 에 대화 기록 저장 (status: answered)

API 과금 없음. run_bucky()가 ANTHROPIC_API_KEY를 env에서 제거하고
Claude Code CLI 구독 경로만 사용함.

Requirements:
    pip install discord.py>=2.3 python-dotenv>=1.0 pyyaml>=6.0

Setup:
    1. Copy .env.example -> .env and fill in tokens/IDs
    2. (선택) configs/discord_users.yaml 에 허용 사용자 등록
    3. python scripts/discord_bot.py

Commands:
    !status   — 봇 상태 확인
    !help     — 명령어 목록
    !reset    — 현재 채널 대화 기록 초기화
"""

import asyncio
import io
import os
import sys
import tempfile
from collections import defaultdict

# Windows stdout/stderr를 UTF-8로 강제 설정 (로그 인코딩 깨짐 방지)
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
from datetime import datetime
from pathlib import Path

import discord
import yaml
from discord import Intents, Message
from dotenv import load_dotenv

from bucky_client import BuckyError, run_bucky

_ROOT = Path(__file__).parent.parent
load_dotenv(_ROOT / ".env", encoding="utf-8")

# ── 환경변수 ───────────────────────────────────────────────────────────────────

TOKEN: str = os.getenv("DISCORD_BOT_TOKEN", "")
GUILD_ID: str = os.getenv("DISCORD_GUILD_ID", "")
ALLOWED_CHANNELS: set[str] = {
    c.strip() for c in os.getenv("DISCORD_CHANNEL_IDS", "").split(",") if c.strip()
}
VAULT = Path(os.getenv("VAULT_PATH", str(_ROOT / "ObsidianVault")))
INBOX = VAULT / "10_AgentBus" / "inbox"
MIN_LENGTH: int = int(os.getenv("DISCORD_MIN_LENGTH", "1"))
BUCKY_ENABLED: bool = os.getenv("BUCKY_ENABLED", "1").strip().lower() not in {"0", "false", "no"}
VOICE_ENABLED: bool = os.getenv("VOICE_ENABLED", "1").strip().lower() not in {"0", "false", "no"}
WHISPER_MODEL_NAME: str = os.getenv("WHISPER_MODEL", "small")

# Whisper 선택적 임포트 — 미설치 시 음성 기능만 비활성화, 봇은 정상 동작
if VOICE_ENABLED:
    try:
        import whisper as _whisper_module
    except ImportError:
        print("[Bot] openai-whisper 미설치 — 음성 기능 비활성화.", flush=True)
        VOICE_ENABLED = False

_whisper_model = None


def _get_whisper_model():
    global _whisper_model
    if _whisper_model is None:
        import whisper as _w
        print(f"[Bot] Whisper '{WHISPER_MODEL_NAME}' 모델 로딩 중...", flush=True)
        _whisper_model = _w.load_model(WHISPER_MODEL_NAME)
        print("[Bot] Whisper 모델 로드 완료.", flush=True)
    return _whisper_model


BUCKY_SYSTEM_PROMPT: str = os.getenv(
    "BUCKY_SYSTEM_PROMPT",
    "당신은 Bucky입니다. Obsidian 지식 관리 시스템과 연결된 AI 에이전트로, "
    "사용자의 요청에 간결하고 정확하게 한국어로 답변합니다.",
)

# ── 사용자 접근제어 ─────────────────────────────────────────────────────────────

_USERS_CONFIG_PATH = _ROOT / "configs" / "discord_users.yaml"

def _load_allowed_users() -> dict:
    """configs/discord_users.yaml 로드. 파일 없으면 빈 dict (전체 허용)."""
    if not _USERS_CONFIG_PATH.exists():
        return {}
    try:
        return yaml.safe_load(_USERS_CONFIG_PATH.read_text(encoding="utf-8")) or {}
    except Exception as e:
        print(f"[Bot] discord_users.yaml 로드 실패: {e}", flush=True)
        return {}

_USERS_CONFIG: dict = _load_allowed_users()
_ALLOWED_USER_IDS: set[str] = set(
    str(uid) for uid in _USERS_CONFIG.get("users", {}).keys()
)

def _is_user_allowed(author_id: str) -> bool:
    """허용된 사용자인지 확인. 설정 파일 없으면 전체 허용."""
    if not _ALLOWED_USER_IDS:
        return True
    return author_id in _ALLOWED_USER_IDS

def _get_user_role(author_id: str) -> str:
    users = _USERS_CONFIG.get("users", {})
    return users.get(author_id, {}).get("role", "viewer")

# ── 대화 기록 ──────────────────────────────────────────────────────────────────

conversation_history: dict[str, list[dict]] = defaultdict(list)
MAX_HISTORY = 20

# ── 유틸 ───────────────────────────────────────────────────────────────────────

def split_message(text: str, limit: int = 1900) -> list[str]:
    """Discord 2000자 제한 대응. 줄 단위 분할 후 초과 줄은 고정 길이로 재분할."""
    if len(text) <= limit:
        return [text]
    chunks: list[str] = []
    current = ""
    for line in text.splitlines(keepends=True):
        # 단일 줄이 limit 초과 → 강제 분할
        while len(line) > limit:
            if current:
                chunks.append(current)
                current = ""
            chunks.append(line[:limit])
            line = line[limit:]
        if len(current) + len(line) > limit:
            chunks.append(current)
            current = line
        else:
            current += line
    if current:
        chunks.append(current)
    return chunks


def write_discord_message(message: Message, reply: str = "", status: str = "pending") -> Path:
    """AgentBus inbox에 Discord 메시지 기록.

    bot이 직접 답변한 경우 status='answered'로 저장해
    dispatcher가 재처리하지 않도록 한다.
    """
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
channel_id: {channel_id}
author: {message.author.name}
author_id: {message.author.id}
message_id: {message.id}
created: {iso}
status: {status}
---

# Discord: #{channel_name} — {message.author.name}

> {iso}

**User:** {message.content}
"""
    if reply:
        content += f"\n**Bucky:** {reply}\n"

    out_path.write_text(content, encoding="utf-8")
    return out_path


BUCKY_CHAT_FILE = VAULT / "10_AgentBus" / "chat" / "BUCKY_CHAT.md"
_CHAT_HEADER = "---\ntype: bucky-chat\nagent: Bucky\n---\n\n# Bucky Chat\n\n"
_CHAT_MAX_ENTRIES = 50


def append_to_bucky_chat(author_name: str, user_text: str, reply_text: str) -> None:
    """Discord 대화를 BUCKY_CHAT.md에 기록 — Obsidian 채팅창에 실시간 반영."""
    now = datetime.now().isoformat(timespec="milliseconds") + "Z"
    entry = (
        f"## {now}\n\n"
        f"### User\n\n"
        f"[Discord] {author_name}: {user_text.strip()}\n\n"
        f"### Bucky\n\n"
        f"{reply_text.strip()}\n\n"
    )
    try:
        BUCKY_CHAT_FILE.parent.mkdir(parents=True, exist_ok=True)
        existing = BUCKY_CHAT_FILE.read_text(encoding="utf-8") if BUCKY_CHAT_FILE.exists() else _CHAT_HEADER
        # 최대 50개 엔트리 유지
        import re as _re
        matches = list(_re.finditer(r"\n## \d{4}-\d{2}-\d{2}T", existing))
        if len(matches) >= _CHAT_MAX_ENTRIES:
            existing = _CHAT_HEADER.strip() + existing[matches[-_CHAT_MAX_ENTRIES].start():]
        BUCKY_CHAT_FILE.write_text(existing.rstrip() + "\n\n" + entry, encoding="utf-8")
    except Exception as e:
        print(f"[Bot] BUCKY_CHAT 기록 실패: {e}", flush=True)


async def transcribe_discord_audio(attachment: discord.Attachment) -> str:
    """Discord 음성 첨부파일(ogg/mp3/wav/m4a/webm) → Whisper STT → 텍스트 반환."""
    data = await attachment.read()
    suffix = Path(attachment.filename).suffix or ".ogg"
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(data)
            tmp_path = tmp.name
        model = await asyncio.to_thread(_get_whisper_model)
        result = await asyncio.to_thread(
            lambda: model.transcribe(tmp_path, language="ko", fp16=False)
        )
        return result.get("text", "").strip()
    finally:
        if tmp_path:
            Path(tmp_path).unlink(missing_ok=True)


async def ask_bucky(channel_id: str, user_message: str) -> str:
    """Bucky Agent에 질문하고 답변 반환. Claude CLI 구독 경로만 사용."""
    history = conversation_history[channel_id]
    history.append({"role": "user", "content": user_message})

    if len(history) > MAX_HISTORY:
        conversation_history[channel_id] = history[-MAX_HISTORY:]
        history = conversation_history[channel_id]

    transcript = "\n".join(
        f"{item['role'].title()}: {item['content']}" for item in history
    )
    prompt = (
        "# Discord 대화\n\n"
        f"{BUCKY_SYSTEM_PROMPT}\n\n"
        "답변은 한국어로. 명령이 없으면 간결하게.\n\n"
        f"{transcript}"
    )
    reply = await asyncio.to_thread(run_bucky, prompt)
    history.append({"role": "assistant", "content": reply})
    return reply


# ── 봇 클래스 ──────────────────────────────────────────────────────────────────

class BuckyDiscordBot(discord.Client):
    async def on_ready(self) -> None:
        guilds = [f"{g.name}({g.id})" for g in self.guilds]
        mode = "Bucky Agent (구독)" if BUCKY_ENABLED else "inbox-only"
        user_count = len(_ALLOWED_USER_IDS) if _ALLOWED_USER_IDS else "전체 허용"
        voice_status = f"ON ({WHISPER_MODEL_NAME})" if VOICE_ENABLED else "OFF"
        print(f"Bot ready: {self.user} [{mode}]", flush=True)
        print(f"Guilds joined: {guilds}", flush=True)
        print(f"Watching channels: {ALLOWED_CHANNELS or 'ALL'}", flush=True)
        print(f"Inbox: {INBOX}", flush=True)
        print(f"허용 사용자: {user_count}", flush=True)
        print(f"음성(Whisper): {voice_status}", flush=True)

    async def on_message(self, message: Message) -> None:
        if message.author == self.user:
            return
        if GUILD_ID and str(getattr(message.guild, "id", "")) != GUILD_ID:
            return
        if ALLOWED_CHANNELS and str(message.channel.id) not in ALLOWED_CHANNELS:
            return

        author_id = str(message.author.id)
        if not _is_user_allowed(author_id):
            await message.channel.send(
                f"⛔ `{message.author.name}` — 접근 권한이 없습니다. 관리자에게 문의하세요."
            )
            return

        content = message.content.strip()
        channel_id = str(message.channel.id)

        # ── 음성 첨부파일 처리 ─────────────────────────────────────────────────
        if VOICE_ENABLED and message.attachments:
            for att in message.attachments:
                if att.content_type and att.content_type.startswith("audio/"):
                    async with message.channel.typing():
                        try:
                            transcript = await transcribe_discord_audio(att)
                            if transcript:
                                await message.channel.send(f"🎙️ **인식:** {transcript}")
                                content = f"[음성] {transcript}" if not content else f"{content} [음성] {transcript}"
                            else:
                                await message.channel.send("⚠️ 음성을 인식하지 못했습니다.")
                        except Exception as e:
                            await message.channel.send(f"⚠️ 음성 인식 실패: {e}")
                            print(f"[Bot] STT 오류: {e}", flush=True)
                    break  # 첫 번째 음성 파일만 처리

        # ── 내장 명령어 ────────────────────────────────────────────────────────
        if content == "!status":
            role = _get_user_role(author_id)
            mode = "Bucky Agent 대화 모드" if BUCKY_ENABLED else "inbox 저장 모드"
            await message.channel.send(f"✅ 실행 중 ({mode}) | 역할: `{role}`")
            return

        if content == "!help":
            await message.channel.send(
                "**Bucky 명령어**\n"
                "`!status` — 봇 상태 및 내 역할 확인\n"
                "`!reset` — 대화 기록 초기화\n"
                "`!help` — 도움말\n"
                "_그 외 메시지는 Bucky가 답변합니다._"
            )
            return

        if content == "!reset":
            conversation_history[channel_id].clear()
            await message.channel.send("🔄 대화 기록을 초기화했습니다.")
            return

        if len(content) < MIN_LENGTH:
            return

        # ── Bucky 응답 ─────────────────────────────────────────────────────────
        if BUCKY_ENABLED:
            async with message.channel.typing():
                try:
                    reply = await ask_bucky(channel_id, content)
                except BuckyError as e:
                    reply = f"⚠️ Bucky 오류: {e}"
                    print(f"[Bot] BuckyError: {e}", flush=True)
                except Exception as e:
                    reply = f"⚠️ 오류: {e}"
                    print(f"[Bot] Error: {e}", flush=True)

            for chunk in split_message(reply):
                await message.channel.send(chunk)

            # Obsidian PC 채팅창에 동기화
            append_to_bucky_chat(message.author.name, content, reply)

            # 이미 답변했으므로 status=answered → dispatcher 재처리 방지
            out_path = write_discord_message(message, reply, status="answered")
        else:
            out_path = write_discord_message(message, status="pending")

        print(f"[Bot] Saved: {out_path.name}", flush=True)


# ── 진입점 ─────────────────────────────────────────────────────────────────────

def main() -> None:
    if not TOKEN:
        print("[Bot] DISCORD_BOT_TOKEN not set.", flush=True)
        raise SystemExit(1)
    if not BUCKY_ENABLED:
        print("[Bot] BUCKY_ENABLED=0 — inbox-only 모드.", flush=True)

    intents = Intents.default()
    intents.message_content = True
    BuckyDiscordBot(intents=intents).run(TOKEN)


if __name__ == "__main__":
    main()
