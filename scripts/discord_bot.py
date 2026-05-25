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

# Windows stdout/stderr UTF-8 설정 — reconfigure 사용 (Python 3.7+)
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
    except Exception:
        pass
from datetime import datetime, timedelta
from pathlib import Path

import discord
import yaml
from discord import Intents, Message, app_commands
from dotenv import load_dotenv

from bucky_client import BuckyError, run_bucky
from bucky_briefing import generate_briefing
from task_tracker import add_task, format_task_list, get_today_tasks
from daily_report_generator import run as generate_daily_report
from bucky_dispatcher import dispatch as dispatch_task, get_pending_tasks

_ROOT = Path(__file__).parent.parent
load_dotenv(_ROOT / ".env", encoding="utf-8")

# Discord 봇은 Vault 파일 읽기·명령 실행이 필요 → 항상 auto(dangerously-skip-permissions)
os.environ.setdefault("BUCKY_TOOL_MODE", "auto")

# ── 자동 브리핑 스케줄 ─────────────────────────────────────────────────────────
AUTO_BRIEFING: bool = os.getenv("AUTO_BRIEFING", "0").strip().lower() in {"1", "true", "yes"}
BRIEFING_CHANNEL_ID: str = os.getenv("BRIEFING_CHANNEL_ID", "")
BRIEFING_TIME: str = os.getenv("BRIEFING_TIME", "09:00")  # HH:MM 로컬 시각

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
VOICE_CHANNEL_ENABLED: bool = os.getenv("VOICE_CHANNEL_ENABLED", "1").strip().lower() not in {"0", "false", "no"}
TTS_LANG: str = os.getenv("TTS_LANG", "ko")
VOICE_RECV_ENABLED: bool = os.getenv("VOICE_RECV_ENABLED", "1").strip().lower() not in {"0", "false", "no"}

# Whisper 선택적 임포트 — 미설치 시 음성 기능만 비활성화, 봇은 정상 동작
if VOICE_ENABLED:
    try:
        import whisper as _whisper_module
    except ImportError:
        print("[Bot] openai-whisper 미설치 — 음성 기능 비활성화.", flush=True)
        VOICE_ENABLED = False

# gTTS 선택적 임포트 — 음성 채널 TTS 출력용
_gtts_available = False
if VOICE_CHANNEL_ENABLED:
    try:
        from gtts import gTTS as _gTTS
        _gtts_available = True
        print("[Bot] gTTS 로드 완료 — TTS 음성 출력 활성화", flush=True)
    except ImportError:
        print("[Bot] gTTS 미설치 — TTS 비활성화. pip install gTTS", flush=True)

# discord-ext-voice-recv 선택적 임포트 — 실시간 음성 수신용
_voice_recv: object = None
if VOICE_CHANNEL_ENABLED and VOICE_RECV_ENABLED and VOICE_ENABLED:
    try:
        import discord.ext.voice_recv as _voice_recv_mod  # type: ignore
        _voice_recv = _voice_recv_mod
        print("[Bot] discord-ext-voice-recv 로드 완료 — 실시간 음성 수신 활성화", flush=True)
    except ImportError:
        print("[Bot] discord-ext-voice-recv 미설치 — 실시간 수신 비활성화. pip install discord-ext-voice-recv", flush=True)

# 음성 채널 상태 관리
_voice_clients: dict[int, discord.VoiceClient] = {}   # guild_id → VoiceClient
_voice_text_ch: dict[int, "discord.abc.Messageable"] = {}  # guild_id → 텍스트 채널
_speaking_locks: "dict[int, asyncio.Lock]" = {}

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


import re as _re

_FILLER_PATTERN = _re.compile(
    r"(?<!\w)(음+|어+|아+|그+|저+|그니까|그러니까|있잖아|있죠|있어요|뭔가)(?!\w)",
    _re.IGNORECASE
)

_URL_PATTERN = _re.compile(r'https?://[^\s<>"\']+')
_YOUTUBE_PATTERN = _re.compile(r'(youtu\.be/|youtube\.com/watch\?|youtube\.com/shorts/)[\w?=&-]+')

_CLAUDE_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
_STT_ENHANCE_ENABLED: bool = bool(_CLAUDE_API_KEY) and os.getenv("STT_AI_ENHANCE", "1").strip() not in {"0", "false", "no"}
_NLP_ENABLED: bool = os.getenv("NLP_ENABLED", "1").strip() not in {"0", "false", "no"}

# ── STT 고도화 + NLP 전처리기 선택적 임포트 ─────────────────────────────────
_stt_enhance_fn = None
_nlp_preprocess_fn = None
try:
    _scripts_dir = str(_ROOT / "scripts")
    if _scripts_dir not in sys.path:
        sys.path.insert(0, _scripts_dir)
    from stt_enhanced import postprocess_for_discord as _stt_enhance_fn  # type: ignore
    from nlp_preprocessor import preprocess as _nlp_preprocess_fn  # type: ignore
    print("[Bot] STT 고도화 + NLP 전처리기 로드 완료", flush=True)
except Exception as _nlp_e:
    print(f"[Bot] STT/NLP 모듈 로드 실패 (기본 후처리 사용): {_nlp_e}", flush=True)


def _postprocess_stt(text: str) -> str:
    """Typeless 스타일 기본 후처리: 필러 제거 + 중복 공백 정리."""
    text = _FILLER_PATTERN.sub("", text)
    return _re.sub(r"\s{2,}", " ", text).strip()


def _postprocess_stt_claude(text: str) -> str:
    """STT 고도화 — bucky_stt_enhancer(의도분류+명령어감지) 우선, 폴백: Claude API.

    필러 제거 + 반복 문장 정리 + 의도 명확화 + 명령어 자동 감지.
    """
    # Item 4: 고도화 STT 모듈 (의도분류 + 명령어 감지 포함)
    if _stt_enhance_fn:
        try:
            return _stt_enhance_fn(text)
        except Exception as _e:
            print(f"[STT] 고도화 모듈 실패: {_e}", flush=True)

    if not _STT_ENHANCE_ENABLED or len(text) < 10:
        return _postprocess_stt(text)

    prompt = f"""다음은 한국어 음성 인식(STT) 결과입니다. 아래 규칙에 따라 정제하세요:

1. 필러 단어 제거: "음", "어", "아", "그", "저", "그니까", "있잖아", "뭔가" 등
2. 반복되는 표현 정리 (동일 내용 중복 제거)
3. 문장 의도를 유지하면서 자연스럽게 다듬기
4. 원문의 내용과 의도를 절대 바꾸지 말 것
5. 정제된 텍스트만 출력 (설명 없이)

STT 원문:
{text}"""

    try:
        import urllib.request
        import urllib.error
        body = json.dumps({
            "model": "claude-haiku-4-5-20251001",
            "max_tokens": 300,
            "messages": [{"role": "user", "content": prompt}],
        }).encode("utf-8")
        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=body,
            headers={
                "x-api-key": _CLAUDE_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            refined = data["content"][0]["text"].strip()
            if refined:
                return refined
    except Exception as e:
        print(f"[STT] Claude API 후처리 실패, 기본 후처리 사용: {e}", flush=True)

    return _postprocess_stt(text)


async def _auto_capture_url_bg(url: str, notify_channel=None) -> None:
    """URL을 백그라운드로 Obsidian에 캡처 — YouTube는 전용 모듈로 처리."""
    try:
        import sys as _sys
        scripts_dir = str(Path(__file__).parent)
        if scripts_dir not in _sys.path:
            _sys.path.insert(0, scripts_dir)

        is_youtube = bool(_YOUTUBE_PATTERN.search(url))
        if is_youtube:
            from bucky_youtube_capture import capture_youtube
            result = await asyncio.to_thread(capture_youtube, url)
            if result["success"]:
                msg = (
                    f"📺 **YouTube 지식 캡처 완료!**\n"
                    f"📝 {result['title']}\n"
                    f"{'트랜스크립트 포함 ✅' if result['has_transcript'] else '트랜스크립트 없음'}\n"
                    f"```\n{result['summary'][:300]}\n```" if result.get("summary") else ""
                )
                print(f"[AutoCapture] YouTube 저장: {result['filepath']}", flush=True)
                if notify_channel:
                    for chunk in split_message(msg):
                        await notify_channel.send(chunk)
            else:
                print(f"[AutoCapture] YouTube 실패: {result.get('error')}", flush=True)
        else:
            from bucky_knowledge_capture import capture_url
            saved = await asyncio.to_thread(capture_url, url)
            print(f"[AutoCapture] 저장: {saved}", flush=True)
    except Exception as e:
        print(f"[AutoCapture] 실패 ({url[:50]}): {e}", flush=True)


async def transcribe_discord_audio(attachment: discord.Attachment) -> str:
    """Discord 음성 첨부파일(ogg/mp3/wav/m4a/webm) → Whisper STT → AI 후처리 → 텍스트 반환."""
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
        raw = result.get("text", "").strip()
        # Claude API 가용 시 고급 후처리, 아니면 regex 폴백
        return await asyncio.to_thread(_postprocess_stt_claude, raw)
    finally:
        if tmp_path:
            Path(tmp_path).unlink(missing_ok=True)


# ── 음성 채널 TTS / 수신 헬퍼 ──────────────────────────────────────────────────

def _get_speaking_lock(guild_id: int) -> asyncio.Lock:
    if guild_id not in _speaking_locks:
        _speaking_locks[guild_id] = asyncio.Lock()
    return _speaking_locks[guild_id]


async def _tts_speak(vc: discord.VoiceClient, text: str, guild_id: int) -> None:
    """텍스트 → gTTS MP3 → FFmpegPCMAudio → 음성 채널 재생."""
    if not _gtts_available or not vc or not vc.is_connected():
        return
    # 마크다운 특수문자 제거 (TTS 자연스럽게)
    import re as _re
    clean = _re.sub(r"[*`#_~>|]", "", text)[:500]
    if not clean.strip():
        return

    async with _get_speaking_lock(guild_id):
        tmp_path = None
        try:
            tts = _gTTS(text=clean, lang=TTS_LANG, slow=False)
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
                tmp_path = f.name
            await asyncio.to_thread(tts.save, tmp_path)

            if vc.is_playing():
                vc.stop()
                await asyncio.sleep(0.2)

            done_event = asyncio.Event()
            path_ref = tmp_path

            def _after(error):
                Path(path_ref).unlink(missing_ok=True)
                asyncio.get_event_loop().call_soon_threadsafe(done_event.set)

            vc.play(discord.FFmpegPCMAudio(tmp_path), after=_after)
            await asyncio.wait_for(done_event.wait(), timeout=60)
            tmp_path = None  # after callback이 삭제 담당
        except asyncio.TimeoutError:
            pass
        except Exception as e:
            print(f"[TTS] 재생 오류: {e}", flush=True)
        finally:
            if tmp_path:
                Path(tmp_path).unlink(missing_ok=True)


async def _join_voice_channel(vc_channel: discord.VoiceChannel, text_channel, guild_id: int) -> discord.VoiceClient | None:
    """지정 음성 채널에 입장. 이미 연결된 경우 이동."""
    try:
        existing = _voice_clients.get(guild_id)
        if existing and existing.is_connected():
            await existing.move_to(vc_channel)
            vc = existing
        elif _voice_recv:
            vc = await vc_channel.connect(cls=_voice_recv.VoiceRecvClient)  # type: ignore
        else:
            vc = await vc_channel.connect()

        _voice_clients[guild_id] = vc
        _voice_text_ch[guild_id] = text_channel

        # 실시간 음성 수신 등록 — 기존 sink 정리 후 새로 등록
        if _voice_recv and hasattr(vc, "listen"):
            if hasattr(vc, "sink") and vc.sink:  # type: ignore
                try:
                    vc.stop_listening()  # type: ignore
                except Exception:
                    pass
            sink = BuckyVoiceSink(guild_id)
            vc.listen(sink)  # type: ignore
            print(f"[Voice] BuckyVoiceSink 등록 완료 — guild {guild_id}", flush=True)

        return vc
    except Exception as e:
        print(f"[Voice] 입장 오류: {e}", flush=True)
        return None


async def _leave_voice_channel(guild_id: int) -> None:
    vc = _voice_clients.pop(guild_id, None)
    _voice_text_ch.pop(guild_id, None)
    if vc and vc.is_connected():
        if vc.is_playing():
            vc.stop()
        await vc.disconnect()


# ── 실시간 음성 수신 싱크 ──────────────────────────────────────────────────────

def _make_voice_sink_class():
    """_voice_recv 로드 후 동적으로 AudioSink 상속 클래스 생성."""
    base = _voice_recv.AudioSink if _voice_recv else object  # type: ignore

    class BuckyVoiceSinkInner(base):  # type: ignore
        """discord-ext-voice-recv AudioSink — PCM → Whisper STT → Bucky → TTS."""

        SILENCE_SEC = 1.5
        MIN_PACKETS = 10

        def __init__(self, guild_id: int) -> None:
            if base is not object:
                super().__init__()
            self.guild_id = guild_id
            self._chunks: dict[int, list[bytes]] = defaultdict(list)
            self._tasks: dict[int, asyncio.Task] = {}
            # 생성 시점(async 컨텍스트)에 loop 캡처 — write()는 다른 스레드에서 호출됨
            try:
                self._loop = asyncio.get_running_loop()
            except RuntimeError:
                self._loop = asyncio.get_event_loop()

        def wants_opus(self) -> bool:
            return False

        def write(self, user, data) -> None:  # type: ignore
            # user=None은 Discord가 SSRC→멤버 매핑 전 상태 — uid=0으로 계속 처리
            uid = user.id if user is not None else 0
            pcm = data.pcm if hasattr(data, "pcm") else bytes(data) if data else b""
            if not pcm:
                return
            self._chunks[uid].append(pcm)
            if len(self._chunks[uid]) == 1:
                name = user.display_name if user is not None else "Unknown"
                print(f"[VoiceSink] 음성 수신 시작: {name}", flush=True)

            # 이전 타이머 취소 (스레드 안전)
            task = self._tasks.pop(uid, None)
            if task and not task.done():
                self._loop.call_soon_threadsafe(task.cancel)

            # 새 타이머 등록 (call_soon_threadsafe로 event loop 스레드에서 create_task 실행)
            def _schedule():
                self._tasks[uid] = self._loop.create_task(self._process_silence(user, uid))

            try:
                self._loop.call_soon_threadsafe(_schedule)
            except Exception as e:
                print(f"[VoiceSink] 스케줄 오류: {e}", flush=True)

        async def _process_silence(self, user, uid: int) -> None:
            try:
                await asyncio.sleep(self.SILENCE_SEC)
                chunks = self._chunks.pop(uid, [])
                if len(chunks) < self.MIN_PACKETS:
                    return
                await self._handle_audio(user, chunks)
            except asyncio.CancelledError:
                pass
            except Exception as e:
                print(f"[VoiceSink] 처리 오류: {e}", flush=True)

        async def _handle_audio(self, user, chunks: list[bytes]) -> None:
            import wave
            pcm = b"".join(chunks)
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                wav_path = f.name
            try:
                with wave.open(wav_path, "wb") as wf:
                    wf.setnchannels(2)
                    wf.setsampwidth(2)
                    wf.setframerate(48000)
                    wf.writeframes(pcm)

                model = await asyncio.to_thread(_get_whisper_model)
                result = await asyncio.to_thread(
                    lambda: model.transcribe(wav_path, language="ko", fp16=False)
                )
                text = _postprocess_stt(result.get("text", "").strip())
                if not text or len(text) < 2:
                    return

                ch = _voice_text_ch.get(self.guild_id)
                if not ch:
                    return

                display_name = user.display_name if user is not None else "음성"
                await ch.send(f"🎙️ **{display_name}:** {text}")
                reply = await ask_bucky(str(self.guild_id), text)
                for chunk in split_message(reply):
                    await ch.send(chunk)

                vc = _voice_clients.get(self.guild_id)
                if vc and vc.is_connected():
                    await _tts_speak(vc, reply, self.guild_id)
            finally:
                Path(wav_path).unlink(missing_ok=True)

        def cleanup(self, error) -> None:
            pass

    return BuckyVoiceSinkInner


BuckyVoiceSink = _make_voice_sink_class()


# ── /evolve 슬래시 명령어 헬퍼 ────────────────────────────────────────────────

_KNOWLEDGE_GAPS_PATH = VAULT / "00_System" / "knowledge-gaps.md"
_EVOLUTION_LOG_PATH = VAULT / "00_System" / "evolution-log.md"
_AGENT_BUS_QUEUE = VAULT / "10_AgentBus" / "agent-room-messages.jsonl"
_KNOWLEDGE_GAP_ANALYZER = _ROOT / "scripts" / "knowledge_gap_analyzer.py"


def _read_evolve_status() -> dict:
    """evolution-log.md와 knowledge-gaps.md를 읽어 상태 딕셔너리 반환."""
    import re as _re

    # 마지막 실행 시각 파싱
    last_run = "기록 없음"
    if _EVOLUTION_LOG_PATH.exists():
        text = _EVOLUTION_LOG_PATH.read_text(encoding="utf-8", errors="replace")
        # ## YYYY-MM-DD 또는 ## YYYY-MM-DDTHH:MM 형태 탐색
        matches = _re.findall(r"##\s+(\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}[^\n]*)", text)
        if not matches:
            matches = _re.findall(r"##\s+(\d{4}-\d{2}-\d{2}[^\n]*)", text)
        if matches:
            last_run = matches[-1].strip()

    # 지식갭 수 파싱 (## 또는 - 으로 시작하는 갭 항목 카운트)
    gap_count = 0
    if _KNOWLEDGE_GAPS_PATH.exists():
        gap_text = _KNOWLEDGE_GAPS_PATH.read_text(encoding="utf-8", errors="replace")
        # H2 섹션 기준 갭 수 (frontmatter 제외)
        gap_count = len(_re.findall(r"^#{1,3} ", gap_text, flags=_re.MULTILINE))
        if gap_count == 0:
            # 목록 항목 기준 폴백
            gap_count = len(_re.findall(r"^\s*[-*] ", gap_text, flags=_re.MULTILINE))

    # 태스크 수: evolution-log.md 내 task/created 키워드
    task_count = 0
    if _EVOLUTION_LOG_PATH.exists():
        text = _EVOLUTION_LOG_PATH.read_text(encoding="utf-8", errors="replace")
        task_count = len(_re.findall(r"태스크|task|generated|created", text, flags=_re.IGNORECASE))

    return {"last_run": last_run, "task_count": task_count, "gap_count": gap_count}


def _read_knowledge_gap_tasks(limit: int = 10) -> list[dict]:
    """agent-room-messages.jsonl에서 knowledge_gap_fill 타입 태스크 최근 N개 반환."""
    import json as _json

    if not _AGENT_BUS_QUEUE.exists():
        return []

    results: list[dict] = []
    try:
        lines = _AGENT_BUS_QUEUE.read_text(encoding="utf-8", errors="replace").splitlines()
        for line in lines:
            line = line.strip()
            if not line:
                continue
            try:
                entry = _json.loads(line)
            except _json.JSONDecodeError:
                continue
            msg_type = entry.get("type", "") or entry.get("task_type", "")
            if "knowledge_gap" in msg_type.lower():
                results.append(entry)
    except Exception:
        return []

    # 최신 N개 (뒤에서부터)
    return results[-limit:]


async def ask_bucky(channel_id: str, user_message: str) -> str:
    """Bucky Agent에 질문하고 답변 반환. NLP 전처리 후 Claude CLI 구독 경로 사용."""
    history = conversation_history[channel_id]

    # Item 1: NLP 전처리 — COMMAND 의도 감지 시 구조화 힌트 삽입
    nlp_hint = ""
    if _nlp_preprocess_fn and _NLP_ENABLED and len(user_message) > 5:
        try:
            context_msgs = [m["content"] for m in history[-4:]]
            nlp_result = _nlp_preprocess_fn(user_message, context_msgs)
            action = nlp_result.get("action", "")
            if action in ("BUILD", "DEPLOY", "FIX", "UPGRADE") and nlp_result.get("confidence", 0) >= 0.5:
                router = nlp_result.get("agent_router", "")
                target = nlp_result.get("target", "")
                nlp_hint = f"[NLP: {action}→{router} | 대상:{target}] "
        except Exception as _e:
            print(f"[NLP] 전처리 실패: {_e}", flush=True)

    enriched_message = nlp_hint + user_message if nlp_hint else user_message
    history.append({"role": "user", "content": enriched_message})

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


# ── /evolve 슬래시 명령어 등록 ────────────────────────────────────────────────

def _register_evolve_commands(tree: app_commands.CommandTree) -> None:
    """CommandTree에 /evolve 그룹(status · tasks · run) 등록."""

    evolve_group = app_commands.Group(
        name="evolve",
        description="Bucky 진화 사이클 관리 명령어",
    )

    @evolve_group.command(name="status", description="마지막 진화 사이클 실행 시각, 태스크 수, 지식갭 수 표시")
    async def evolve_status(interaction: discord.Interaction) -> None:
        await interaction.response.defer(thinking=True)
        try:
            status = await asyncio.to_thread(_read_evolve_status)
            gaps_exists = "✅" if _KNOWLEDGE_GAPS_PATH.exists() else "⚠️ 파일 없음"
            elog_exists = "✅" if _EVOLUTION_LOG_PATH.exists() else "⚠️ 파일 없음"
            lines = [
                "**[Evolve Status]**",
                f"마지막 실행: `{status['last_run']}`",
                f"생성된 태스크 수: `{status['task_count']}`",
                f"지식갭 수: `{status['gap_count']}`",
                f"knowledge-gaps.md: {gaps_exists}",
                f"evolution-log.md: {elog_exists}",
            ]
            await interaction.followup.send("\n".join(lines))
        except Exception as e:
            await interaction.followup.send(f"⚠️ status 조회 오류: {e}")
            print(f"[Evolve] status 오류: {e}", flush=True)

    @evolve_group.command(name="tasks", description="AgentBus 큐에서 knowledge_gap_fill 태스크 목록 표시 (최근 10개)")
    async def evolve_tasks(interaction: discord.Interaction) -> None:
        await interaction.response.defer(thinking=True)
        try:
            tasks = await asyncio.to_thread(_read_knowledge_gap_tasks, 10)
            if not tasks:
                queue_exists = "✅" if _AGENT_BUS_QUEUE.exists() else "⚠️ 파일 없음"
                await interaction.followup.send(
                    f"**[Evolve Tasks]**\nknowledge_gap_fill 태스크 없음 (큐: {queue_exists})"
                )
                return

            import json as _json
            lines = [f"**[Evolve Tasks]** — 최근 {len(tasks)}개"]
            for i, task in enumerate(reversed(tasks), 1):
                ts = task.get("timestamp", task.get("created", ""))[:19] if isinstance(
                    task.get("timestamp", task.get("created", "")), str
                ) else ""
                title = task.get("title", task.get("subject", task.get("gap", "")))
                msg_type = task.get("type", task.get("task_type", ""))
                status = task.get("status", "")
                parts = [f"`{i}.`"]
                if ts:
                    parts.append(f"`{ts}`")
                parts.append(f"[{msg_type}]")
                if title:
                    parts.append(title[:60])
                if status:
                    parts.append(f"({status})")
                lines.append(" ".join(parts))

            for chunk in split_message("\n".join(lines)):
                await interaction.followup.send(chunk)
        except Exception as e:
            await interaction.followup.send(f"⚠️ tasks 조회 오류: {e}")
            print(f"[Evolve] tasks 오류: {e}", flush=True)

    @evolve_group.command(name="run", description="knowledge_gap_analyzer.py 즉시 실행 후 결과 전송")
    async def evolve_run(interaction: discord.Interaction) -> None:
        await interaction.response.defer(thinking=True)
        if not _KNOWLEDGE_GAP_ANALYZER.exists():
            await interaction.followup.send(
                f"⚠️ `knowledge_gap_analyzer.py` 파일이 없습니다.\n경로: `{_KNOWLEDGE_GAP_ANALYZER}`"
            )
            return
        try:
            import subprocess as _subprocess
            await interaction.followup.send("⚙️ `knowledge_gap_analyzer.py` 실행 중...")
            result = await asyncio.to_thread(
                lambda: _subprocess.run(
                    [sys.executable, str(_KNOWLEDGE_GAP_ANALYZER)],
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=120,
                    cwd=str(_ROOT),
                )
            )
            stdout = result.stdout.strip()
            stderr = result.stderr.strip()
            rc = result.returncode

            status_icon = "✅" if rc == 0 else "❌"
            output_lines = [f"{status_icon} **[Evolve Run]** 종료코드: `{rc}`"]
            if stdout:
                output_lines.append(f"**stdout:**\n```\n{stdout[:1200]}\n```")
            if stderr:
                output_lines.append(f"**stderr:**\n```\n{stderr[:600]}\n```")
            if not stdout and not stderr:
                output_lines.append("_(출력 없음)_")

            for chunk in split_message("\n".join(output_lines)):
                await interaction.followup.send(chunk)
            print(f"[Evolve] run 완료 — rc={rc}", flush=True)
        except asyncio.TimeoutError:
            await interaction.followup.send("⚠️ 실행 타임아웃 (120초 초과)")
        except Exception as e:
            await interaction.followup.send(f"⚠️ run 실행 오류: {e}")
            print(f"[Evolve] run 오류: {e}", flush=True)

    tree.add_command(evolve_group)


# ── /tasks · /report 슬래시 명령어 등록 ──────────────────────────────────────

def _register_tasks_commands(tree: app_commands.CommandTree) -> None:
    """세션 태스크 조회(/tasks) · 데일리 리포트 생성(/report) 등록."""

    @tree.command(name="tasks", description="오늘 세션 태스크 현황 표시 (ClaudeCode / Codex / Bucky)")
    async def cmd_tasks(interaction: discord.Interaction) -> None:
        await interaction.response.defer(thinking=True)
        try:
            tasks = await asyncio.to_thread(get_today_tasks)
            text = format_task_list(tasks)
            for chunk in split_message("**📋 세션 태스크**\n\n" + text):
                await interaction.followup.send(chunk)
        except Exception as e:
            await interaction.followup.send(f"⚠️ tasks 조회 오류: {e}")

    @tree.command(name="report", description="오늘 데일리 리포트 생성 후 전송")
    async def cmd_report(interaction: discord.Interaction) -> None:
        await interaction.response.defer(thinking=True)
        try:
            content, jh_path, obs_path = await asyncio.to_thread(generate_daily_report)
            header = f"📊 **[데일리 리포트]** `{jh_path.name}`"
            for chunk in split_message(header + "\n\n" + content[:3000]):
                await interaction.followup.send(chunk)
        except Exception as e:
            await interaction.followup.send(f"⚠️ 리포트 생성 오류: {e}")


# ── /landing · /deploy · /pipeline 슬래시 명령어 등록 ──────────────────────────

def _register_deploy_commands(tree: app_commands.CommandTree) -> None:
    """랜딩 페이지 생성(/landing) · Vercel 배포(/deploy) · 원스톱 파이프라인(/pipeline) 등록."""

    @tree.command(name="landing", description="GitHub 레포 URL → 프리미엄 랜딩 페이지 생성 후 HTML 파일 전송")
    @app_commands.describe(repo_url="GitHub 레포 URL (예: https://github.com/user/repo)")
    async def cmd_landing(interaction: discord.Interaction, repo_url: str) -> None:
        await interaction.response.defer(thinking=True)
        try:
            sys.path.insert(0, str(_ROOT / "scripts"))
            from bucky_landing_generator import from_github_url as _gen
            out_path = await asyncio.to_thread(_gen, repo_url)
            await interaction.followup.send(
                f"✅ **랜딩 페이지 생성 완료!**\n📦 `{out_path.name}`",
                file=discord.File(str(out_path), filename=out_path.name),
            )
        except Exception as e:
            await interaction.followup.send(f"⚠️ 랜딩 페이지 생성 오류: {e}")
            print(f"[Deploy] landing 오류: {e}", flush=True)

    @tree.command(name="deploy", description="프로젝트 경로 → Vercel 배포 후 URL 전송")
    @app_commands.describe(
        project_path="배포할 프로젝트 경로 (절대 경로 또는 루트 기준 상대 경로)",
        project_name="프로젝트 이름 (비워두면 경로에서 자동 추출)",
    )
    async def cmd_deploy(
        interaction: discord.Interaction,
        project_path: str,
        project_name: str = "",
    ) -> None:
        await interaction.response.defer(thinking=True)
        try:
            sys.path.insert(0, str(_ROOT / "scripts"))
            from bucky_vercel_deploy import deploy as _deploy
            path = Path(project_path)
            if not path.is_absolute():
                path = _ROOT / project_path
            result = await asyncio.to_thread(_deploy, str(path), project_name)
            if result["success"]:
                await interaction.followup.send(
                    f"✅ **{result['project']}** 배포 완료!\n🌐 {result.get('url', '확인 중...')}"
                )
            else:
                await interaction.followup.send(
                    f"❌ 배포 실패: {result.get('error', '알 수 없는 오류')[:500]}"
                )
        except Exception as e:
            await interaction.followup.send(f"⚠️ 배포 오류: {e}")
            print(f"[Deploy] deploy 오류: {e}", flush=True)

    @tree.command(name="pipeline", description="GitHub 레포 URL → 랜딩 페이지 생성 + Vercel 배포 (원스톱)")
    @app_commands.describe(repo_url="GitHub 레포 URL (예: https://github.com/user/repo)")
    async def cmd_pipeline(interaction: discord.Interaction, repo_url: str) -> None:
        await interaction.response.defer(thinking=True)
        try:
            sys.path.insert(0, str(_ROOT / "scripts"))
            from bucky_landing_generator import from_github_url as _gen
            from bucky_vercel_deploy import deploy_landing_page as _deploy_landing

            await interaction.followup.send(f"⚙️ 파이프라인 시작: `{repo_url}`\n**1️⃣** 랜딩 페이지 생성 중...")
            out_path = await asyncio.to_thread(_gen, repo_url)
            repo_name = out_path.stem

            await interaction.followup.send(f"**2️⃣** Vercel 배포 중 (`{repo_name}`)...")
            result = await asyncio.to_thread(_deploy_landing, repo_name, out_path)

            if result["success"]:
                await interaction.followup.send(
                    f"✅ **파이프라인 완료!**\n"
                    f"📦 레포: `{repo_name}`\n"
                    f"🌐 URL: {result.get('url', '확인 중...')}\n"
                    f"⏱️ {result.get('deployed_at', '')[:19]}"
                )
            else:
                await interaction.followup.send(
                    f"⚠️ 랜딩 페이지 생성 완료, Vercel 배포 실패\n"
                    f"```{result.get('error', '')[:300]}```"
                )
        except Exception as e:
            await interaction.followup.send(f"⚠️ 파이프라인 오류: {e}")
            print(f"[Deploy] pipeline 오류: {e}", flush=True)


# ── /analyze · /nlp 슬래시 명령어 등록 ──────────────────────────────────────

def _register_analyze_commands(tree: app_commands.CommandTree) -> None:
    """/analyze (패턴 즉시 분석) · /nlp (NLP 전처리 결과 표시) 등록."""

    @tree.command(name="analyze", description="반복 패턴 즉시 분석 후 스킬 제안 결과 표시")
    async def cmd_analyze(interaction: discord.Interaction) -> None:
        await interaction.response.defer(thinking=True)
        try:
            sys.path.insert(0, str(_ROOT / "scripts"))
            from bucky_pattern_extractor import run as run_patterns
            result = await asyncio.to_thread(run_patterns, False)  # webhook 알림 없이 실행

            patterns = result.get("patterns", [])
            suggestions = result.get("suggestions", [])
            report = result.get("report", "")

            if not patterns:
                await interaction.followup.send("📊 **[패턴 분석]** 아직 반복 패턴 없음 (메시지 더 쌓이면 재시도)")
                return

            lines = [f"🔍 **[패턴 분석 결과]** — {len(patterns)}개 패턴 감지"]
            for i, p in enumerate(patterns[:5], 1):
                nlp_badge = "🧠" if p.get("nlp_enhanced") else "📊"
                lines.append(
                    f"{nlp_badge} `{i}.` **{p['pattern_key'][:40]}** — {p['count']}회"
                )
            if suggestions:
                lines.append(f"\n💡 **스킬 자동 제안**: {len(suggestions)}개")
                for s in suggestions[:3]:
                    lines.append(f"  • `{s['skill']}` ({s['count']}회)")
            if report:
                lines.append(f"\n📄 `{Path(report).name}`")

            for chunk in split_message("\n".join(lines)):
                await interaction.followup.send(chunk)
            print("[Analyze] 즉시 패턴 분석 완료", flush=True)
        except Exception as e:
            await interaction.followup.send(f"⚠️ 분석 오류: {e}")
            print(f"[Analyze] 오류: {e}", flush=True)

    @tree.command(name="nlp", description="텍스트 NLP 전처리 — 액션/컴포넌트/구조화 프롬프트 반환")
    @app_commands.describe(text="분석할 자연어 텍스트 (예: 대시보드 만들어줘)")
    async def cmd_nlp(interaction: discord.Interaction, text: str) -> None:
        await interaction.response.defer(thinking=True)
        try:
            sys.path.insert(0, str(_ROOT / "scripts"))
            from bucky_nlp_preprocessor import preprocess, format_for_discord as _nlp_fmt
            result = await asyncio.to_thread(preprocess, text)

            lines = [
                f"🧠 **[NLP 전처리 결과]**",
                f"입력: `{text[:60]}`",
                f"액션: **{result.get('action', '?')}**",
                f"컴포넌트: `{result.get('component') or '없음'}`",
                f"타겟: `{result.get('target', '?')}`",
                f"신뢰도: `{result.get('confidence', 0):.0%}`",
            ]
            structured = result.get("structured_prompt", "")
            if structured and structured != text:
                lines.append(f"\n📝 **구조화 프롬프트:**\n```\n{structured[:400]}\n```")

            fmt = _nlp_fmt(result)
            if fmt:
                lines.append(fmt)

            await interaction.followup.send("\n".join(lines))
        except Exception as e:
            await interaction.followup.send(f"⚠️ NLP 오류: {e}")
            print(f"[NLP] 오류: {e}", flush=True)


# ── /wishket 슬래시 명령어 등록 ──────────────────────────────────────────────

def _register_wishket_commands(tree: app_commands.CommandTree) -> None:
    """/wishket (공고 수집+제안서 생성) · /wishket_stats · /wishket_won 등록."""
    import sys as _sys
    _sys.path.insert(0, str(Path(__file__).parent))

    @tree.command(name="wishket", description="Wishket 공고 자동 수집 + 제안서 생성 + 수익 파이프라인 실행")
    async def cmd_wishket(interaction: discord.Interaction) -> None:
        await interaction.response.defer(thinking=True)
        try:
            from bucky_wishket_agent import run_full_pipeline, format_stats_message
            result = await asyncio.get_event_loop().run_in_executor(None, run_full_pipeline)

            if result["status"] == "no_projects":
                await interaction.followup.send("📭 조건에 맞는 공고가 없습니다. 키워드나 예산 조건을 확인하세요.")
                return

            lines = [f"**Wishket 파이프라인 완료** — {result['count']}개 제안서 생성\n"]
            for p in result["proposals"][:3]:
                lines.append(f"**{p['title']}** ({p['budget']})")
                lines.append(f"> {p['preview'][:150]}...")
                lines.append("")

            if len(result["proposals"]) > 3:
                lines.append(f"_외 {len(result['proposals'])-3}개..._\n")

            lines.append(format_stats_message(result.get("stats", {})))
            await interaction.followup.send("\n".join(lines)[:2000])
        except Exception as e:
            await interaction.followup.send(f"⚠️ Wishket 오류: {e}")
            print(f"[Wishket] 오류: {e}", flush=True)

    @tree.command(name="wishket_stats", description="Wishket 응찰 현황 및 누적 수익 조회")
    async def cmd_wishket_stats(interaction: discord.Interaction) -> None:
        await interaction.response.defer(thinking=True)
        try:
            from bucky_wishket_agent import get_stats, format_stats_message
            stats = get_stats()
            await interaction.followup.send(format_stats_message(stats))
        except Exception as e:
            await interaction.followup.send(f"⚠️ 통계 조회 오류: {e}")

    @tree.command(name="wishket_won", description="낙찰 수동 기록 — 프로젝트명과 수익(만원) 입력")
    @app_commands.describe(
        project_title="낙찰된 프로젝트 제목 (일부 입력 가능)",
        revenue_wan="수익 금액 (만원 단위, 예: 150)",
    )
    async def cmd_wishket_won(
        interaction: discord.Interaction,
        project_title: str,
        revenue_wan: int,
    ) -> None:
        await interaction.response.defer(thinking=True)
        try:
            from bucky_wishket_agent import mark_won, get_stats, format_stats_message
            ok = mark_won(project_title, revenue_wan)
            if ok:
                stats = get_stats()
                await interaction.followup.send(
                    f"낙찰 기록 완료!\n"
                    f"**{project_title}** — {revenue_wan}만원\n\n"
                    + format_stats_message(stats)
                )
            else:
                await interaction.followup.send(f"⚠️ '{project_title}'에 해당하는 대기 중 공고를 찾지 못했습니다.")
        except Exception as e:
            await interaction.followup.send(f"⚠️ 낙찰 기록 오류: {e}")


# ── 봇 클래스 ──────────────────────────────────────────────────────────────────

class BuckyDiscordBot(discord.Client):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.tree = app_commands.CommandTree(self)
        _register_evolve_commands(self.tree)
        _register_tasks_commands(self.tree)
        _register_deploy_commands(self.tree)
        _register_analyze_commands(self.tree)
        _register_wishket_commands(self.tree)

    async def setup_hook(self) -> None:
        # 슬래시 명령어 전역 동기화
        try:
            synced = await self.tree.sync()
            print(f"[Bot] 슬래시 명령어 동기화 완료 — {len(synced)}개", flush=True)
        except Exception as e:
            print(f"[Bot] 슬래시 명령어 동기화 실패: {e}", flush=True)

        if AUTO_BRIEFING and BRIEFING_CHANNEL_ID:
            self.loop.create_task(self._daily_briefing_task())

        # 6시간마다 패턴 분석 자동 실행
        self.loop.create_task(self._periodic_pattern_task())
        # 매일 1회 자기 반성 (P2)
        self.loop.create_task(self._periodic_reflection_task())
        # 매일 오전 8:30 Wishket 공고 자동 스캔
        self.loop.create_task(self._wishket_auto_scan_task())

    async def _daily_briefing_task(self) -> None:
        """매일 BRIEFING_TIME에 자동 브리핑 게시."""
        await self.wait_until_ready()
        h, m = (int(x) for x in BRIEFING_TIME.split(":"))
        print(f"[Bot] 자동 브리핑 스케줄 ON — 매일 {BRIEFING_TIME} / 채널 {BRIEFING_CHANNEL_ID}", flush=True)

        # 오늘 브리핑 파일이 없고 지정 시각이 지났으면 즉시 발송
        date_str = datetime.now().strftime("%Y-%m-%d")
        briefing_today = VAULT / "04_DAILY_REPORTS" / "briefings" / f"{date_str}-briefing.md"
        now = datetime.now()
        if not briefing_today.exists() and (now.hour > h or (now.hour == h and now.minute >= m)):
            await self._post_auto_briefing()

        while not self.is_closed():
            now = datetime.now()
            next_run = now.replace(hour=h, minute=m, second=0, microsecond=0)
            if next_run <= now:
                next_run += timedelta(days=1)
            await asyncio.sleep((next_run - now).total_seconds())
            await self._post_auto_briefing()

    async def _periodic_pattern_task(self) -> None:
        """매일 자정(00:05) 패턴 분석 자동 실행. 임계값 초과 패턴은 Discord 알림."""
        await self.wait_until_ready()
        # 오늘 자정이 지났으면 내일 00:05까지 대기, 아니면 오늘 00:05 대기
        now = datetime.now()
        next_run = now.replace(hour=0, minute=5, second=0, microsecond=0)
        if next_run <= now:
            next_run += timedelta(days=1)
        initial_wait = (next_run - now).total_seconds()
        print(f"[Bot] 패턴 분석 스케줄: 다음 실행 {next_run.strftime('%Y-%m-%d %H:%M')}", flush=True)
        await asyncio.sleep(initial_wait)

        while not self.is_closed():
            try:
                import sys as _sys
                if str(_ROOT / "scripts") not in _sys.path:
                    _sys.path.insert(0, str(_ROOT / "scripts"))
                from bucky_pattern_extractor import run as run_patterns
                result = await asyncio.to_thread(run_patterns, True)

                # 임계값 초과 패턴이 있으면 BRIEFING_CHANNEL_ID 로 알림
                patterns = result.get("patterns", [])
                high_freq = [p for p in patterns if p.get("count", 0) >= 5]
                if high_freq and BRIEFING_CHANNEL_ID:
                    channel = self.get_channel(int(BRIEFING_CHANNEL_ID))
                    if channel:
                        top = high_freq[0]
                        await channel.send(
                            f"🚨 **[패턴 임계값 초과]**\n"
                            f"패턴 `{top['pattern_key'][:40]}` — **{top['count']}회** 반복\n"
                            f"💡 스킬 자동 제안이 생성되었습니다. `/analyze` 로 확인하세요."
                        )
                print("[Bot] 자동 패턴 분석 완료", flush=True)
            except Exception as e:
                print(f"[Bot] 패턴 분석 오류: {e}", flush=True)
            await asyncio.sleep(3600 * 24)  # 다음 날 자정까지 24시간 대기

    async def _periodic_reflection_task(self) -> None:
        """매일 1회 자기 반성 자동 실행 (P2)."""
        await self.wait_until_ready()
        await asyncio.sleep(3600 * 4)  # 봇 시작 4시간 후 첫 실행
        while not self.is_closed():
            try:
                import sys as _sys
                if str(_ROOT / "scripts") not in _sys.path:
                    _sys.path.insert(0, str(_ROOT / "scripts"))
                from bucky_self_reflection import run as run_reflection
                await asyncio.to_thread(run_reflection, True)
                print("[Bot] 자동 자기 반성 완료", flush=True)
            except Exception as e:
                print(f"[Bot] 자기 반성 오류: {e}", flush=True)
            await asyncio.sleep(3600 * 24)  # 24시간 대기

    async def _wishket_auto_scan_task(self) -> None:
        """매일 오전 8:30 Wishket 공고 자동 스캔 + 제안서 생성."""
        await self.wait_until_ready()

        # profile에서 스캔 시각 로드
        try:
            import yaml as _yaml
            _profile = _yaml.safe_load((_ROOT / "configs" / "wishket_profile.yaml").read_text(encoding="utf-8")) or {}
            _h = int(_profile.get("auto_scan_hour", 8))
            _m = int(_profile.get("auto_scan_minute", 30))
        except Exception:
            _h, _m = 8, 30

        now = datetime.now()
        next_run = now.replace(hour=_h, minute=_m, second=0, microsecond=0)
        if next_run <= now:
            next_run += timedelta(days=1)
        print(f"[WishketAuto] 다음 스캔: {next_run.strftime('%Y-%m-%d %H:%M')}", flush=True)
        await asyncio.sleep((next_run - now).total_seconds())

        while not self.is_closed():
            try:
                import sys as _sys
                if str(_ROOT / "scripts") not in _sys.path:
                    _sys.path.insert(0, str(_ROOT / "scripts"))
                from bucky_wishket_agent import run_full_pipeline, format_stats_message
                result = await asyncio.to_thread(run_full_pipeline)

                if BRIEFING_CHANNEL_ID:
                    channel = self.get_channel(int(BRIEFING_CHANNEL_ID))
                    if channel and result.get("count", 0) > 0:
                        lines = [
                            f"💰 **[Wishket 자동 스캔]** — {result['count']}개 제안서 생성 완료",
                        ]
                        for p in result.get("proposals", [])[:3]:
                            lines.append(f"  • **{p['title'][:40]}** ({p['budget']})")
                        lines.append(format_stats_message(result.get("stats", {})))
                        await channel.send("\n".join(lines)[:2000])
                        print("[WishketAuto] 스캔 완료 → Discord 알림 발송", flush=True)
                    elif channel and result.get("status") == "no_projects":
                        await channel.send("📭 **[Wishket]** 오늘 조건 맞는 공고 없음")
            except Exception as e:
                print(f"[WishketAuto] 오류: {e}", flush=True)

            await asyncio.sleep(3600 * 24)  # 24시간 후 재실행

    async def _post_auto_briefing(self) -> None:
        channel = self.get_channel(int(BRIEFING_CHANNEL_ID))
        if not channel:
            print(f"[Bot] 자동 브리핑: 채널 {BRIEFING_CHANNEL_ID} 없음", flush=True)
            return
        try:
            briefing_text, saved_path = await asyncio.to_thread(generate_briefing)
            fname = Path(saved_path).name
            header = f"📡 **[자동 브리핑]** `{fname}`"
            for chunk in split_message(header + "\n\n" + briefing_text):
                await channel.send(chunk)
            print(f"[Bot] 자동 브리핑 발송 → #{getattr(channel, 'name', channel.id)}", flush=True)
        except Exception as e:
            print(f"[Bot] 자동 브리핑 오류: {e}", flush=True)

    async def on_voice_state_update(self, member, before, after) -> None:
        """봇 혼자 남으면 자동 퇴장."""
        if not VOICE_CHANNEL_ENABLED:
            return
        if member == self.user:
            return
        guild_id = member.guild.id
        vc = _voice_clients.get(guild_id)
        if not vc or not vc.is_connected():
            return
        # 채널에 봇만 남았으면 퇴장
        members_in_vc = [m for m in vc.channel.members if not m.bot]
        if not members_in_vc:
            ch = _voice_text_ch.get(guild_id)
            await _leave_voice_channel(guild_id)
            if ch:
                await ch.send("👋 채널에 아무도 없어 퇴장했습니다.")

    async def on_ready(self) -> None:
        guilds = [f"{g.name}({g.id})" for g in self.guilds]
        mode = "Bucky Agent (구독)" if BUCKY_ENABLED else "inbox-only"
        user_count = len(_ALLOWED_USER_IDS) if _ALLOWED_USER_IDS else "전체 허용"
        voice_status = f"ON ({WHISPER_MODEL_NAME})" if VOICE_ENABLED else "OFF"
        tts_status = f"ON ({TTS_LANG})" if _gtts_available else "OFF"
        recv_status = "ON" if _voice_recv else "OFF"
        print(f"Bot ready: {self.user} [{mode}]", flush=True)
        print(f"Guilds joined: {guilds}", flush=True)
        print(f"Watching channels: {ALLOWED_CHANNELS or 'ALL'}", flush=True)
        print(f"Inbox: {INBOX}", flush=True)
        print(f"허용 사용자: {user_count}", flush=True)
        print(f"음성(Whisper STT): {voice_status}", flush=True)
        print(f"음성(TTS 출력): {tts_status}", flush=True)
        print(f"음성(실시간 수신): {recv_status}", flush=True)

        # ── 자동 음성 채널 입장 (AUTO_JOIN_VOICE_CHANNEL_ID 설정 시) ──────────────
        auto_join_ch_id = os.getenv("AUTO_JOIN_VOICE_CHANNEL_ID", "").strip()
        auto_join_text_ch_id = os.getenv("AUTO_JOIN_TEXT_CHANNEL_ID", "").strip()
        if auto_join_ch_id and VOICE_CHANNEL_ENABLED:
            await asyncio.sleep(2)  # 게이트웨이 안정화 대기
            try:
                vc_channel = self.get_channel(int(auto_join_ch_id))
                text_channel = self.get_channel(int(auto_join_text_ch_id)) if auto_join_text_ch_id else None
                if vc_channel and isinstance(vc_channel, discord.VoiceChannel):
                    guild_id = vc_channel.guild.id
                    await _join_voice_channel(vc_channel, text_channel, guild_id)
                    print(f"[Voice] 자동 입장: {vc_channel.name}", flush=True)
                    if text_channel:
                        await text_channel.send(f"🎙️ `{vc_channel.name}` 음성 채널에 자동 입장했습니다. 말씀하세요!")
            except Exception as e:
                print(f"[Voice] 자동 입장 실패: {e}", flush=True)

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

        # ── URL 자동 캡처 — YouTube는 알림 포함, 일반 URL은 조용히 처리 ──────────────
        if content and not content.startswith("!") and not content.startswith("/"):
            urls = _URL_PATTERN.findall(content)
            for url in urls:
                is_yt = bool(_YOUTUBE_PATTERN.search(url))
                notify_ch = message.channel if is_yt else None
                asyncio.ensure_future(_auto_capture_url_bg(url, notify_ch))

        # ── 음성 첨부파일 처리 + NLP 전처리 ───────────────────────────────────────
        if VOICE_ENABLED and message.attachments:
            for att in message.attachments:
                if att.content_type and att.content_type.startswith("audio/"):
                    async with message.channel.typing():
                        try:
                            transcript = await transcribe_discord_audio(att)
                            if transcript:
                                await message.channel.send(f"🎙️ **인식:** {transcript}")
                                # NLP 전처리 — 음성 명령 구조화
                                if _NLP_ENABLED:
                                    try:
                                        import sys as _sys
                                        if str(Path(__file__).parent) not in _sys.path:
                                            _sys.path.insert(0, str(Path(__file__).parent))
                                        from bucky_nlp_preprocessor import preprocess, format_for_discord as _nlp_fmt
                                        nlp_result = await asyncio.to_thread(preprocess, transcript)
                                        if nlp_result.get("confidence", 0) > 0.3 and nlp_result.get("action") != "EXPLAIN":
                                            fmt = _nlp_fmt(nlp_result)
                                            if fmt:
                                                await message.channel.send(fmt)
                                        content = nlp_result.get("structured_prompt", transcript)
                                        content = f"[음성] {content}"
                                    except Exception as _nlp_err:
                                        print(f"[NLP] 전처리 오류: {_nlp_err}", flush=True)
                                        content = f"[음성] {transcript}" if not content else f"{content} [음성] {transcript}"
                                else:
                                    content = f"[음성] {transcript}" if not content else f"{content} [음성] {transcript}"
                            else:
                                await message.channel.send("⚠️ 음성을 인식하지 못했습니다.")
                        except Exception as e:
                            await message.channel.send(f"⚠️ 음성 인식 실패: {e}")
                            print(f"[Bot] STT 오류: {e}", flush=True)
                    break  # 첫 번째 음성 파일만 처리

        # ── 내장 명령어 ────────────────────────────────────────────────────────
        if content == "!debug":
            guild_id = getattr(message.guild, "id", None)
            vc = _voice_clients.get(guild_id) if guild_id else None
            vc_status = f"✅ 연결됨: {vc.channel.name}" if (vc and vc.is_connected()) else "❌ 미연결"
            recv_ok = "✅ OK" if _voice_recv else "❌ 미설치"
            whisper_ok = f"✅ OK ({WHISPER_MODEL_NAME})" if VOICE_ENABLED else "❌ 미설치"
            gtts_ok = "✅ OK" if _gtts_available else "❌ 비활성화"
            sink_ok = "✅ 등록됨" if (vc and hasattr(vc, "sink") and vc.sink) else "❌ 미등록"  # type: ignore
            has_listen = "✅ VoiceRecvClient" if (vc and hasattr(vc, "listen")) else "❌ 기본VoiceClient"
            members_in_vc = []
            if vc and vc.is_connected():
                members_in_vc = [m.display_name for m in vc.channel.members if not m.bot]
            await message.channel.send(
                f"**[음성 디버그]**\n"
                f"VoiceClient: {vc_status}\n"
                f"클라이언트: {has_listen} | Sink: {sink_ok}\n"
                f"voice-recv: {recv_ok} | Whisper: {whisper_ok} | gTTS: {gtts_ok}\n"
                f"채널 멤버: {', '.join(members_in_vc) or '없음'}"
            )
            return

        if content == "!status":
            role = _get_user_role(author_id)
            mode = "Bucky Agent 대화 모드" if BUCKY_ENABLED else "inbox 저장 모드"
            await message.channel.send(f"✅ 실행 중 ({mode}) | 역할: `{role}`")
            return

        if content == "!help":
            vc_status = "활성화" if VOICE_CHANNEL_ENABLED else "비활성화"
            tts_status = "활성화" if _gtts_available else "비활성화 (pip install gTTS)"
            recv_status = "활성화" if _voice_recv else "비활성화 (pip install discord-ext-voice-recv)"
            await message.channel.send(
                "**Bucky 명령어**\n"
                "`!status` — 봇 상태 및 내 역할 확인\n"
                "`!reset` — 대화 기록 초기화\n"
                "`!tasks` / `!태스크` / `!현황` — 오늘 태스크 현황\n"
                "`!태스크추가 <내용>` — 태스크 등록 및 배분\n"
                "`!배분 <내용>` — 태스크 자동 분류 → Claude/Codex/Sub-agent 배분\n"
                "`!배분현황` — 대기 중인 배분 태스크 조회\n"
                "`!리포트` / `!report` — 데일리 리포트 생성\n"
                "`!수집` / `!collect` — GPT+Claude 세션 수집 → 지식 정제 파이프라인\n"
                "`!위임 <내용>` / `!delegate` — 복잡한 작업을 서브에이전트에게 자동 분리 위임\n"
                "`!에이전트` / `!agents` — 서브에이전트 역할 목록 확인\n"
                "`!이관` / `!migrate` — Google Drive Agent Room → ObsidianVault 이관\n"
                "`!브리핑` / `!briefing` / `!뉴스` — AI/기술 일일 브리핑 생성\n"
                "`!깃헙` — GitHub 레포 카탈로그 전체 업데이트\n"
                "`!깃헙 [repo명]` — 특정 레포 상태 조회\n"
                "`!상품화 <GitHub URL>` — 랜딩 페이지 + 결제 + Vercel 배포 통합 파이프라인\n"
                "`!랜딩 <GitHub URL 또는 이름>` — 랜딩 페이지만 생성\n"
                "`!배포 <경로>` — 프로젝트를 Vercel에 배포\n"
                "`!저장 <URL 또는 텍스트>` / `!캡처` — Obsidian 지식베이스에 저장\n"
                "`!패턴` / `!pattern` — 반복 요청 패턴 분석 → 스킬 자동 제안\n"
                f"`!입장` / `!join` — 내가 있는 음성 채널 입장 ({vc_status})\n"
                f"`!퇴장` / `!leave` — 음성 채널 퇴장\n"
                f"TTS: {tts_status} | 실시간 수신: {recv_status}\n"
                "`!help` — 도움말\n"
                "_그 외 메시지는 Bucky가 답변합니다._"
            )
            return

        if content == "!reset":
            conversation_history[channel_id].clear()
            await message.channel.send("🔄 대화 기록을 초기화했습니다.")
            return

        # ── 음성 채널 입장 ──────────────────────────────────────────────────────
        if content in ("!입장", "!join") and VOICE_CHANNEL_ENABLED:
            guild_id = getattr(message.guild, "id", None)
            if not guild_id:
                await message.channel.send("⚠️ 서버(Guild) 채널에서만 사용 가능합니다.")
                return
            member = message.guild.get_member(message.author.id)
            vc_channel = member.voice.channel if (member and member.voice) else None
            if not vc_channel:
                await message.channel.send("⚠️ 먼저 음성 채널에 입장하세요.")
                return
            await message.channel.send(f"🎙️ `{vc_channel.name}` 입장 중...")
            vc = await _join_voice_channel(vc_channel, message.channel, guild_id)
            if vc:
                await message.channel.send(f"✅ `{vc_channel.name}` 입장 완료. Bucky 음성 대화 준비됨.")
                await _tts_speak(vc, "안녕하세요. Bucky 음성 채널 연결 완료.", guild_id)
            else:
                await message.channel.send("⚠️ 음성 채널 입장 실패. FFmpeg 설치를 확인하세요.")
            return

        if content in ("!퇴장", "!leave") and VOICE_CHANNEL_ENABLED:
            guild_id = getattr(message.guild, "id", None)
            if guild_id and guild_id in _voice_clients:
                await _leave_voice_channel(guild_id)
                await message.channel.send("👋 음성 채널에서 퇴장했습니다.")
            else:
                await message.channel.send("ℹ️ 현재 음성 채널에 없습니다.")
            return

        if content in ("!tasks", "!태스크", "!현황"):
            task_text = format_task_list()
            for chunk in split_message(task_text):
                await message.channel.send(chunk)
            return

        if content.startswith("!태스크추가 ") or content.startswith("!task "):
            body = content.split(" ", 1)[1].strip()
            if body:
                task = await asyncio.to_thread(add_task, body[:40], body, None, "discord")
                await message.channel.send(
                    f"✅ 태스크 등록: `{task['id']}` → **{task['type']}** → {task['router']}"
                )
            return

        if content in ("!리포트", "!report", "!일지"):
            async with message.channel.typing():
                try:
                    report_content, jh_path, _ = await asyncio.to_thread(generate_daily_report)
                    header = f"📊 **데일리 리포트 저장** → `{jh_path.name}`\n\n"
                    for chunk in split_message(header + report_content[:1600]):
                        await message.channel.send(chunk)
                except Exception as e:
                    await message.channel.send(f"⚠️ 리포트 생성 실패: {e}")
            return

        if content.startswith("!배분 ") or content.startswith("!dispatch "):
            body = content.split(" ", 1)[1].strip()
            if body:
                task = await asyncio.to_thread(dispatch_task, body, "discord")
                agent = task.get("agent", "unknown")
                task_id = task.get("id", "?")
                agent_emoji = {"claude": "🤖", "codex": "🔍", "collector": "📥", "distiller": "🧠", "gap": "🔎", "reporter": "📊"}.get(agent, "📋")
                await message.channel.send(
                    f"{agent_emoji} **[{agent}] 배분 완료**\n"
                    f"태스크 ID: `{task_id}`\n"
                    f"내용: {body[:80]}"
                )
            return

        if content in ("!배분현황", "!pending"):
            tasks = await asyncio.to_thread(get_pending_tasks)
            if not tasks:
                await message.channel.send("✅ 대기 중인 태스크 없음")
            else:
                lines = [f"**📋 대기 태스크 ({len(tasks)}개)**"]
                for t in tasks[:10]:
                    lines.append(f"• [{t['agent']}] {t['instruction'][:60]} — `{t['id']}`")
                await message.channel.send("\n".join(lines))
            return

        if content in ("!수집", "!collect", "!파이프라인"):
            async with message.channel.typing():
                await message.channel.send("⚙️ 수집 파이프라인 시작 중... (GPT + Claude → 정제 → 갭 분석)")
                try:
                    import subprocess as _sp
                    pipeline_script = str(Path(__file__).parent / "collection_pipeline.py")
                    result = await asyncio.to_thread(
                        lambda: _sp.run(
                            [sys.executable, pipeline_script],
                            capture_output=True, text=True, encoding="utf-8", timeout=600
                        )
                    )
                    out = (result.stdout + result.stderr).strip()
                    status = "✅ 완료" if result.returncode == 0 else f"⚠️ 일부 실패 (rc={result.returncode})"
                    summary = out[-800:] if len(out) > 800 else out
                    for chunk in split_message(f"📥 **파이프라인 {status}**\n```\n{summary}\n```"):
                        await message.channel.send(chunk)
                except Exception as e:
                    await message.channel.send(f"❌ 파이프라인 실행 오류: {e}")
            return

        # ── 서브에이전트 위임 ───────────────────────────────────────────────────────
        if content.startswith("!위임") or content.startswith("!delegate"):
            body = content.split(None, 1)[1].strip() if len(content.split(None, 1)) > 1 else ""
            if not body:
                await message.channel.send("사용법: `!위임 <작업 내용>` — 복잡한 작업을 서브에이전트에게 분리 위임")
                return
            async with message.channel.typing():
                try:
                    from bucky_sub_agent_manager import delegate, summary_report
                    result = await asyncio.to_thread(delegate, body)
                    report = summary_report(result)
                    for chunk in split_message(report):
                        await message.channel.send(chunk)
                except Exception as e:
                    await message.channel.send(f"❌ 위임 실패: {e}")
            return

        if content in ("!이관", "!migrate", "!gdrive"):
            async with message.channel.typing():
                await message.channel.send("⚙️ Google Drive Agent Room 이관 시작 중...")
                try:
                    import subprocess as _sp
                    migrator = str(Path(__file__).parent / "gdrive_agent_room_migrator.py")
                    result = await asyncio.to_thread(
                        lambda: _sp.run(
                            [sys.executable, migrator],
                            capture_output=True, text=True, encoding="utf-8", timeout=300
                        )
                    )
                    out = (result.stdout + result.stderr).strip()[-800:]
                    status = "✅ 완료" if result.returncode == 0 else f"⚠️ 실패 (rc={result.returncode})"
                    for chunk in split_message(f"📦 **Agent Room 이관 {status}**\n```\n{out}\n```"):
                        await message.channel.send(chunk)
                except Exception as e:
                    await message.channel.send(f"❌ 이관 오류: {e}")
            return

        if content in ("!에이전트", "!agents", "!roles"):
            lines = [
                "**서브에이전트 역할 분담**\n",
                "🤖 **Bucky** — 조율(오케스트레이터), 지식 정제, 갭 분석, 브리핑",
                "🛠️ **ClaudeCode** — 구현(코드 작성, 스크립트, 파일 생성, 수정)",
                "🔍 **Codex** — 검토, 검수, 리뷰, 테스트 검증",
                "📥 **Collector** — GPT/Claude/Codex 대화 수집 파이프라인",
                "🧠 **Distiller** — 원시 대화 → 구조화 지식 변환\n",
                "→ `!위임 <작업>` 으로 자동 분류 위임",
            ]
            await message.channel.send("\n".join(lines))
            return

        if content in ("!브리핑", "!briefing", "!뉴스"):
            async with message.channel.typing():
                try:
                    briefing_text, saved_path = await asyncio.to_thread(generate_briefing)
                    reply_header = f"📡 **브리핑 생성 완료** — `{Path(saved_path).name}`\n\n"
                    for chunk in split_message(reply_header + briefing_text):
                        await message.channel.send(chunk)
                except Exception as e:
                    await message.channel.send(f"⚠️ 브리핑 생성 실패: {e}")
                    print(f"[Bot] 브리핑 오류: {e}", flush=True)
            return

        # ── GitHub 카탈로그 명령어 ──────────────────────────────────────────────
        if content == "!깃헙" or content.startswith("!깃헙 "):
            async with message.channel.typing():
                try:
                    # scripts 폴더를 sys.path에 추가
                    import sys as _sys
                    scripts_dir = str(Path(__file__).parent)
                    if scripts_dir not in _sys.path:
                        _sys.path.insert(0, scripts_dir)

                    repo_arg = content[len("!깃헙"):].strip()

                    if repo_arg:
                        # 특정 레포 상태 조회
                        from bucky_sub_agents.github_agent import cmd_status
                        reply_text = await asyncio.to_thread(
                            cmd_status, {"repo": repo_arg}
                        )
                    else:
                        # 전체 카탈로그 업데이트
                        from bucky_sub_agents.github_agent import cmd_catalog
                        await message.channel.send("⚙️ GitHub 레포 카탈로그 업데이트 중...")
                        reply_text = await asyncio.to_thread(cmd_catalog, {})

                    for chunk in split_message(reply_text):
                        await message.channel.send(chunk)
                except Exception as e:
                    await message.channel.send(f"⚠️ GitHub 명령 실패: {e}")
                    print(f"[Bot] GitHub 오류: {e}", flush=True)
            return

        # ── P1 패턴 분석 ───────────────────────────────────────────────────────────
        if content in ("!패턴", "!pattern", "!패턴분석"):
            async with message.channel.typing():
                try:
                    import sys as _sys
                    if str(Path(__file__).parent) not in _sys.path:
                        _sys.path.insert(0, str(Path(__file__).parent))
                    from bucky_pattern_extractor import run as run_patterns
                    await message.channel.send("🔍 패턴 분석 시작...")
                    result = await asyncio.to_thread(run_patterns, False)
                    patterns = result.get("patterns", [])
                    suggestions = result.get("suggestions", [])
                    if not patterns:
                        await message.channel.send("📊 분석할 반복 패턴이 없습니다. (메시지 축적 필요)")
                    else:
                        lines = [f"**🔄 패턴 분석 완료** — {len(patterns)}개 감지"]
                        for i, p in enumerate(patterns[:5], 1):
                            lines.append(f"`{i}.` {p['pattern_key'][:50]} — **{p['count']}회**")
                        if suggestions:
                            lines.append(f"\n💡 **{len(suggestions)}개 스킬 자동 제안** 생성됨 (`.claude/skills/suggested/`)")
                        await message.channel.send("\n".join(lines))
                except Exception as e:
                    await message.channel.send(f"⚠️ 패턴 분석 실패: {e}")
                    print(f"[Bot] 패턴 분석 오류: {e}", flush=True)
            return

        # ── P2 자기 반성 ───────────────────────────────────────────────────────────
        if content in ("!성찰", "!reflect", "!자기반성"):
            async with message.channel.typing():
                try:
                    import sys as _sys
                    if str(Path(__file__).parent) not in _sys.path:
                        _sys.path.insert(0, str(Path(__file__).parent))
                    from bucky_self_reflection import run as run_reflection
                    await message.channel.send("💭 자기 반성 분석 시작...")
                    result = await asyncio.to_thread(run_reflection, False)
                    analysis = result.get("analysis", "")[:600]
                    await message.channel.send(f"**💭 자기 반성 완료**\n\n{analysis}")
                except Exception as e:
                    await message.channel.send(f"⚠️ 자기 반성 실패: {e}")
            return

        # ── Track A: 상품화 파이프라인 (랜딩 + 결제 + 배포 통합) ─────────────────
        # 사용법: !상품화 <github_url> [결제URL] [가격]
        if content.startswith("!상품화") or content.startswith("!commercialize"):
            parts = content.split(None, 3)
            if len(parts) < 2:
                await message.channel.send(
                    "**사용법**: `!상품화 <GitHub URL> [결제URL] [가격]`\n"
                    "예: `!상품화 https://github.com/user/repo https://buy.stripe.com/xxx ₩29,000/월`\n"
                    "_결제URL 생략 시 랜딩 페이지만 생성_"
                )
                return
            async with message.channel.typing():
                try:
                    _sys = __import__("sys")
                    _sys.path.insert(0, str(Path(__file__).parent))
                    from bucky_commercialize import run as commercialize_run
                    repo_url = parts[1]
                    pay_url = parts[2] if len(parts) > 2 else ""
                    price = parts[3] if len(parts) > 3 else "₩29,000/월"
                    await message.channel.send(f"🏭 **상품화 시작** — `{repo_url}`\n_랜딩 생성 → 결제 연동 → Vercel 배포_")
                    result = await asyncio.to_thread(commercialize_run, repo_url, pay_url, price)
                    name = result.get("config", {}).get("REPO_NAME", "?")
                    lines = [f"✅ **{name}** 상품화 완료!"]
                    if result.get("landing_path"):
                        lines.append(f"📄 랜딩: `{Path(result['landing_path']).name}`")
                    if result.get("url"):
                        lines.append(f"🌐 {result['url']}")
                    elif not result.get("deployed"):
                        lines.append("ℹ️ Vercel 배포 생략 (vercel CLI 필요: `npm i -g vercel`)")
                    await message.channel.send("\n".join(lines))
                except Exception as e:
                    await message.channel.send(f"❌ 상품화 실패: {e}")
                    print(f"[Bot] 상품화 오류: {e}", flush=True)
            return

        # ── 랜딩 페이지 생성 ────────────────────────────────────────────────────
        if content.startswith("!랜딩") or content.startswith("!landing"):
            arg = content.split(None, 1)[1].strip() if len(content.split(None, 1)) > 1 else ""
            async with message.channel.typing():
                try:
                    _sys = __import__("sys")
                    _sys.path.insert(0, str(Path(__file__).parent))
                    from bucky_landing_generator import generate, from_github_url
                    if arg.startswith("http"):
                        out = await asyncio.to_thread(from_github_url, arg)
                    else:
                        from bucky_landing_generator import DEFAULT_CONFIG
                        cfg = {**DEFAULT_CONFIG, "REPO_NAME": arg or "MyProduct", "LOGO_CHAR": (arg or "M")[0].upper()}
                        out = await asyncio.to_thread(generate, cfg, (arg or "product").lower())
                    await message.channel.send(f"✅ 랜딩 페이지 생성 완료!\n📄 `{out}`\n`!배포 {out}` 로 Vercel에 배포하세요.")
                except Exception as e:
                    await message.channel.send(f"⚠️ 랜딩 생성 실패: {e}")
            return

        # ── Vercel 배포 ──────────────────────────────────────────────────────────
        if content.startswith("!배포") or content.startswith("!deploy"):
            arg = content.split(None, 1)[1].strip() if len(content.split(None, 1)) > 1 else ""
            async with message.channel.typing():
                try:
                    _sys = __import__("sys")
                    _sys.path.insert(0, str(Path(__file__).parent))
                    from bucky_vercel_deploy import deploy, deploy_landing_page
                    if not arg:
                        await message.channel.send("⚠️ 사용법: `!배포 <프로젝트_경로_또는_이름>`")
                    elif arg.endswith(".html") and Path(arg).exists():
                        repo_name = Path(arg).stem
                        result = await asyncio.to_thread(deploy_landing_page, repo_name, Path(arg))
                    else:
                        result = await asyncio.to_thread(deploy, arg, "", True)
                    if result.get("success"):
                        await message.channel.send(f"✅ 배포 완료!\n🌐 {result.get('url', '')}")
                    else:
                        await message.channel.send(f"❌ 배포 실패: {result.get('error', '')[:300]}")
                except Exception as e:
                    await message.channel.send(f"⚠️ 배포 오류: {e}")
            return

        # ── 지식 저장 (Knowledge Capture) — YouTube 전용 처리 포함 ─────────────────
        if content.startswith("!저장") or content.startswith("!capture") or content.startswith("!캡처"):
            arg = content.split(None, 1)[1].strip() if len(content.split(None, 1)) > 1 else ""
            async with message.channel.typing():
                try:
                    _sys = __import__("sys")
                    _sys.path.insert(0, str(Path(__file__).parent))
                    if arg.startswith("http") and _YOUTUBE_PATTERN.search(arg):
                        await message.channel.send("📺 YouTube 영상 분석 중... (트랜스크립트 + AI 요약)")
                        from bucky_youtube_capture import capture_youtube
                        yt_result = await asyncio.to_thread(capture_youtube, arg)
                        if yt_result["success"]:
                            reply_lines = [
                                "✅ **YouTube 지식 저장 완료!**",
                                f"📝 {yt_result['title']}",
                                f"{'트랜스크립트 포함 ✅' if yt_result['has_transcript'] else '트랜스크립트 없음 ⚠️'}",
                            ]
                            if yt_result.get("summary"):
                                reply_lines.append(f"```\n{yt_result['summary'][:300]}\n```")
                            for chunk in split_message("\n".join(reply_lines)):
                                await message.channel.send(chunk)
                        else:
                            await message.channel.send(f"⚠️ YouTube 캡처 실패: {yt_result.get('error', '')}")
                    elif arg.startswith("http"):
                        from bucky_knowledge_capture import capture_url
                        result = await asyncio.to_thread(capture_url, arg)
                        await message.channel.send(f"✅ Obsidian 저장 완료!\n📝 `{result}`")
                    elif arg:
                        from bucky_knowledge_capture import capture_text
                        result = await asyncio.to_thread(capture_text, arg, message.author.name)
                        await message.channel.send(f"✅ Obsidian 저장 완료!\n📝 `{result}`")
                    else:
                        await message.channel.send("⚠️ 사용법: `!저장 <URL 또는 텍스트>`")
                        return
                except Exception as e:
                    await message.channel.send(f"⚠️ 저장 실패: {e}")
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

            # 음성 채널 TTS 재생 (입장 중인 경우)
            guild_id = getattr(message.guild, "id", None)
            if guild_id and VOICE_CHANNEL_ENABLED:
                vc = _voice_clients.get(guild_id)
                if vc and vc.is_connected():
                    asyncio.ensure_future(_tts_speak(vc, reply, guild_id))

            # Obsidian PC 채팅창에 동기화
            append_to_bucky_chat(message.author.name, content, reply)

            # 이미 답변했으므로 status=answered → dispatcher 재처리 방지
            out_path = write_discord_message(message, reply, status="answered")

            # 구현/리뷰 키워드 감지 시 task_tracker에 자동 등록
            try:
                from task_tracker import classify
                detected_type = classify(content)
                if detected_type in ("implementation_request", "review_request"):
                    await asyncio.to_thread(
                        add_task, content[:40], content, detected_type, "discord"
                    )
            except Exception:
                pass
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
