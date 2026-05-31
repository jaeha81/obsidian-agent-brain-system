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
    !queue    — AgentBus 큐 읽기 전용 점검
    !pack     — 작업별 최소 컨텍스트 팩 선택
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

# stdout/stderr 닫혀 있을 때(콘솔 없이 실행, 창 닫힘 등) print 크래시 방지
import io as _io
if sys.stdout is None or (hasattr(sys.stdout, "closed") and sys.stdout.closed):
    sys.stdout = _io.TextIOWrapper(_io.open(os.devnull, "wb"), encoding="utf-8", errors="replace")
if sys.stderr is None or (hasattr(sys.stderr, "closed") and sys.stderr.closed):
    sys.stderr = _io.TextIOWrapper(_io.open(os.devnull, "wb"), encoding="utf-8", errors="replace")
import builtins as _builtins
_unsafe_print = _builtins.print


def _safe_print(*args, **kwargs):
    try:
        return _unsafe_print(*args, **kwargs)
    except ValueError:
        fallback = sys.__stderr__
        if fallback is None or getattr(fallback, "closed", False):
            fallback = _io.TextIOWrapper(_io.open(os.devnull, "wb"), encoding="utf-8", errors="replace")
        kwargs["file"] = fallback
        try:
            return _unsafe_print(*args, **kwargs)
        except Exception:
            return None


_builtins.print = _safe_print
from datetime import datetime, timedelta
from pathlib import Path

import discord
import yaml
from discord import Intents, Message, app_commands
from dotenv import load_dotenv

import json as _json_mod
import subprocess as _subprocess_mod

from bucky_client import BuckyError, run_bucky
from bucky_briefing import generate_briefing
from task_tracker import add_task, format_task_list, get_today_tasks
from daily_report_generator import run as generate_daily_report
from bucky_dispatcher import dispatch as dispatch_task, get_pending_tasks
from bucky_multi_dispatcher import (
    parse_multi_tasks,
    is_multi_task,
    run_parallel,
    format_multi_result,
)

try:
    import task_queue as tq
    from bucky_worker_pool import get_pool as _get_worker_pool
    _WORKER_POOL_ENABLED = True
except ImportError:
    tq = None  # type: ignore
    _get_worker_pool = None  # type: ignore
    _WORKER_POOL_ENABLED = False

try:
    from bucky_knowledge_capture import capture_url as _kc_capture_url, capture_text as _kc_capture_text
    _KNOWLEDGE_CAPTURE_ENABLED = True
except ImportError:
    _KNOWLEDGE_CAPTURE_ENABLED = False

try:
    from bucky_pattern_extractor import run as _pattern_extractor_run
    _PATTERN_EXTRACTOR_ENABLED = True
except ImportError:
    _PATTERN_EXTRACTOR_ENABLED = False

try:
    from bucky_self_reflection import run as _self_reflection_run
    _SELF_REFLECTION_ENABLED = True
except ImportError:
    _SELF_REFLECTION_ENABLED = False

_ROOT = Path(__file__).parent.parent
load_dotenv(_ROOT / ".env", encoding="utf-8")

# Discord 봇은 Vault 파일 읽기·명령 실행이 필요 → 항상 auto(dangerously-skip-permissions)
os.environ.setdefault("BUCKY_TOOL_MODE", "auto")

# ── 자동 브리핑 스케줄 ─────────────────────────────────────────────────────────
AUTO_BRIEFING: bool = os.getenv("AUTO_BRIEFING", "0").strip().lower() in {"1", "true", "yes"}
BRIEFING_CHANNEL_ID: str = os.getenv("BRIEFING_CHANNEL_ID", "")
BRIEFING_TIME: str = os.getenv("BRIEFING_TIME", "09:00")  # HH:MM 로컬 시각
BUCKY_STATUS_CHANNEL_ID: str = os.getenv("BUCKY_STATUS_CHANNEL_ID", "").strip()

# ── JH 채널 체계 ───────────────────────────────────────────────────────────────
JH_CHAT_CHANNEL_ID: str    = os.getenv("JH_CHAT_CHANNEL_ID", "").strip()
JH_TASKS_CHANNEL_ID: str   = os.getenv("JH_TASKS_CHANNEL_ID", "").strip()
JH_STATUS_CHANNEL_ID: str  = os.getenv("JH_STATUS_CHANNEL_ID", "").strip()
JH_RESULTS_CHANNEL_ID: str = os.getenv("JH_RESULTS_CHANNEL_ID", "").strip()
# 작업 채널: 채널 = 독립 Claude Code 인스턴스 (tools 허용, 병렬 실행)
JH_WORK_CHANNEL_IDS: set[str] = {
    c.strip() for c in os.getenv("JH_WORK_CHANNEL_IDS", "").split(",") if c.strip()
}

# ── 환경변수 ───────────────────────────────────────────────────────────────────

TOKEN: str = os.getenv("DISCORD_BOT_TOKEN", "")
GUILD_ID: str = os.getenv("DISCORD_GUILD_ID", "")
ALLOWED_CHANNELS: set[str] = {
    c.strip() for c in os.getenv("DISCORD_CHANNEL_IDS", "").split(",") if c.strip()
} | JH_WORK_CHANNEL_IDS  # 작업 채널 자동 포함
VAULT = Path(os.getenv("VAULT_PATH", str(_ROOT / "ObsidianVault")))
INBOX = VAULT / "10_AgentBus" / "inbox"
MIN_LENGTH: int = int(os.getenv("DISCORD_MIN_LENGTH", "1"))
BUCKY_ENABLED: bool = os.getenv("BUCKY_ENABLED", "1").strip().lower() not in {"0", "false", "no"}
VOICE_ENABLED: bool = os.getenv("VOICE_ENABLED", "1").strip().lower() not in {"0", "false", "no"}
WHISPER_MODEL_NAME: str = os.getenv("WHISPER_MODEL", "small")
VOICE_CHANNEL_ENABLED: bool = os.getenv("VOICE_CHANNEL_ENABLED", "1").strip().lower() not in {"0", "false", "no"}
TTS_LANG: str = os.getenv("TTS_LANG", "ko")
VOICE_RECV_ENABLED: bool = os.getenv("VOICE_RECV_ENABLED", "1").strip().lower() not in {"0", "false", "no"}

# ── Windows libopus 자동 감지 및 로드 ──────────────────────────────────────────
def _try_load_opus() -> bool:
    """Windows에서 libopus DLL 자동 탐색 후 로드. 실패 시 False 반환."""
    import ctypes, glob as _glob
    candidates = [
        str(_ROOT / "opus.dll"),
        str(_ROOT / "libopus.dll"),
        "opus", "libopus",
        "opus-0", "libopus-0",
    ]
    # scripts 폴더 내 DLL도 탐색
    candidates += _glob.glob(str(_ROOT / "*.dll"))
    for name in candidates:
        try:
            discord.opus.load_opus(name)
            print(f"[Bot] libopus 로드 성공: {name}", flush=True)
            return True
        except Exception:
            pass
    print("[Bot] ⚠️ libopus 미발견 — 음성 채널 비활성화. opus.dll을 프로젝트 루트에 배치하세요.", flush=True)
    print("[Bot]   다운로드: https://github.com/xiph/opus/releases (Windows x64 binary)", flush=True)
    return False

if VOICE_CHANNEL_ENABLED and sys.platform == "win32" and not discord.opus.is_loaded():
    if not _try_load_opus():
        # opus DLL 없어도 PyAV + FFmpegOpusAudio로 동작 가능 — 비활성화하지 않음
        print("[Bot] libopus DLL 없음 — PyAV(수신) + FFmpegOpusAudio(TTS)로 대체 동작", flush=True)

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

# ── 동적 컨텍스트 로더 (BUCKY_CONTEXT.md, 5분 캐시) ─────────────────────────
_VAULT = Path(__file__).parent.parent / "ObsidianVault"
_CONTEXT_FILE = _VAULT / "00_System" / "BUCKY_CONTEXT.md"
_REQUIRED_CONTEXT_PACKS = [
    _VAULT / "06_Context_Packs" / "bucky-agent-os-legacy-rules.md",
    _VAULT / "06_Context_Packs" / "bucky-migration-build-charter.md",
    _VAULT / "06_Context_Packs" / "bucky-context-efficiency-goal-mode.md",
    _VAULT / "00_System" / "GDRIVE_SCRIPT_CLASSIFICATION_2026-05-30.md",
    _VAULT / "05_Frameworks" / "LegalizeKR" / "legalize_update_policy.md",
]
_CONTEXT_PACK_CHAR_LIMIT = int(os.getenv("BUCKY_CONTEXT_PACK_CHAR_LIMIT", "18000"))
_context_cache: dict = {"text": "", "loaded_at": 0.0}
_CONTEXT_TTL = 300  # 5분

def _read_required_context_packs() -> str:
    sections: list[str] = []
    remaining = _CONTEXT_PACK_CHAR_LIMIT
    for path in _REQUIRED_CONTEXT_PACKS:
        if remaining <= 0:
            break
        try:
            text = path.read_text(encoding="utf-8", errors="replace").strip()
        except Exception as exc:
            sections.append(f"## {path.name}\n\n[load failed: {exc}]")
            continue
        if not text:
            continue
        excerpt = text[:remaining]
        if len(text) > len(excerpt):
            excerpt += "\n\n[TRUNCATED: Context Pack char limit reached]"
        sections.append(f"## {path.name}\n\n{excerpt}")
        remaining -= len(excerpt)
    if not sections:
        return ""
    return "\n\n---\n\n# Bucky Required Context Packs\n\n" + "\n\n---\n\n".join(sections)

def _load_bucky_context() -> str:
    import time
    now = time.time()
    if now - _context_cache["loaded_at"] < _CONTEXT_TTL and _context_cache["text"]:
        return _context_cache["text"]
    try:
        text = _CONTEXT_FILE.read_text(encoding="utf-8")
        packs = _read_required_context_packs()
        if packs:
            text = f"{text}\n\n{packs}"
        _context_cache["text"] = text
        _context_cache["loaded_at"] = now
        return text
    except Exception:
        return BUCKY_SYSTEM_PROMPT

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

# ── 메시지 ID 중복 처리 방지 ─────────────────────────────────────────────────────
# 레이어 1: 인메모리 (같은 프로세스 내 재연결·이중 이벤트)
_processed_msg_ids: set[int] = set()
_PROCESSED_MSG_MAX = 500

# 레이어 2: 파일 기반 (프로세스 재시작 후 Discord RESUME, 다중 인스턴스)
_CLAIMS_DIR = INBOX.parent / "claims"
_CLAIM_TTL_SEC = 86400  # 24시간 후 claim 만료


def _claim_message(msg_id: int) -> bool:
    """메시지 처리권 선점. True=처리 진행, False=이미 처리됨(스킵).

    claim 파일을 message_id 기반으로 생성해 여러 인스턴스/재시작에 걸친 중복을 차단.
    """
    _CLAIMS_DIR.mkdir(parents=True, exist_ok=True)
    claim_file = _CLAIMS_DIR / f"{msg_id}.claim"

    # 만료된 claim 정리 (이 파일이 대상인 경우)
    try:
        if claim_file.exists():
            import time as _t
            if _t.time() - claim_file.stat().st_mtime > _CLAIM_TTL_SEC:
                claim_file.unlink(missing_ok=True)
            else:
                return False  # 유효한 claim 존재 → 스킵
    except Exception:
        pass

    try:
        # "x" 모드: 파일 없을 때만 생성 (원자적 선점)
        with open(str(claim_file), "x", encoding="utf-8") as f:
            import os as _os
            f.write(str(_os.getpid()))
        return True
    except FileExistsError:
        return False
    except Exception:
        return True  # 파일 시스템 오류 시 처리 허용 (안전 폴백)

# ── 채널별 활성 thinking 메시지 추적 (봇 재시작 후 잔여 메시지 정리용) ─────────
# key: channel_id(str), value: discord.Message object
_active_thinking_msgs: dict = {}  # channel_id -> discord.Message

# ── 유틸 ───────────────────────────────────────────────────────────────────────

_THINKING_STAGES = [
    (0,  "🔍 RAG 지식 검색 중"),
    (6,  "🧠 Claude 응답 생성 중"),
    (20, "📝 응답 마무리 중"),
    (60, "⏳ 복잡한 작업 처리 중"),
]


async def _animate_thinking(msg: "discord.Message", stop_event: "asyncio.Event") -> None:
    """thinking 메시지를 3초마다 단계·경과시간으로 업데이트한다."""
    elapsed = 0
    while not stop_event.is_set():
        await asyncio.sleep(3)
        if stop_event.is_set():
            break
        elapsed += 3
        label = _THINKING_STAGES[0][1]
        for threshold, stage_label in _THINKING_STAGES:
            if elapsed >= threshold:
                label = stage_label
        try:
            await msg.edit(content=f"{label}... _(⏱ {elapsed}초)_")
        except Exception:
            break


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
# CLI(구독) 있으면 API key 없어도 STT 고도화 활성
try:
    from bucky_client import is_bucky_available as _is_bucky_avail  # already imported above, re-import safe
    _CLI_AVAILABLE: bool = _is_bucky_avail()
except Exception:
    _CLI_AVAILABLE = False
_STT_ENHANCE_ENABLED: bool = (bool(_CLAUDE_API_KEY) or _CLI_AVAILABLE) and os.getenv("STT_AI_ENHANCE", "1").strip() not in {"0", "false", "no"}
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
    try:
        print("[Bot] STT 고도화 + NLP 전처리기 로드 완료", flush=True)
    except ValueError:
        pass
except Exception as _nlp_e:
    try:
        print(f"[Bot] STT/NLP 모듈 로드 실패 (기본 후처리 사용): {_nlp_e}", flush=True)
    except ValueError:
        pass


def _postprocess_stt(text: str) -> str:
    """Typeless 스타일 기본 후처리: 필러 제거 + 중복 공백 정리."""
    text = _FILLER_PATTERN.sub("", text)
    return _re.sub(r"\s{2,}", " ", text).strip()


def _postprocess_stt_claude(text: str) -> str:
    """STT 고도화 — bucky_stt_enhancer 우선, CLI(구독) 폴백, API 최후 폴백."""
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

    # 1순위: CLI (구독)
    if _CLI_AVAILABLE:
        try:
            refined = run_bucky(prompt, task_type="chat")
            if refined and len(refined) > 1:
                return refined.strip()
        except Exception as e:
            print(f"[STT] CLI 후처리 실패: {e}", flush=True)

    # 2순위: Anthropic API (key 있을 때만)
    if _CLAUDE_API_KEY:
        try:
            import urllib.request
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
            print(f"[STT] API 후처리 실패: {e}", flush=True)

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


def _oral_format(text: str) -> str:
    """마크다운 응답 → TTS 구어체 변환. 코드블록·표·헤더 제거, 문장 추출."""
    import re
    lines = text.splitlines()
    result = []
    in_code = False
    for line in lines:
        s = line.strip()
        if s.startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            continue
        if re.match(r"^[-=|#]{3,}$", s) or s.startswith("|"):
            continue
        s = re.sub(r"[*`#_~>]", "", s)
        s = re.sub(r"^[-*•]\s+", "", s)
        s = re.sub(r"^\d+\.\s+", "", s).strip()
        if s:
            result.append(s)
    combined = " ".join(result)
    if len(combined) > 220:
        snippet = combined[:220]
        last = max(snippet.rfind("다."), snippet.rfind("요."), snippet.rfind("요!"), snippet.rfind("니다."))
        if last > 60:
            combined = snippet[: last + 2]
        else:
            combined = snippet.rstrip() + "…"
    return combined.strip()


async def _tts_speak(vc: discord.VoiceClient, text: str, guild_id: int) -> None:
    """텍스트 → gTTS MP3 → FFmpegOpusAudio → 음성 채널 재생 (opus DLL 불필요)."""
    if not _gtts_available or not vc or not vc.is_connected():
        return
    clean = _oral_format(text)
    if not clean:
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
            loop = asyncio.get_running_loop()

            def _after(error):
                # done_event는 반드시 설정 (unlink 실패해도 락이 60초 점유하지 않도록)
                try:
                    Path(path_ref).unlink(missing_ok=True)
                except OSError:
                    # WinError 32: FFmpeg가 파일 사용 중 — 무시하고 계속
                    pass
                finally:
                    loop.call_soon_threadsafe(done_event.set)

            # FFmpegOpusAudio: ffmpeg이 opus 인코딩 담당 → libopus DLL 불필요
            audio_src = await discord.FFmpegOpusAudio.from_probe(tmp_path)
            vc.play(audio_src, after=_after)
            await asyncio.wait_for(done_event.wait(), timeout=60)
            tmp_path = None  # after callback이 삭제 담당
        except asyncio.TimeoutError:
            pass
        except Exception as e:
            print(f"[TTS] 재생 오류: {e}", flush=True)
        finally:
            if tmp_path:
                try:
                    Path(tmp_path).unlink(missing_ok=True)
                except OSError:
                    pass


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


# ── 음성 AgentBus 오케스트레이터 ────────────────────────────────────────────────

_VOICE_TASK_KEYWORDS = frozenset([
    "만들어", "구현", "작성", "코드", "개발", "추가", "삭제", "리팩토링",
    "검수", "리뷰", "오류", "버그", "디버그", "검증", "테스트", "점검",
    "배포", "실행", "수정", "고쳐", "바꿔", "변경",
])


def _is_voice_task(text: str) -> bool:
    return any(kw in text for kw in _VOICE_TASK_KEYWORDS)


def _write_voice_intake(text: str, display_name: str, guild_id: int, channel_id: str) -> None:
    """음성 텍스트를 AgentBus inbox에 voice_intake 파일로 기록."""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = re.sub(r"[^\w\-]", "_", display_name)
    fname = f"{ts}_voice_{safe_name[:20]}.md"
    INBOX.mkdir(parents=True, exist_ok=True)
    path = INBOX / fname
    path.write_text(
        f"---\n"
        f"type: voice_intake\n"
        f"source: discord_voice\n"
        f"author: {display_name}\n"
        f"guild_id: {guild_id}\n"
        f"channel_id: {channel_id}\n"
        f"status: answered\n"
        f"created: {datetime.now().isoformat()}\n"
        f"---\n\n{text}\n",
        encoding="utf-8",
    )
    print(f"[VoiceOrchestrator] AgentBus 기록: {fname}", flush=True)


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
            # True = raw opus frames (DLL 불필요), PyAV로 디코딩
            return True

        def write(self, user, data) -> None:  # type: ignore
            uid = user.id if user is not None else 0
            # wants_opus=True → data는 raw opus 패킷 bytes
            opus_pkt = bytes(data) if data else b""
            if not opus_pkt:
                return
            self._chunks[uid].append(opus_pkt)
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
            import av as _av  # PyAV — opus DLL 없이 디코딩
            wav_path = None
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                wav_path = f.name
            try:
                # raw opus 패킷 → PCM via PyAV (libopus DLL 불필요)
                codec_ctx = _av.CodecContext.create("libopus", "r")
                codec_ctx.sample_rate = 48000
                pcm_frames: list[bytes] = []
                for opus_pkt in chunks:
                    pkt = _av.Packet(opus_pkt)
                    for audio_frame in codec_ctx.decode(pkt):
                        pcm_frames.append(
                            audio_frame.to_ndarray(format="s16", layout="stereo").tobytes()
                        )
                pcm = b"".join(pcm_frames)
                if not pcm:
                    return
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

                # 음성 오케스트레이터: AgentBus inbox에 voice_intake 기록
                try:
                    _write_voice_intake(text, display_name, self.guild_id, str(ch.id))
                except Exception as _ve:
                    print(f"[VoiceOrchestrator] 기록 실패: {_ve}", flush=True)

                thinking_msg = await ch.send("🔍 RAG 지식 검색 중... _(⏱ 0초)_")
                _stop = asyncio.Event()
                _anim = asyncio.create_task(_animate_thinking(thinking_msg, _stop))
                try:
                    reply = await ask_bucky(str(self.guild_id), text)
                finally:
                    _stop.set()
                    _anim.cancel()
                voice_chunks = split_message(reply)
                await thinking_msg.edit(content=voice_chunks[0])
                for chunk in voice_chunks[1:]:
                    await ch.send(chunk)

                vc = _voice_clients.get(self.guild_id)
                if vc and vc.is_connected():
                    await _tts_speak(vc, reply, self.guild_id)

                # Obsidian voice-log 기록
                try:
                    from obsidian_voice_logger import logger as _vl
                    _vl.log_final(
                        {"text": text, "source": "discord_voice", "confidence": 0.0, "latency_ms": 0},
                        agent="bucky",
                        result={"status": "ok"},
                    )
                except Exception as _log_err:
                    print(f"[VoiceSink] Obsidian 로그 실패: {_log_err}", flush=True)
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


_RAG_SCRIPT = _ROOT / "scripts" / "vault_rag.py"

_SIMPLE_MSG_RE = _re.compile(
    r'^(안녕|ㅎㅇ|ㅋ+|ㅎ+|네|예|아니|맞아|ok|okay|hi|hello|thanks|고마워|감사|ㄴㄴ|응|어+|음+|그래|알겠|ㅇㅇ)',
    _re.IGNORECASE,
)


def _should_skip_rag(message: str) -> bool:
    """짧거나 단순한 메시지는 RAG 생략 — 응답 속도 1~3초 개선."""
    msg = message.strip()
    if len(msg) < 20:
        return True
    if _SIMPLE_MSG_RE.match(msg):
        return True
    return False


def _get_rag_context(query: str, top_k: int = 3) -> str:
    """vault_rag.py를 통해 쿼리와 관련된 Vault 지식을 가져온다."""
    if not _RAG_SCRIPT.exists():
        return ""
    try:
        result = _subprocess_mod.run(
            ["python", str(_RAG_SCRIPT), "search", query, "--top", str(top_k), "--json"],
            capture_output=True, text=True, encoding="utf-8", timeout=15,
            cwd=str(_ROOT),
        )
        if result.returncode != 0 or not result.stdout.strip():
            return ""
        hits = _json_mod.loads(result.stdout)
        if not hits:
            return ""
        lines = ["[Vault 관련 지식]"]
        for h in hits:
            sim = h.get("similarity", 0)
            if sim < 0.3:
                continue
            src = h.get("source", "")
            section = h.get("section", "")
            preview = h.get("preview", "")[:200]
            header = f"• {src}" + (f" > {section}" if section else "")
            lines.append(header)
            lines.append(f"  {preview}")
        return "\n".join(lines) if len(lines) > 1 else ""
    except Exception:
        return ""


async def ask_bucky(channel_id: str, user_message: str) -> str:
    """Bucky Agent에 질문하고 답변 반환. NLP 전처리 후 Claude CLI 구독 경로 사용."""
    try:
        import bucky_memory as _mem
        history = _mem.load_history(channel_id)
        _use_mem = True
    except Exception:
        history = conversation_history[channel_id]
        _use_mem = False

    # Item 1: NLP 전처리 — COMMAND 의도 감지 시 구조화 힌트 삽입
    nlp_hint = ""
    if _nlp_preprocess_fn and _NLP_ENABLED and len(user_message) > 5:
        try:
            nlp_result = _nlp_preprocess_fn(user_message)
            action = nlp_result.get("action", "")
            if action in ("BUILD", "DEPLOY", "FIX", "UPGRADE") and nlp_result.get("confidence", 0) >= 0.5:
                router = nlp_result.get("agent_router", "")
                target = nlp_result.get("target", "")
                nlp_hint = f"[NLP: {action}→{router} | 대상:{target}] "
        except Exception as _e:
            print(f"[NLP] 전처리 실패: {_e}", flush=True)

    enriched_message = nlp_hint + user_message if nlp_hint else user_message

    if _use_mem:
        await asyncio.to_thread(_mem.save_message, channel_id, "user", enriched_message)
        history.append({"role": "user", "content": enriched_message})
    else:
        history.append({"role": "user", "content": enriched_message})
        if len(history) > MAX_HISTORY:
            conversation_history[channel_id] = history[-MAX_HISTORY:]
            history = conversation_history[channel_id]

    transcript = "\n".join(
        f"{item['role'].title()}: {item['content']}" for item in history
    )

    # RAG: 단순 메시지는 생략, 지식 쿼리만 실행
    if _should_skip_rag(user_message):
        rag_block = ""
    else:
        rag_context = await asyncio.to_thread(_get_rag_context, user_message)
        rag_block = f"\n\n{rag_context}" if rag_context else ""

    bucky_context = _load_bucky_context()
    prompt = (
        "# Bucky 운영 컨텍스트\n\n"
        f"{bucky_context}\n\n"
        "---\n\n"
        "# Discord 대화\n\n"
        "위 컨텍스트를 기반으로 아래 대화에 답변한다. "
        "실행 작업이면 '요약→실행안→저장위치→다음행동' 순서로, 단순 질문이면 간결하게."
        f"{rag_block}\n\n"
        f"{transcript}"
    )
    # task_type='chat' → Sonnet (기본). 한도 초과 시 자동 Haiku→Opus 폴백
    reply = await asyncio.to_thread(run_bucky, prompt, task_type="chat")

    if _use_mem:
        await asyncio.to_thread(_mem.save_message, channel_id, "assistant", reply)
        # 5번째 교환마다 백그라운드 사실 추출
        total = len(history) + 1
        if total % 10 == 0:
            asyncio.ensure_future(_extract_and_learn(transcript + f"\nAssistant: {reply}"))
    else:
        history.append({"role": "assistant", "content": reply})

    return reply


async def _extract_and_learn(conversation: str) -> None:
    """대화에서 사실 추출 → BUCKY_CONTEXT 자동 기록 (백그라운드)."""
    try:
        import bucky_memory as _mem
        facts = await asyncio.to_thread(_mem.extract_facts, conversation)
        if facts:
            await asyncio.to_thread(_mem.save_facts, facts, "auto")
            await asyncio.to_thread(_mem.append_to_context, facts)
    except Exception as e:
        print(f"[Memory] 자동 학습 실패: {e}", flush=True)


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


# ── Wishket 모바일 대시보드 UI ────────────────────────────────────────────────

class WishketDashboardView(discord.ui.View):
    """공고 카드를 한 장씩 넘기며 지원 승인/건너뜀 선택 — 모바일 최적화."""

    def __init__(self, projects: list[dict], channel: discord.abc.Messageable) -> None:
        super().__init__(timeout=600)  # 10분
        self.projects = projects
        self.channel = channel
        self.idx = 0
        self._refresh_buttons()

    def _refresh_buttons(self) -> None:
        self.clear_items()
        if not self.projects:
            return
        p = self.projects[self.idx]

        apply_btn = discord.ui.Button(
            label=f"✅ 지원하기 ({self.idx + 1}/{len(self.projects)})",
            style=discord.ButtonStyle.success,
            custom_id="wk_apply",
        )
        apply_btn.callback = self._on_apply

        skip_btn = discord.ui.Button(
            label="⏭️ 건너뜀",
            style=discord.ButtonStyle.secondary,
            custom_id="wk_skip",
        )
        skip_btn.callback = self._on_skip

        link = p.get("link", "")
        if link and link.startswith("http"):
            link_btn = discord.ui.Button(
                label="🔗 공고 보기",
                style=discord.ButtonStyle.link,
                url=link,
            )
            self.add_item(link_btn)

        self.add_item(apply_btn)
        self.add_item(skip_btn)

    def _make_embed(self) -> discord.Embed:
        p = self.projects[self.idx]
        source_tag = "📧 Gmail" if p.get("source") == "gmail" else "🌐 Web"
        embed = discord.Embed(
            title=p["title"][:256],
            url=p.get("link") or discord.utils.MISSING,
            color=0x00B4D8,
        )
        embed.add_field(name="💰 예산", value=p.get("budget", "미정"), inline=True)
        embed.add_field(name="출처", value=source_tag, inline=True)
        if p.get("description"):
            embed.add_field(name="📝 요약", value=p["description"][:300], inline=False)
        embed.set_footer(text=f"{self.idx + 1} / {len(self.projects)}  |  Wishket 대시보드")
        return embed

    async def _on_apply(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(thinking=True)
        p = self.projects[self.idx]

        import sys as _sys
        if str(Path(__file__).parent) not in _sys.path:
            _sys.path.insert(0, str(Path(__file__).parent))

        try:
            from wishket_proposal_generator import generate_proposal_via_claude, save_proposal
            from bucky_wishket_agent import record_bid

            proposal_text = await asyncio.to_thread(generate_proposal_via_claude, p)
            proposal_path = await asyncio.to_thread(save_proposal, p, proposal_text)
            await asyncio.to_thread(record_bid, p, str(proposal_path))

            preview = proposal_text[:800] + "\n..." if len(proposal_text) > 800 else proposal_text
            await interaction.followup.send(
                f"✅ **제안서 생성 완료!**\n**{p['title']}** ({p.get('budget', '미정')})\n\n{preview}"
            )
        except Exception as e:
            await interaction.followup.send(f"⚠️ 제안서 생성 오류: {e}")

        self._advance()
        if self.projects:
            await interaction.message.edit(embed=self._make_embed(), view=self)
        else:
            await interaction.message.edit(content="✅ 모든 공고 검토 완료!", embed=None, view=None)

    async def _on_skip(self, interaction: discord.Interaction) -> None:
        self._advance()
        if self.projects:
            await interaction.response.edit_message(embed=self._make_embed(), view=self)
        else:
            await interaction.response.edit_message(content="✅ 모든 공고 검토 완료!", embed=None, view=None)

    def _advance(self) -> None:
        self.projects.pop(self.idx)
        if self.projects:
            self.idx = self.idx % len(self.projects)
            self._refresh_buttons()


# ── /wishket 슬래시 명령어 등록 ──────────────────────────────────────────────

def _register_wishket_commands(tree: app_commands.CommandTree) -> None:
    """/wishket · /wishket_stats · /wishket_won 등록."""
    import sys as _sys
    _sys.path.insert(0, str(Path(__file__).parent))

    @tree.command(name="wishket", description="Wishket 공고 스캔 (웹+Gmail) + 모바일 승인 대시보드")
    async def cmd_wishket(interaction: discord.Interaction) -> None:
        await interaction.response.defer(thinking=True)
        try:
            from bucky_wishket_agent import scan_projects, format_stats_message, get_stats

            projects = await asyncio.to_thread(scan_projects)

            if not projects:
                await interaction.followup.send(
                    "📭 새로운 공고 없음\n" + format_stats_message(get_stats())
                )
                return

            view = WishketDashboardView(list(projects), interaction.channel)
            msg = await interaction.followup.send(
                f"**Wishket 신규 공고 {len(projects)}개** — 카드를 넘기며 지원 여부를 결정하세요",
                embed=view._make_embed(),
                view=view,
            )
        except Exception as e:
            await interaction.followup.send(f"⚠️ Wishket 오류: {e}")
            print(f"[Wishket] 오류: {e}", flush=True)

    @tree.command(name="wishket_stats", description="Wishket 응찰 현황 및 누적 수익 조회")
    async def cmd_wishket_stats(interaction: discord.Interaction) -> None:
        await interaction.response.defer(thinking=True)
        try:
            from bucky_wishket_agent import get_stats, format_stats_message
            await interaction.followup.send(format_stats_message(get_stats()))
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
                await interaction.followup.send(
                    f"낙찰 기록 완료!\n**{project_title}** — {revenue_wan}만원\n\n"
                    + format_stats_message(get_stats())
                )
            else:
                await interaction.followup.send(f"⚠️ '{project_title}'에 해당하는 대기 중 공고를 찾지 못했습니다.")
        except Exception as e:
            await interaction.followup.send(f"⚠️ 낙찰 기록 오류: {e}")

    @tree.command(name="wishket_reply", description="이메일 자동응답 — 스캔/발송/취소/목록")
    @app_commands.describe(
        action="scan(스캔) | send(발송) | cancel(취소) | list(목록)",
        email_id="발송/취소 시 이메일 ID (send/cancel 시 필수)",
    )
    async def cmd_wishket_reply(
        interaction: discord.Interaction,
        action: str = "scan",
        email_id: str = "",
    ) -> None:
        await interaction.response.defer(thinking=True)
        import sys as _sys
        if str(Path(__file__).parent) not in _sys.path:
            _sys.path.insert(0, str(Path(__file__).parent))

        try:
            from wishket_email_responder import (
                run as responder_run,
                list_pending,
                send_reply_playwright,
                load_pending,
                save_pending,
            )

            if action == "scan":
                result = await asyncio.to_thread(responder_run)
                if result["count"] == 0:
                    await interaction.followup.send("📭 신규 클라이언트 이메일 없음")
                else:
                    await interaction.followup.send(
                        f"📨 **{result['count']}개** 클라이언트 이메일 감지 — 위에서 승인/취소하세요"
                    )

            elif action == "send":
                if not email_id:
                    await interaction.followup.send("⚠️ email_id 를 입력하세요")
                    return
                ok = await send_reply_playwright(email_id)
                await interaction.followup.send(
                    f"✅ 발송 완료: `{email_id}`" if ok else f"⚠️ 발송 실패: `{email_id}` — 수동 처리 필요"
                )

            elif action == "cancel":
                if not email_id:
                    await interaction.followup.send("⚠️ email_id 를 입력하세요")
                    return
                data = load_pending()
                before = len(data["pending"])
                data["pending"] = [r for r in data["pending"] if r["id"] != email_id]
                if len(data["pending"]) < before:
                    save_pending(data)
                    await interaction.followup.send(f"❌ 취소 완료: `{email_id}`")
                else:
                    await interaction.followup.send(f"⚠️ ID 없음: `{email_id}`")

            elif action == "list":
                data = load_pending()
                pending = data.get("pending", [])
                if not pending:
                    await interaction.followup.send("📭 대기 중인 초안 없음")
                else:
                    lines = [f"**대기 중 이메일 초안 {len(pending)}개:**"]
                    for r in pending[:10]:
                        lines.append(
                            f"• `{r['id']}` — **{r['subject'][:40]}** (from {r['sender'][:30]})"
                        )
                    await interaction.followup.send("\n".join(lines))

            else:
                await interaction.followup.send("⚠️ action: scan | send | cancel | list 중 선택")

        except Exception as e:
            await interaction.followup.send(f"⚠️ wishket_reply 오류: {e}")


# ── Codex 명령어 ──────────────────────────────────────────────────────────────

def _register_codex_commands(tree: app_commands.CommandTree) -> None:
    """Discord /codex_review — 지정 파일 또는 최근 커밋 변경 파일을 Codex가 검수."""

    codex_group = app_commands.Group(
        name="codex",
        description="Codex 코드 검수 명령어",
    )

    @codex_group.command(name="review", description="파일을 Codex로 검수 (비워두면 마지막 커밋 기준)")
    @app_commands.describe(files="검수할 파일 경로 (쉼표 구분). 비우면 마지막 커밋 자동 감지")
    async def codex_review(interaction: discord.Interaction, files: str = "") -> None:
        import subprocess as _sp
        await interaction.response.defer(thinking=True)
        try:
            target_files = [f.strip() for f in files.split(",") if f.strip()]
            if not target_files:
                r = await asyncio.to_thread(
                    _sp.run,
                    ["git", "diff", "--name-only", "HEAD~1", "HEAD", "--diff-filter=ACM"],
                    capture_output=True, text=True, cwd=str(ROOT),
                )
                exts = {".py", ".js", ".ts", ".jsx", ".tsx"}
                target_files = [f for f in r.stdout.strip().splitlines() if Path(f).suffix in exts]

            if not target_files:
                await interaction.followup.send("⚠️ 검수할 코드 파일 없음")
                return

            if len(target_files) > 10:
                await interaction.followup.send(f"⚠️ 파일이 {len(target_files)}개 — 10개 이하로 지정해 주세요")
                return

            await interaction.followup.send(f"🔍 Codex 검수 시작 — {len(target_files)}개 파일...")

            proc = await asyncio.to_thread(
                _sp.run,
                [sys.executable, str(ROOT / "scripts" / "codex_precommit.py")],
                capture_output=True, text=True,
                env={**os.environ, "CODEX_PRECOMMIT_FILES": ",".join(target_files)},
                cwd=str(ROOT),
            )
            output = (proc.stdout + proc.stderr).strip()[:1800] or "(출력 없음)"
            status = "❌ 차단" if proc.returncode != 0 else "✅ 통과"
            file_list = "\n".join(f"• `{f}`" for f in target_files)
            msg = f"**[Codex 검수 {status}]**\n{file_list}\n\n```\n{output}\n```"
            await interaction.followup.send(msg[:2000])
        except Exception as e:
            await interaction.followup.send(f"⚠️ codex review 오류: {e}")

    @codex_group.command(name="log", description="최근 Codex pre-commit 검수 로그 표시")
    async def codex_log(interaction: discord.Interaction) -> None:
        await interaction.response.defer(thinking=True)
        try:
            log_dir = ROOT / "ObsidianVault" / "10_AgentBus" / "codex-precommit-logs"
            if not log_dir.exists():
                await interaction.followup.send("📭 검수 로그 없음")
                return
            logs = sorted(log_dir.glob("*.md"), reverse=True)[:5]
            if not logs:
                await interaction.followup.send("📭 검수 로그 없음")
                return
            lines = ["**[Codex 검수 로그 — 최근 5건]**"]
            for log in logs:
                text = log.read_text(encoding="utf-8")[:300]
                status = "❌" if "BLOCK:" in text.upper() else ("⚠️" if "WARN:" in text.upper() else "✅")
                lines.append(f"{status} `{log.stem}`")
            await interaction.followup.send("\n".join(lines))
        except Exception as e:
            await interaction.followup.send(f"⚠️ log 조회 오류: {e}")

    tree.add_command(codex_group)


# ── /voice 슬래시 커맨드 ────────────────────────────────────────────────────────

def _register_voice_commands(tree: app_commands.CommandTree) -> None:
    """음성 채널 입/퇴장 및 상태 조회 슬래시 커맨드."""

    voice_group = app_commands.Group(name="voice", description="음성 채널 관리")

    @voice_group.command(name="join", description="Bucky를 현재 음성 채널(또는 지정 채널)에 입장시킵니다")
    @app_commands.describe(channel="입장할 음성 채널 (생략 시 사용자의 현재 채널)")
    async def cmd_voice_join(
        interaction: discord.Interaction,
        channel: discord.VoiceChannel | None = None,
    ) -> None:
        if not VOICE_CHANNEL_ENABLED:
            await interaction.response.send_message("⚠️ 음성 채널 기능이 비활성화되어 있습니다 (`VOICE_CHANNEL_ENABLED=0`).", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)

        # 채널 미지정 → 사용자의 현재 음성 채널 사용
        vc_channel = channel
        if vc_channel is None:
            member = interaction.guild.get_member(interaction.user.id) if interaction.guild else None
            if member and member.voice and member.voice.channel:
                vc_channel = member.voice.channel  # type: ignore[assignment]
            else:
                await interaction.followup.send("⚠️ 음성 채널에 먼저 입장하거나, 채널을 지정해 주세요.", ephemeral=True)
                return

        guild_id = interaction.guild_id or 0
        vc = await _join_voice_channel(vc_channel, interaction.channel, guild_id)
        if vc:
            await interaction.followup.send(f"✅ **{vc_channel.name}** 채널에 입장했습니다. 말씀하시면 Bucky가 응답합니다.", ephemeral=True)
        else:
            await interaction.followup.send("❌ 음성 채널 입장에 실패했습니다. 봇 권한 또는 opus/ffmpeg 설치를 확인하세요.", ephemeral=True)

    @voice_group.command(name="leave", description="Bucky를 음성 채널에서 퇴장시킵니다")
    async def cmd_voice_leave(interaction: discord.Interaction) -> None:
        guild_id = interaction.guild_id or 0
        if guild_id not in _voice_clients:
            await interaction.response.send_message("ℹ️ 현재 음성 채널에 연결되어 있지 않습니다.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        await _leave_voice_channel(guild_id)
        await interaction.followup.send("👋 음성 채널에서 퇴장했습니다.", ephemeral=True)

    @voice_group.command(name="status", description="현재 음성 채널 연결 상태를 확인합니다")
    async def cmd_voice_status(interaction: discord.Interaction) -> None:
        guild_id = interaction.guild_id or 0
        vc = _voice_clients.get(guild_id)
        lines = ["**[음성 채널 상태]**"]
        if vc and vc.is_connected():
            members_in_vc = [m.display_name for m in vc.channel.members if not m.bot]
            lines.append(f"🔊 채널: **{vc.channel.name}**")
            lines.append(f"🎤 참여자: {', '.join(members_in_vc) if members_in_vc else '없음'}")
            lines.append(f"📡 수신: {'✅ 활성' if _voice_recv else '⚠️ discord-ext-voice-recv 미설치'}")
            lines.append(f"🔉 TTS: {'✅ gTTS' if _gtts_available else '⚠️ gTTS 미설치'}")
            lines.append(f"🧠 Whisper: {'✅ ' + WHISPER_MODEL_NAME if VOICE_ENABLED else '⚠️ 미설치'}")
        else:
            lines.append("❌ 현재 음성 채널 미연결")
            lines.append(f"📡 수신 준비: {'✅' if _voice_recv else '⚠️ discord-ext-voice-recv 필요'}")
            lines.append("💡 `/voice join` 으로 입장하세요")
        await interaction.response.send_message("\n".join(lines))

    tree.add_command(voice_group)


# ── 현황판 초기화 헬퍼 ────────────────────────────────────────────────────────────

async def _init_status_board(client, pool) -> None:
    """#bucky-status 채널에서 현황판 메시지를 찾거나 새로 생성하고 pool에 등록."""
    if not BUCKY_STATUS_CHANNEL_ID:
        return
    try:
        ch = client.get_channel(int(BUCKY_STATUS_CHANNEL_ID))
        if not ch:
            return

        # 기존 핀 메시지 탐색 (봇이 보낸 것 중 "현황판" 키워드 포함)
        board_msg = None
        try:
            async for pin in ch.pins():
                if pin.author == client.user and "현황판" in pin.content:
                    board_msg = pin
                    break
        except Exception:
            pass

        # 기존 핀 없으면 최근 메시지에서 탐색
        if not board_msg:
            try:
                async for msg in ch.history(limit=20):
                    if msg.author == client.user and "현황판" in msg.content:
                        board_msg = msg
                        break
            except Exception:
                pass

        # 그래도 없으면 새 메시지 전송
        if not board_msg:
            board_msg = await ch.send(pool.get_board_text())
            try:
                await board_msg.pin()
            except Exception:
                pass

        pool.set_board_message(board_msg.id)
        print(f"[WorkerPool] 현황판 등록 완료: msg_id={board_msg.id}", flush=True)
    except Exception as e:
        print(f"[WorkerPool] 현황판 초기화 실패: {e}", flush=True)


def _persist_env_key(key: str, value: str) -> None:
    """.env 파일에 key=value 저장 (없으면 추가, 있으면 덮어씀)."""
    import re as _re
    env_path = _ROOT / ".env"
    if not env_path.exists():
        return
    try:
        content = env_path.read_text(encoding="utf-8")
        new_line = f"{key}={value}"
        if f"{key}=" in content:
            content = _re.sub(rf"^{key}=.*", new_line, content, flags=_re.MULTILINE)
        else:
            content = content.rstrip("\n") + f"\n{new_line}\n"
        env_path.write_text(content, encoding="utf-8")
        print(f"[Setup] .env 저장: {new_line}", flush=True)
    except Exception as e:
        print(f"[Setup] .env 저장 실패: {e}", flush=True)


async def _init_jh_channels(client) -> None:
    """jh-chat / jh-tasks / jh-status / jh-results / jh-work-* 채널 자동 생성."""
    global JH_CHAT_CHANNEL_ID, JH_TASKS_CHANNEL_ID, JH_STATUS_CHANNEL_ID, JH_RESULTS_CHANNEL_ID
    if not client.guilds:
        return
    guild = client.guilds[0]
    _specs = [
        ("jh-chat",    "JH_CHAT_CHANNEL_ID",    "💬 JH ↔ Bucky 대화 전용"),
        ("jh-tasks",   "JH_TASKS_CHANNEL_ID",   "📋 태스크 지시 전용 — Claude 없이 즉시 배정"),
        ("jh-status",  "JH_STATUS_CHANNEL_ID",  "📊 태스크 현황판 (자동 갱신)"),
        ("jh-results", "JH_RESULTS_CHANNEL_ID", "✅ 완료 결과 수신 · @멘션 알림"),
    ]
    _globals = globals()
    for ch_name, env_key, topic in _specs:
        if _globals[env_key]:
            continue
        existing = discord.utils.get(guild.text_channels, name=ch_name)
        if existing:
            _globals[env_key] = str(existing.id)
            print(f"[Setup] #{ch_name} 발견: {existing.id}", flush=True)
        else:
            try:
                new_ch = await guild.create_text_channel(ch_name, topic=topic)
                _globals[env_key] = str(new_ch.id)
                await new_ch.send(f"✅ **#{ch_name}** 자동 생성됨\n{topic}")
                print(f"[Setup] #{ch_name} 생성: {new_ch.id}", flush=True)
            except discord.Forbidden:
                print(f"[Setup] #{ch_name} 생성 실패: 권한 없음", flush=True)

    # ── 작업 채널 자동 생성 (jh-work-1, jh-work-2) ────────────────────────────
    _work_specs = [
        ("jh-work-1", "⚙️ Claude Code 작업 채널 1 — 독립 세션, 병렬 실행"),
        ("jh-work-2", "⚙️ Claude Code 작업 채널 2 — 독립 세션, 병렬 실행"),
    ]
    for ch_name, topic in _work_specs:
        existing = discord.utils.get(guild.text_channels, name=ch_name)
        if existing:
            ch_id = str(existing.id)
            if ch_id not in JH_WORK_CHANNEL_IDS:
                JH_WORK_CHANNEL_IDS.add(ch_id)
                ALLOWED_CHANNELS.add(ch_id)
            print(f"[Setup] #{ch_name} 발견: {existing.id}", flush=True)
        else:
            try:
                new_ch = await guild.create_text_channel(ch_name, topic=topic)
                ch_id = str(new_ch.id)
                JH_WORK_CHANNEL_IDS.add(ch_id)
                ALLOWED_CHANNELS.add(ch_id)
                await new_ch.send(
                    f"⚙️ **#{ch_name}** 자동 생성됨\n"
                    f"{topic}\n\n"
                    f"메시지를 보내면 독립 Claude Code 인스턴스가 실행됩니다.\n"
                    f"여러 작업 채널에서 동시에 병렬 작업이 가능합니다."
                )
                print(f"[Setup] #{ch_name} 생성: {new_ch.id}", flush=True)
            except discord.Forbidden:
                print(f"[Setup] #{ch_name} 생성 실패: 권한 없음", flush=True)

    # 작업 채널 ID .env 영구 저장 (재시작 시 유지)
    if JH_WORK_CHANNEL_IDS:
        _persist_env_key("JH_WORK_CHANNEL_IDS", ",".join(sorted(JH_WORK_CHANNEL_IDS)))

    # jh-status를 bucky-status 대신 현황판으로 사용
    if JH_STATUS_CHANNEL_ID and not BUCKY_STATUS_CHANNEL_ID:
        globals()["BUCKY_STATUS_CHANNEL_ID"] = JH_STATUS_CHANNEL_ID


async def _dispatch_task(message: Message, task_body: str) -> None:
    """태스크 단건 큐 투입 + 배정 확인 메시지."""
    task = tq.add(task_body[:80], task_body, source="jh-tasks")
    results_ch_id = int(JH_RESULTS_CHANNEL_ID) if JH_RESULTS_CHANNEL_ID else None
    pool = _get_worker_pool()
    pool.register_task(task, origin_channel_id=results_ch_id,
                       requester_id=int(message.author.id))
    pool.submit(task)
    _LABEL = {"claude": "🧠 Claude", "codex": "⚡ Codex", "bucky": "🤖 Bucky"}
    label = _LABEL.get(task["agent"], task["agent"].upper())
    results_hint = f" → <#{JH_RESULTS_CHANNEL_ID}>" if JH_RESULTS_CHANNEL_ID else ""
    await message.channel.send(
        f"✅ `{task['id'][-6:]}` {label} 배정 완료{results_hint}\n"
        f"> {task_body[:80]}{'...' if len(task_body) > 80 else ''}"
    )
    return task


async def _handle_jh_tasks(message: Message) -> None:
    """#jh-tasks 전용 핸들러 — Claude 거치지 않고 즉시 태스크 배정."""
    content = message.content.strip()

    # ── 현황 ──────────────────────────────────────────────────────────────────
    if content in ("!현황", "!status", "!tasks"):
        pool = _get_worker_pool()
        await message.channel.send(pool.get_board_text())
        return

    # ── 골모드: 목표 설정 ──────────────────────────────────────────────────────
    if content.startswith("!골 ") or content.startswith("!goal "):
        goal = content.split(None, 1)[1].strip()
        if not goal:
            await message.channel.send("사용법: `!골 <목표 설명>`")
            return
        thinking = await message.channel.send(f"🎯 **골모드 시작** — 목표 분석 중...\n> {goal}")
        try:
            import goal_tracker as gt
            subtasks = await asyncio.to_thread(gt.decompose, goal)
            data = gt.set_goal(goal, subtasks)
            lines = [f"🎯 **목표 설정 완료** — `{len(subtasks)}개 서브태스크` 자동 분해\n> {goal}\n"]
            results_ch_id = int(JH_RESULTS_CHANNEL_ID) if JH_RESULTS_CHANNEL_ID else None
            pool = _get_worker_pool()
            for st in data["subtasks"]:
                task = tq.add(st["body"][:80], st["body"], source="goal")
                st["task_id"] = task["id"]
                pool.register_task(task, origin_channel_id=results_ch_id,
                                   requester_id=int(message.author.id))
                pool.submit(task)
                _LABEL = {"claude": "🧠", "codex": "⚡", "bucky": "🤖"}
                icon = _LABEL.get(task["agent"], "▶")
                lines.append(f"{icon} `{task['id'][-6:]}` {st['body'][:60]}")
            gt.save(data)
            await thinking.edit(content="\n".join(lines))
        except Exception as e:
            await thinking.edit(content=f"⚠️ 골모드 오류: {e}")
        return

    # ── 골모드: 상태 확인 ─────────────────────────────────────────────────────
    if content in ("!골상태", "!골", "!goal"):
        try:
            import goal_tracker as gt
            await message.channel.send(gt.status_text())
        except Exception as e:
            await message.channel.send(f"⚠️ {e}")
        return

    # ── 골모드: 포커스 ON/OFF ─────────────────────────────────────────────────
    if content in ("!골포커스", "!focus"):
        try:
            import goal_tracker as gt
            current = gt.is_focus()
            gt.set_focus(not current)
            state = "ON 🎯 목표 외 태스크 거절" if not current else "OFF"
            await message.channel.send(f"포커스모드 {state}")
        except Exception as e:
            await message.channel.send(f"⚠️ {e}")
        return

    # ── 골모드: 목표 종료 ─────────────────────────────────────────────────────
    if content in ("!골종료", "!골완료"):
        try:
            import goal_tracker as gt
            data = gt.load()
            goal_name = data["goal"] if data else "없음"
            gt.clear()
            await message.channel.send(f"✅ 골모드 종료: `{goal_name}`")
        except Exception as e:
            await message.channel.send(f"⚠️ {e}")
        return

    # ── 일반 태스크 배정 ──────────────────────────────────────────────────────
    task_body = content.removeprefix("!task").strip() or content
    if not task_body:
        await message.channel.send("📋 태스크 내용을 입력하세요.\n예: `개발건 A — login API 구현`")
        return

    # 포커스 모드: 목표 연관도 체크
    try:
        import goal_tracker as gt
        if gt.is_focus():
            data = gt.load()
            goal = data["goal"] if data else ""
            goal_keywords = set(goal.lower().split())
            task_keywords = set(task_body.lower().split())
            if goal_keywords and not goal_keywords & task_keywords:
                await message.channel.send(
                    f"🎯 **포커스모드 ON** — 현재 목표와 무관한 태스크\n"
                    f"> 목표: {goal}\n"
                    f"`!골포커스` 로 포커스 해제 후 진행 가능"
                )
                return
    except Exception:
        pass

    await _dispatch_task(message, task_body)


# ── 작업 채널 핸들러 ─────────────────────────────────────────────────────────────

_WORK_SYSTEM_PROMPT = (
    "너는 Claude Code 작업 전용 에이전트다. "
    "이 채널은 독립 작업 세션이다 — 다른 채널과 컨텍스트를 공유하지 않는다. "
    "파일 읽기·쓰기·코드 실행 등 도구를 적극 활용해 작업을 완료한다. "
    "결과는 간결하게: 완료 항목 → 변경 파일 → 다음 행동 순서로 보고한다. "
    "불필요한 설명 없이 실행 결과 위주로 답변한다."
)


async def _handle_work_channel(message: Message) -> None:
    """작업 채널(jh-work-*) 핸들러.

    채널 = 독립 Claude Code 인스턴스. --dangerously-skip-permissions 적용.
    작업 추적: 저장 → 중복 감지 → 실행 → 결과 저장.
    """
    from bucky_client import run_bucky_with_tools, BuckyError as _BErr
    try:
        import channel_task_tracker as _ctt
        _track = True
    except ImportError:
        _ctt = None
        _track = False

    content = message.content.strip()
    if not content:
        return

    channel_id   = str(message.channel.id)
    channel_name = getattr(message.channel, "name", channel_id)

    # ── !명령어 처리 ───────────────────────────────────────────────────────────
    if content in ("!report", "!현황", "!보고"):
        if _track:
            await message.channel.send(_ctt.get_report())
        else:
            await message.channel.send("⚠️ 작업 추적 모듈 미설치")
        return

    if content in ("!history", "!기록"):
        if _track:
            await message.channel.send(_ctt.get_channel_history(channel_id))
        else:
            await message.channel.send("⚠️ 작업 추적 모듈 미설치")
        return

    if content.startswith("!플랜 ") or content.startswith("!plan "):
        plan_body = content.split(None, 1)[1].strip()
        if _track and plan_body:
            _ctt.mark_plan(channel_id, channel_name, plan_body)
            await message.channel.send(f"📐 플랜 저장: `{plan_body[:80]}`")
        return

    if content.startswith("!재개 ") or content.startswith("!resume "):
        resume_body = content.split(None, 1)[1].strip()
        if not resume_body:
            await message.channel.send("사용법: `!재개 [작업 내용 또는 이전 작업 설명]`")
            return
        # 재개 = 해당 내용으로 즉시 재실행 (content를 override)
        content = f"[재개] {resume_body}"

    # ── 중복 감지 ─────────────────────────────────────────────────────────────
    task_id = None
    if _track:
        dupes = _ctt.find_duplicates(content)
        if dupes:
            dupe_lines = "\n".join(
                f"  `#{d['channel']}` ({d['status']}) {d['content'][:50]}…"
                for d in dupes[:3]
            )
            await message.channel.send(
                f"⚠️ **유사 작업 감지** — 중복 가능성 있음:\n{dupe_lines}\n"
                f"계속 진행합니다."
            )
        task_id = _ctt.save_task(channel_id, channel_name, content)

    # ── Claude Code 실행 ──────────────────────────────────────────────────────
    custom_sp = os.getenv(f"JH_WORK_PROMPT_{channel_id}", "").strip()
    system_prompt = custom_sp or _WORK_SYSTEM_PROMPT

    # 이전 세션에서 남은 thinking 메시지 삭제
    _old_tm = _active_thinking_msgs.pop(channel_id, None)
    if _old_tm is not None:
        try:
            await _old_tm.delete()
        except Exception:
            pass

    thinking_msg = await message.channel.send(
        f"⚙️ **[{channel_name}]** 작업 실행 중... _(⏱ 0초)_"
    )
    _active_thinking_msgs[channel_id] = thinking_msg
    _stop = asyncio.Event()
    _anim = asyncio.create_task(_animate_thinking(thinking_msg, _stop))
    reply = ""
    status = "done"
    try:
        # 작업 채널: 코드/구현 작업이 주를 이룸 → task_type='code'
        reply = await asyncio.to_thread(
            run_bucky_with_tools, content, system_prompt=system_prompt, task_type="code"
        )
    except _BErr as e:
        reply = f"⚠️ 작업 실패: {e}"
        status = "failed"
        print(f"[WorkCh] BuckyError [{channel_name}]: {e}", flush=True)
    except Exception as e:
        reply = f"⚠️ 오류: {e}"
        status = "failed"
        print(f"[WorkCh] Error [{channel_name}]: {e}", flush=True)
    finally:
        _stop.set()
        _anim.cancel()
        _active_thinking_msgs.pop(channel_id, None)

    # ── 결과 저장 ─────────────────────────────────────────────────────────────
    if _track and task_id:
        result_summary = reply[:200] if reply else None
        _ctt.update_task(task_id, status, result_summary)

    chunks = split_message(reply)
    await thinking_msg.edit(content=chunks[0])
    for chunk in chunks[1:]:
        await message.channel.send(chunk)

    write_discord_message(message, reply, status="answered")


# ── 봇 클래스 ──────────────────────────────────────────────────────────────────

class BuckyDiscordBot(discord.Client):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._auto_joined: bool = False
        self.tree = app_commands.CommandTree(self)
        _register_evolve_commands(self.tree)
        _register_tasks_commands(self.tree)
        _register_deploy_commands(self.tree)
        _register_analyze_commands(self.tree)
        _register_wishket_commands(self.tree)
        _register_codex_commands(self.tree)
        _register_voice_commands(self.tree)

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
        """Wishket 공고 자동 스캔 + 모바일 승인 버튼 UI 전송."""
        await self.wait_until_ready()

        # profile에서 스캔 시각 및 주기 로드
        try:
            import yaml as _yaml
            _profile = _yaml.safe_load((_ROOT / "configs" / "wishket_profile.yaml").read_text(encoding="utf-8")) or {}
            _h = int(_profile.get("auto_scan_hour", 8))
            _m = int(_profile.get("auto_scan_minute", 30))
            # scan_interval_hours: 0 = 하루 1회(지정 시각), N = N시간마다 반복
            _interval_h = int(_profile.get("scan_interval_hours", 0))
        except Exception:
            _h, _m, _interval_h = 8, 30, 0

        if _interval_h > 0:
            # N시간 간격 반복 모드 — 즉시 첫 실행 후 반복
            wait_sec = 0.0
            interval_sec = float(_interval_h * 3600)
            print(f"[WishketAuto] 인터벌 모드: {_interval_h}시간 간격 스캔", flush=True)
        else:
            # 하루 1회 지정 시각 모드
            now = datetime.now()
            next_run = now.replace(hour=_h, minute=_m, second=0, microsecond=0)
            if next_run <= now:
                next_run += timedelta(days=1)
            wait_sec = (next_run - datetime.now()).total_seconds()
            interval_sec = float(3600 * 24)
            print(f"[WishketAuto] 1일 1회 모드 — 다음 스캔: {next_run.strftime('%Y-%m-%d %H:%M')}", flush=True)

        await asyncio.sleep(wait_sec)

        while not self.is_closed():
            try:
                import sys as _sys
                if str(_ROOT / "scripts") not in _sys.path:
                    _sys.path.insert(0, str(_ROOT / "scripts"))
                from bucky_wishket_agent import scan_projects, format_stats_message, get_stats

                projects = await asyncio.to_thread(scan_projects)

                if BRIEFING_CHANNEL_ID:
                    channel = self.get_channel(int(BRIEFING_CHANNEL_ID))
                    if channel and projects:
                        # 버튼 UI로 전송 — 모바일에서 즉시 승인 가능
                        view = WishketDashboardView(list(projects), channel)
                        embed = view._make_embed()
                        stats = get_stats()
                        header = (
                            f"💰 **[Wishket 자동 스캔]** {len(projects)}개 신규 공고!\n"
                            f"{format_stats_message(stats)}"
                        )
                        await channel.send(header[:1000], embed=embed, view=view)
                        print(f"[WishketAuto] {len(projects)}개 공고 → 버튼 UI 발송", flush=True)
                    elif channel:
                        await channel.send("📭 **[Wishket]** 새 공고 없음")
            except Exception as e:
                print(f"[WishketAuto] 오류: {e}", flush=True)

            # 공고 스캔 후 클라이언트 이메일 응답도 함께 스캔
            try:
                from wishket_email_responder import run as email_responder_run
                email_result = await asyncio.to_thread(email_responder_run)
                if email_result.get("count", 0) > 0:
                    print(f"[WishketAuto] 클라이언트 이메일 {email_result['count']}개 감지 → Discord 승인 요청 게시", flush=True)
            except Exception as e:
                print(f"[WishketAuto] 이메일 응답 스캔 오류: {e}", flush=True)

            await asyncio.sleep(interval_sec)

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

    async def on_disconnect(self) -> None:
        print("[Bot] Discord 연결 끊김 — 재연결 대기 중...", flush=True)
        # 음성 클라이언트 상태 정리 (끊김 시 VoiceClient가 무효화됨)
        for guild_id in list(_voice_clients.keys()):
            vc = _voice_clients.get(guild_id)
            if vc and not vc.is_connected():
                _voice_clients.pop(guild_id, None)
                _voice_text_ch.pop(guild_id, None)

    async def on_resumed(self) -> None:
        print("[Bot] Discord 재연결 완료 (resumed)", flush=True)
        # WorkerPool Discord 인스턴스 재등록
        if _WORKER_POOL_ENABLED:
            try:
                pool = _get_worker_pool()
                pool.set_discord(self)
            except Exception as e:
                print(f"[Bot] 재연결 후 WorkerPool 재등록 실패: {e}", flush=True)
        # 알림 채널에 재연결 고지
        notify_ch_id = BUCKY_STATUS_CHANNEL_ID or JH_CHAT_CHANNEL_ID
        if notify_ch_id:
            try:
                ch = self.get_channel(int(notify_ch_id))
                if ch:
                    await ch.send("🔄 Discord 재연결 완료 — 봇이 정상 동작합니다.")
            except Exception as e:
                print(f"[Bot] 재연결 알림 실패: {e}", flush=True)

    async def on_ready(self) -> None:
        guilds = [f"{g.name}({g.id})" for g in self.guilds]
        mode = "Bucky Agent (구독)" if BUCKY_ENABLED else "inbox-only"
        user_count = len(_ALLOWED_USER_IDS) if _ALLOWED_USER_IDS else "전체 허용"
        voice_status = f"ON ({WHISPER_MODEL_NAME})" if VOICE_ENABLED else "OFF"
        tts_status = f"ON ({TTS_LANG})" if _gtts_available else "OFF"
        recv_status = "ON" if _voice_recv else "OFF"
        try:
            from pc_identity import print_identity
            print_identity()
        except ImportError:
            pass
        print(f"Bot ready: {self.user} [{mode}]", flush=True)
        print(f"Guilds joined: {guilds}", flush=True)
        print(f"Watching channels: {ALLOWED_CHANNELS or 'ALL'}", flush=True)
        print(f"Inbox: {INBOX}", flush=True)
        print(f"허용 사용자: {user_count}", flush=True)
        print(f"음성(Whisper STT): {voice_status}", flush=True)
        print(f"음성(TTS 출력): {tts_status}", flush=True)
        print(f"음성(실시간 수신): {recv_status}", flush=True)

        # ── #bucky-status 채널 자동 생성 ──────────────────────────────────────────
        global BUCKY_STATUS_CHANNEL_ID
        if not BUCKY_STATUS_CHANNEL_ID and self.guilds:
            guild = self.guilds[0]
            existing = discord.utils.get(guild.text_channels, name="bucky-status")
            if existing:
                BUCKY_STATUS_CHANNEL_ID = str(existing.id)
                print(f"[Setup] #bucky-status 채널 발견: {existing.id}", flush=True)
            else:
                try:
                    new_ch = await guild.create_text_channel(
                        "bucky-status",
                        topic="🤖 Bucky 태스크 현황판 — 자동 생성됨",
                        reason="Bucky WorkerPool 상태 채널 자동 생성",
                    )
                    BUCKY_STATUS_CHANNEL_ID = str(new_ch.id)
                    await new_ch.send(
                        "🤖 **Bucky 상태 채널 자동 생성 완료**\n"
                        "이 채널에서 모든 태스크 현황을 실시간 추적합니다.\n"
                        "`.env`에 `BUCKY_STATUS_CHANNEL_ID=" + str(new_ch.id) + "` 추가를 권장합니다."
                    )
                    print(f"[Setup] #bucky-status 채널 생성: {new_ch.id}", flush=True)
                except discord.Forbidden:
                    print("[Setup] #bucky-status 채널 생성 실패: 권한 없음", flush=True)

        # ── JH 채널 자동 생성 ─────────────────────────────────────────────────────
        await _init_jh_channels(self)

        # ── 워커풀 초기화 ─────────────────────────────────────────────────────────
        if _WORKER_POOL_ENABLED:
            pool = _get_worker_pool()
            pool.set_discord(self)
            pool.hydrate_from_db()
            if JH_RESULTS_CHANNEL_ID:
                pool.set_results_channel(JH_RESULTS_CHANNEL_ID)
            pool.start_codex_result_poller()
            pool_size = int(os.getenv("WORKER_POOL_SIZE", "5"))
            status_ch = f"채널 {BUCKY_STATUS_CHANNEL_ID}" if BUCKY_STATUS_CHANNEL_ID else "미설정"
            print(f"[WorkerPool] 초기화 완료: 최대 {pool_size}개 동시 실행 | 상태채널: {status_ch}", flush=True)
            _board_task = asyncio.create_task(_init_status_board(self, pool))
            _board_task.add_done_callback(
                lambda t: print(f"[WorkerPool] 현황판 초기화 태스크 예외: {t.exception()}", flush=True)
                if not t.cancelled() and t.exception() else None
            )

        # ── 자동 음성 채널 입장 (AUTO_JOIN_VOICE_CHANNEL_ID 설정 시) ──────────────
        auto_join_ch_id = os.getenv("AUTO_JOIN_VOICE_CHANNEL_ID", "").strip()
        auto_join_text_ch_id = os.getenv("AUTO_JOIN_TEXT_CHANNEL_ID", "").strip()
        if auto_join_ch_id and VOICE_CHANNEL_ENABLED and not self._auto_joined:
            await asyncio.sleep(2)  # 게이트웨이 안정화 대기
            try:
                vc_channel = self.get_channel(int(auto_join_ch_id))
                text_channel = self.get_channel(int(auto_join_text_ch_id)) if auto_join_text_ch_id else None
                if vc_channel and isinstance(vc_channel, discord.VoiceChannel):
                    guild_id = vc_channel.guild.id
                    await _join_voice_channel(vc_channel, text_channel, guild_id)
                    self._auto_joined = True
                    print(f"[Voice] 자동 입장: {vc_channel.name}", flush=True)
                    if text_channel:
                        await text_channel.send(f"🎙️ `{vc_channel.name}` 음성 채널에 자동 입장했습니다. 말씀하세요!")
            except Exception as e:
                print(f"[Voice] 자동 입장 실패: {e}", flush=True)

        # ── 시작 시 미완료 작업 보고 ───────────────────────────────────────────────
        asyncio.ensure_future(self._startup_incomplete_report())

    async def _startup_incomplete_report(self) -> None:
        """봇 시작 시 미완료 작업이 있으면 #jh-status 또는 #jh-chat에 자동 보고."""
        await asyncio.sleep(3)  # 채널 초기화 대기
        try:
            import channel_task_tracker as _ctt
            report = _ctt.get_report(days=7)
            # 미완료 있을 때만 포스팅
            if "미완료 **0**" in report or "작업 없음" in report:
                return
            notify_ch_id = BUCKY_STATUS_CHANNEL_ID or JH_CHAT_CHANNEL_ID
            if not notify_ch_id:
                return
            ch = self.get_channel(int(notify_ch_id))
            if ch:
                await ch.send(
                    f"🔔 **봇 재시작 — 미완료 작업 있음**\n{report}\n\n"
                    f"`!재개 [작업내용]` 으로 재실행 가능"
                )
        except Exception as e:
            print(f"[Startup] 미완료 보고 실패: {e}", flush=True)

    async def on_message(self, message: Message) -> None:
        if message.author == self.user:
            return
        if GUILD_ID and str(getattr(message.guild, "id", "")) != GUILD_ID:
            return
        if ALLOWED_CHANNELS and str(message.channel.id) not in ALLOWED_CHANNELS:
            return

        # ── 중복 처리 방지 (레이어 1: 인메모리) ────────────────────────────────────
        if message.id in _processed_msg_ids:
            print(f"[Bot] Duplicate skipped (in-memory): msg_id={message.id}", flush=True)
            return
        _processed_msg_ids.add(message.id)
        if len(_processed_msg_ids) > _PROCESSED_MSG_MAX:
            _processed_msg_ids.clear()
            _processed_msg_ids.add(message.id)

        # ── 중복 처리 방지 (레이어 2: 파일 기반 — 재시작·다중 인스턴스) ────────────
        if not _claim_message(message.id):
            print(f"[Bot] Duplicate skipped (claim file): msg_id={message.id}", flush=True)
            return

        author_id = str(message.author.id)
        # 웹훅/Discord 앱(봇)은 서버 관리자가 설정한 신뢰된 소스이므로 자동 허용
        is_webhook = bool(getattr(message, "webhook_id", None))
        is_bot_app = getattr(message.author, "bot", False)
        if not _is_user_allowed(author_id) and not is_webhook and not is_bot_app:
            print(f"[Bot] 접근 차단: {message.author.name} (ID: {author_id})", flush=True)
            await message.channel.send(
                f"⛔ `{message.author.name}` — 접근 권한이 없습니다.\n"
                f"관리자가 이 ID를 `discord_users.yaml`에 추가해야 합니다: `{author_id}`"
            )
            return

        content = message.content.strip()
        channel_id = str(message.channel.id)

        # ── Sync Sentinel — PC/스토리지/Git/Docker 상태 확인 ─────────────────────
        if content in ("!sync", "!pc", "!sync-status", "!pc-status", "!동기화상태", "!PC상태"):
            try:
                from sync_sentinel import build_report as _sync_report, format_text as _sync_text
                report = await asyncio.to_thread(_sync_report)
                for chunk in split_message(_sync_text(report)):
                    await message.channel.send(chunk)
            except Exception as _sync_e:
                await message.channel.send(f"⚠️ Sync Sentinel 실패: {_sync_e}")
            return

        # ── AgentBus Queue Audit — 읽기 전용 큐 상태 확인 ─────────────────────────
        if content in ("!queue", "!agentbus", "!agentbus-audit", "!큐", "!버스", "!큐상태"):
            try:
                from agentbus_queue_audit import audit_agentbus as _queue_audit, format_text as _queue_text
                report = await asyncio.to_thread(_queue_audit)
                for chunk in split_message(_queue_text(report)):
                    await message.channel.send(chunk)
            except Exception as _queue_e:
                await message.channel.send(f"⚠️ AgentBus Queue Audit 실패: {_queue_e}")
            return

        # ── Context Pack Selector — 읽기 전용 최소 컨텍스트 선택 ───────────────────
        context_pack_prefixes = ("!context-pack", "!pack", "!컨텍스트팩", "!팩")
        matched_context_pack_prefix = next(
            (
                prefix
                for prefix in context_pack_prefixes
                if content == prefix or content.startswith(f"{prefix} ")
            ),
            None,
        )
        if matched_context_pack_prefix:
            body = content[len(matched_context_pack_prefix):].strip()
            try:
                from context_pack_selector import format_text as _context_pack_text
                from context_pack_selector import select_context_pack as _context_pack_select
                selection = await asyncio.to_thread(
                    _context_pack_select,
                    task_type="general",
                    body=body,
                )
                for chunk in split_message(_context_pack_text(selection)):
                    await message.channel.send(chunk)
            except Exception as _context_pack_e:
                await message.channel.send(f"⚠️ Context Pack Selector 실패: {_context_pack_e}")
            return

        # ── 전역 !report / !현황 — 모든 채널에서 사용 가능 ───────────────────────────
        if content in ("!report", "!현황", "!보고"):
            try:
                import channel_task_tracker as _ctt
                await message.channel.send(_ctt.get_report())
            except Exception as _rpt_e:
                await message.channel.send(f"⚠️ 보고 실패: {_rpt_e}")
            return

        # ── #jh-tasks: Claude 없이 즉시 태스크 배정 ─────────────────────────────────
        if JH_TASKS_CHANNEL_ID and channel_id == JH_TASKS_CHANNEL_ID:
            await _handle_jh_tasks(message)
            return

        # ── 작업 채널: 독립 Claude Code 인스턴스 (tools 허용, 진짜 병렬) ─────────────
        if JH_WORK_CHANNEL_IDS and channel_id in JH_WORK_CHANNEL_IDS:
            await _handle_work_channel(message)
            return

        # ── URL 자동 캡처 — YouTube는 알림 포함, 일반 URL은 조용히 처리 ──────────────
        if content and not content.startswith("!") and not content.startswith("/"):
            urls = _URL_PATTERN.findall(content)
            for url in urls:
                is_yt = bool(_YOUTUBE_PATTERN.search(url))
                notify_ch = message.channel if is_yt else None
                asyncio.ensure_future(_auto_capture_url_bg(url, notify_ch))

        # ── 음성 첨부파일 처리 + NLP 전처리 ───────────────────────────────────────
        _AUDIO_EXTS = {".ogg", ".mp3", ".wav", ".m4a", ".webm", ".aac", ".flac"}
        _is_native_voice = bool(getattr(getattr(message, "flags", None), "voice_message", False))
        if VOICE_ENABLED and message.attachments:
            for att in message.attachments:
                _is_audio = (
                    (att.content_type and att.content_type.startswith("audio/"))
                    or Path(att.filename).suffix.lower() in _AUDIO_EXTS
                )
                if _is_audio:
                    _voice_label = "🎙️ 음성 메시지" if _is_native_voice else "🎙️ 음성 파일"
                    async with message.channel.typing():
                        try:
                            transcript = await transcribe_discord_audio(att)
                            if transcript:
                                # NLP 전처리 — 음성 명령 구조화
                                # (인식 echo는 Bucky 응답 앞에 포함 — 별도 메시지 X)
                                if _NLP_ENABLED:
                                    try:
                                        import sys as _sys
                                        if str(Path(__file__).parent) not in _sys.path:
                                            _sys.path.insert(0, str(Path(__file__).parent))
                                        from bucky_nlp_preprocessor import preprocess, format_for_discord as _nlp_fmt
                                        nlp_result = await asyncio.to_thread(preprocess, transcript)
                                        if False:  # NLP 포맷 Discord 전송 비활성화 (중복 메시지 방지)
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

        # ── 이미지 첨부파일 처리 (Vision 분석 → Obsidian 저장) ─────────────────────
        if message.attachments:
            try:
                import sys as _sys
                if str(Path(__file__).parent) not in _sys.path:
                    _sys.path.insert(0, str(Path(__file__).parent))
                from discord_vision_processor import process_image_attachment, is_image_attachment
                image_atts = [a for a in message.attachments if is_image_attachment(a)]
            except ImportError as _ve:
                image_atts = []
                print(f"[Vision] 모듈 로드 실패: {_ve}", flush=True)

            if image_atts:
                async with message.channel.typing():
                    channel_name = getattr(message.channel, "name", channel_id)
                    author_name = message.author.name
                    summaries = []
                    for att in image_atts[:20]:  # 최대 20장
                        try:
                            vr = await process_image_attachment(att, content, channel_name, author_name)
                            if vr["ok"]:
                                summaries.append(vr["summary"])
                                print(f"[Vision] 저장 완료: {vr['vault_path']}", flush=True)
                            else:
                                print(f"[Vision] 처리 실패: {vr['error']}", flush=True)
                        except Exception as _img_err:
                            print(f"[Vision] 처리 오류: {_img_err}", flush=True)

                    if summaries:
                        # 이미지 요약을 Bucky 대화 컨텍스트에 포함
                        img_context = "\n".join(f"[이미지 {i+1}] {s}" for i, s in enumerate(summaries))
                        if content:
                            content = f"{content}\n\n{img_context}"
                        else:
                            content = f"[이미지 첨부]\n{img_context}"
                        await message.channel.send(
                            f"📸 **이미지 {len(summaries)}장 분석 완료** — Obsidian 저장 완료\n"
                            f">{summaries[0][:120]}{'...' if len(summaries[0]) > 120 else ''}"
                        )
                    elif image_atts:
                        # Vision 백엔드 없음 — 사용자에게 즉시 고지
                        await message.channel.send(
                            "⚠️ **사진 인식 불가** — Vision 백엔드가 없습니다.\n"
                            "원인: Claude API 크레딧 부족 / OpenAI 할당량 초과 / Tesseract 미설치\n"
                            "해결: `pip install pytesseract pillow` + Tesseract 바이너리 설치 후 봇 재시작"
                        )
                        urls_txt = "\n".join(a.url for a in image_atts)
                        content = f"{content}\n[이미지 첨부 — Vision 분석 불가]\n{urls_txt}" if content else f"[이미지 첨부]\n{urls_txt}"

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
                "`!queue` / `!agentbus` / `!큐상태` — AgentBus 큐 읽기 전용 점검\n"
                "`!context-pack <내용>` / `!pack <내용>` / `!팩 <내용>` — 최소 컨텍스트 팩 선택\n"
                "**[멀티태스크 — 워커풀]**\n"
                "`!task <내용>` — 자동 라우팅 (Claude/Codex/Bucky) 백그라운드 실행\n"
                "`!code <내용>` — Codex 강제 배정 (구현/코드 작업)\n"
                "`!think <내용>` — Claude 강제 배정 (분석/설계/전략)\n"
                "`!tasks` / `!태스크` / `!현황` — 오늘 태스크 전체 현황\n"
                "`!status T001` — 특정 태스크 상세 조회\n"
                "`!태스크추가 <내용>` — 태스크 등록 및 배분 (레거시)\n"
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
                "`!capture <url>` / `!저장 <url>` — URL/텍스트를 Obsidian 01_RAW에 저장\n"
                "`!캡처 <텍스트>` — 텍스트 메모 Obsidian 01_RAW에 저장\n"
                "`!patterns` / `!패턴` — 반복 패턴 분석 → 스킬 자동 제안 (P1)\n"
                "`!reflect` / `!반성` — 자기 반성 분석 (P2)\n"
                f"`!입장` / `!join` — 내가 있는 음성 채널 입장 ({vc_status})\n"
                f"`!퇴장` / `!leave` — 음성 채널 퇴장\n"
                f"TTS: {tts_status} | 실시간 수신: {recv_status}\n"
                "`!help` — 도움말\n"
                "_그 외 메시지는 Bucky가 답변합니다._"
            )
            return

        if content == "!reset":
            conversation_history[channel_id].clear()
            try:
                import bucky_memory as _mem
                await asyncio.to_thread(_mem.clear_history, channel_id)
            except Exception:
                pass
            await message.channel.send("🔄 대화 기록을 초기화했습니다.")
            return

        # ── P0: Knowledge Capture ──────────────────────────────────────
        if content.startswith("!capture ") or content.startswith("!저장 "):
            if not _KNOWLEDGE_CAPTURE_ENABLED:
                await message.channel.send("⚠️ knowledge capture 모듈 없음")
                return
            prefix = "!capture " if content.startswith("!capture ") else "!저장 "
            target = content[len(prefix):].strip()
            async with message.channel.typing():
                try:
                    loop = asyncio.get_event_loop()
                    if target.startswith("http"):
                        fp = await loop.run_in_executor(None, lambda: _kc_capture_url(target))
                    else:
                        fp = await loop.run_in_executor(None, lambda: _kc_capture_text(target, message.author.name))
                    await message.channel.send(f"✅ 저장 완료: `{fp.name}`\n📁 `ObsidianVault/01_RAW/`")
                except Exception as e:
                    await message.channel.send(f"❌ 저장 실패: {e}")
            return

        if content.startswith("!캡처 "):
            if not _KNOWLEDGE_CAPTURE_ENABLED:
                await message.channel.send("⚠️ knowledge capture 모듈 없음")
                return
            text_body = content[4:].strip()
            async with message.channel.typing():
                try:
                    loop = asyncio.get_event_loop()
                    fp = await loop.run_in_executor(None, lambda: _kc_capture_text(text_body, message.author.name))
                    await message.channel.send(f"✅ 메모 저장: `{fp.name}`")
                except Exception as e:
                    await message.channel.send(f"❌ 저장 실패: {e}")
            return

        # ── P1: Pattern Extractor ──────────────────────────────────────
        if content in ("!patterns", "!패턴"):
            if not _PATTERN_EXTRACTOR_ENABLED:
                await message.channel.send("⚠️ pattern extractor 모듈 없음")
                return
            await message.channel.send("🔍 패턴 분석 시작... (30초 내외)")
            async with message.channel.typing():
                try:
                    loop = asyncio.get_event_loop()
                    result = await loop.run_in_executor(None, lambda: _pattern_extractor_run(notify_discord=False))
                    patterns = result.get("patterns", [])
                    suggestions = result.get("suggestions", [])
                    lines = [f"📊 **패턴 분석 완료**", f"• 감지된 패턴: {len(patterns)}개", f"• 스킬 제안: {len(suggestions)}개"]
                    if patterns:
                        top = patterns[0]
                        lines.append(f"🥇 최다: `{top['pattern_key'][:40]}` ({top['count']}회)")
                    await message.channel.send("\n".join(lines))
                except Exception as e:
                    await message.channel.send(f"❌ 패턴 분석 실패: {e}")
            return

        # ── P2: Self-Reflection ────────────────────────────────────────
        if content in ("!reflect", "!반성"):
            if not _SELF_REFLECTION_ENABLED:
                await message.channel.send("⚠️ self-reflection 모듈 없음")
                return
            await message.channel.send("💭 자기 반성 분석 시작...")
            async with message.channel.typing():
                try:
                    loop = asyncio.get_event_loop()
                    result = await loop.run_in_executor(None, lambda: _self_reflection_run(notify_discord=False))
                    preview = result.get("analysis", "")[:300].replace("\n", " ")
                    await message.channel.send(f"💭 **자기 반성 완료**\n> {preview}")
                except Exception as e:
                    await message.channel.send(f"❌ 자기 반성 실패: {e}")
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
            if _WORKER_POOL_ENABLED and tq:
                pool = _get_worker_pool()
                task_text = pool.get_board_text()
            else:
                task_text = format_task_list()
            for chunk in split_message(task_text):
                await message.channel.send(chunk)
            return

        # ── 태스크 상태 조회 !status T001 ──────────────────────────────────────
        if content.startswith("!status ") and content[8:].strip().upper().startswith("T"):
            tid = content[8:].strip().upper()
            if _WORKER_POOL_ENABLED and tq:
                task = await asyncio.to_thread(tq.get, tid)
                if task:
                    icon = {"pending": "⏳", "in_progress": "🔄", "submitted": "📤",
                            "done": "✅", "failed": "❌"}.get(task["status"], "❓")
                    agent_icon = {"claude": "🧠", "codex": "⚡", "bucky": "🤖"}.get(task["agent"], "")
                    lines = [
                        f"{icon} `{task['id']}` {agent_icon} **{task['title']}**",
                        f"상태: `{task['status']}` | 에이전트: `{task['agent']}`",
                        f"생성: {task['created']}",
                    ]
                    if task.get("updated"):
                        lines.append(f"갱신: {task['updated']}")
                    if task.get("result"):
                        lines.append(f"\n결과:\n```\n{task['result'][:800]}\n```")
                    await message.channel.send("\n".join(lines))
                else:
                    await message.channel.send(f"❓ `{tid}` — 태스크를 찾을 수 없습니다.")
            else:
                await message.channel.send("⚠️ 워커풀이 비활성화 상태입니다.")
            return

        # ── !task / !태스크추가 — 자동 라우팅 백그라운드 실행 ──────────────────────
        if content.startswith("!태스크추가 ") or content.startswith("!task "):
            body = content.split(" ", 1)[1].strip()
            if body:
                if _WORKER_POOL_ENABLED and tq:
                    task = await asyncio.to_thread(tq.add, body[:60], body, None, "discord")
                    agent_icon = {"claude": "🧠", "codex": "⚡", "bucky": "🤖"}.get(task["agent"], "")
                    tid = task["id"]
                    title_short = task["title"][:40]

                    # 스레드 생성 — 결과 격리용
                    thread = None
                    try:
                        thread = await message.channel.create_thread(
                            name=f"[{tid[-6:]}] {title_short}",
                            message=None,
                            auto_archive_duration=60,
                            type=discord.ChannelType.public_thread,
                        )
                    except Exception as _te:
                        print(f"[Bot] 스레드 생성 실패 (폴백: 메인채널): {_te}", flush=True)

                    thread_mention = f" → {thread.mention}" if thread else ""
                    await message.channel.send(
                        f"📥 `{tid}` {agent_icon} **{task['title']}**\n"
                        f"→ `{task['agent'].upper()}` 배정 · 백그라운드 실행 시작{thread_mention}"
                    )
                    pool = _get_worker_pool()
                    pool.submit(
                        task,
                        thread_id=thread.id if thread else None,
                        reply_channel=message.channel,
                    )
                else:
                    task = await asyncio.to_thread(add_task, body[:40], body, None, "discord")
                    await message.channel.send(
                        f"✅ 태스크 등록: `{task['id']}` → **{task['type']}** → {task['router']}"
                    )
            return

        # ── !code — Codex 강제 배정 ───────────────────────────────────────────
        if content.startswith("!code "):
            body = content[6:].strip()
            if body and _WORKER_POOL_ENABLED and tq:
                task = await asyncio.to_thread(tq.add, body[:60], body, "codex", "discord")
                await message.channel.send(
                    f"📥 `{task['id']}` ⚡ **{task['title']}**\n"
                    f"→ CODEX 강제 배정 · AgentBus 전달 중..."
                )
                pool = _get_worker_pool()
                pool.submit(task, reply_channel=message.channel)
            elif body:
                await message.channel.send("⚠️ 워커풀 비활성화 — `pip install` 후 재시작 필요")
            return

        # ── !think — Claude 강제 배정 ─────────────────────────────────────────
        if content.startswith("!think "):
            body = content[7:].strip()
            if body and _WORKER_POOL_ENABLED and tq:
                task = await asyncio.to_thread(tq.add, body[:60], body, "claude", "discord")
                await message.channel.send(
                    f"📥 `{task['id']}` 🧠 **{task['title']}**\n"
                    f"→ CLAUDE 강제 배정 · 백그라운드 분석 시작..."
                )
                pool = _get_worker_pool()
                pool.submit(task, reply_channel=message.channel)
            elif body:
                await message.channel.send("⚠️ 워커풀 비활성화")
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
                agent_emoji = {
                    "claude": "🤖", "codex": "🔍", "collector": "📥",
                    "distiller": "🧠", "gap": "🔎", "reporter": "📊",
                    "gemini-research": "🔭", "gemini-rag": "📚",
                    "gemini-multimodal": "🖼️", "gemini-content": "✍️",
                    "gemini-validator": "🛡️",
                }.get(agent, "📋")
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

        # ── 컨텍스트 조회 / 업데이트 ─────────────────────────────────────────────
        if content in ("!컨텍스트", "!context"):
            try:
                ctx = _load_bucky_context()
                preview = ctx[:1200] + ("\n...(이하 생략)" if len(ctx) > 1200 else "")
                await message.channel.send(f"📋 **BUCKY_CONTEXT.md 현재 내용:**\n```\n{preview}\n```")
            except Exception as e:
                await message.channel.send(f"❌ 컨텍스트 로드 실패: {e}")
            return

        if content.startswith("!컨텍스트 업데이트 ") or content.startswith("!context update "):
            update_body = content.split(None, 2)[2].strip() if len(content.split(None, 2)) > 2 else ""
            if not update_body:
                await message.channel.send("사용법: `!컨텍스트 업데이트 <추가할 내용>`")
                return
            try:
                existing = _CONTEXT_FILE.read_text(encoding="utf-8")
                from datetime import datetime as _dt
                append_text = f"\n\n> [{_dt.now().strftime('%Y-%m-%d %H:%M')} 업데이트]\n> {update_body}\n"
                _CONTEXT_FILE.write_text(existing + append_text, encoding="utf-8")
                _context_cache["loaded_at"] = 0.0  # 캐시 무효화
                await message.channel.send(f"✅ 컨텍스트 업데이트 완료:\n> {update_body[:200]}")
            except Exception as e:
                await message.channel.send(f"❌ 업데이트 실패: {e}")
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
                "**🧠 에이전트 역할 분담 (버키 오케스트레이터)**\n",
                "**[코어 에이전트]**",
                "🤖 **Bucky** — 의도판단, 작업배분, 최종승인, Obsidian 기록",
                "🛠️ **ClaudeCode** — 시스템설계, 긴 문서, 전략, 워크플로",
                "🔍 **Codex** — 코드작성, 디버깅, 자동화 스크립트, API 연결",
                "📥 **Collector** — GPT/Claude/Codex 대화 수집 파이프라인",
                "🧠 **Distiller** — 원시 대화 → 구조화 지식 변환\n",
                "**[Gemini 보조 전문가]** (`!gemini <역할> <내용>`으로 직접 호출)",
                "🔭 **Gemini-Research** — 웹/시장/기술 리서치, 출처 기반 요약 | 키워드: 검색해, 리서치, 최신, 시장조사",
                "📚 **Gemini-RAG** — Obsidian Vault 검색·요약·재구성 | 키워드: vault, 노트에서, 기록에서",
                "🖼️ **Gemini-Multimodal** — 이미지·도면·현장사진 분석 | 키워드: 이미지 분석, 사진 분석, 도면",
                "✍️ **Gemini-Content** — 블로그·쇼츠·광고문구·영상프롬프트 | 키워드: 블로그, 유튜브, 쇼츠, 콘텐츠",
                "🛡️ **Gemini-Validator** — Claude/Codex 산출물 교차검증 | 키워드: 교차검증, 리스크 점검, 이중검토\n",
                "→ `!배분 <작업>` 자동분류 | `!gemini research 검색할 내용` 직접호출",
            ]
            await message.channel.send("\n".join(lines))
            return

        # ── Gemini 직접 호출 ─────────────────────────────────────────────────
        if content.startswith("!gemini "):
            parts = content.split(None, 2)
            if len(parts) < 3:
                await message.channel.send(
                    "사용법: `!gemini <역할> <내용>`\n"
                    "역할: `research` | `rag` | `multimodal` | `content` | `validator`"
                )
                return
            gemini_role = parts[1].lower()
            gemini_prompt = parts[2].strip()
            valid_roles = {"research", "rag", "multimodal", "content", "validator"}
            if gemini_role not in valid_roles:
                await message.channel.send(f"❌ 알 수 없는 역할: `{gemini_role}`\n가능: {', '.join(sorted(valid_roles))}")
                return
            role_emoji = {"research": "🔭", "rag": "📚", "multimodal": "🖼️", "content": "✍️", "validator": "🛡️"}
            emoji = role_emoji.get(gemini_role, "🤖")
            async with message.channel.typing():
                try:
                    sys.path.insert(0, str(Path(__file__).parent))
                    from gemini_client import run_gemini
                    result = await asyncio.to_thread(run_gemini, gemini_role, gemini_prompt)
                    header = f"{emoji} **[Gemini-{gemini_role.capitalize()}]**\n"
                    for chunk in split_message(header + result):
                        await message.channel.send(chunk)
                except Exception as e:
                    await message.channel.send(f"❌ Gemini 오류: {e}")
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
            # 다중 태스크 감지 → 병렬 처리
            multi_tasks = parse_multi_tasks(content)
            if len(multi_tasks) >= 2:
                await message.channel.send(
                    f"⚡ **{len(multi_tasks)}개 태스크 병렬 실행 시작** — 각 결과는 완료 즉시 전송됩니다."
                )

                async def _notify_done(label: str, reply_text: str) -> None:
                    header = f"**✅ [{label}] 완료**\n"
                    for chunk in split_message(header + reply_text):
                        await message.channel.send(chunk)

                try:
                    results = await run_parallel(
                        ask_fn=ask_bucky,
                        base_channel_id=channel_id,
                        tasks=multi_tasks,
                        notify_done=_notify_done,
                        timeout=300.0,
                    )
                    reply = format_multi_result(results)
                except Exception as e:
                    reply = f"⚠️ 병렬 실행 오류: {e}"
                    print(f"[Bot] MultiDispatch Error: {e}", flush=True)
                    for chunk in split_message(reply):
                        await message.channel.send(chunk)
                # 병렬 완료 후 Obsidian 동기화만 수행 (개별 전송 이미 완료)
                append_to_bucky_chat(message.author.name, content, reply)
                write_discord_message(message, reply, status="answered")
                return

            # jh-chat은 항상 Bucky 대화 응답 — 태스크 배정은 !task/!code 또는 #jh-tasks 채널 사용
            if True:
                # 이전 세션에서 남은 thinking 메시지 삭제 (봇 재시작 후 잔여 메시지 정리)
                _old_tm = _active_thinking_msgs.pop(channel_id, None)
                if _old_tm is not None:
                    try:
                        await _old_tm.delete()
                    except Exception:
                        pass

                thinking_msg = await message.channel.send("🔍 RAG 지식 검색 중... _(⏱ 0초)_")
                _active_thinking_msgs[channel_id] = thinking_msg
                _stop = asyncio.Event()
                _anim = asyncio.create_task(_animate_thinking(thinking_msg, _stop))
                try:
                    reply = await ask_bucky(channel_id, content)
                except BuckyError as e:
                    reply = f"⚠️ Bucky 오류: {e}"
                    print(f"[Bot] BuckyError: {e}", flush=True)
                except Exception as e:
                    reply = f"⚠️ 오류: {e}"
                    print(f"[Bot] Error: {e}", flush=True)
                finally:
                    _stop.set()
                    _anim.cancel()
                    _active_thinking_msgs.pop(channel_id, None)

                chunks = split_message(reply)
                await thinking_msg.edit(content=chunks[0])
                for chunk in chunks[1:]:
                    await message.channel.send(chunk)

                # 음성 채널 TTS 재생 (입장 중인 경우)
                guild_id = getattr(message.guild, "id", None)
                if guild_id and VOICE_CHANNEL_ENABLED:
                    vc = _voice_clients.get(guild_id)
                    if vc and vc.is_connected():
                        asyncio.ensure_future(_tts_speak(vc, reply, guild_id))

                # Obsidian PC 채팅창에 동기화
                append_to_bucky_chat(message.author.name, content, reply)

                out_path = write_discord_message(message, reply, status="answered")
        else:
            out_path = write_discord_message(message, status="pending")

        print(f"[Bot] Saved: {out_path.name}", flush=True)


# ── 진입점 ─────────────────────────────────────────────────────────────────────

def main() -> None:
    import socket as _socket
    _allowed_host = os.getenv("BOT_ALLOWED_HOSTNAME", "").strip()
    _this_host = _socket.gethostname()
    if _allowed_host and _this_host != _allowed_host:
        print(
            f"[Bot] 이 PC({_this_host})는 봇 실행 허용 대상이 아닙니다 "
            f"(BOT_ALLOWED_HOSTNAME={_allowed_host}). 종료.",
            flush=True,
        )
        raise SystemExit(0)

    if not TOKEN:
        print("[Bot] DISCORD_BOT_TOKEN not set.", flush=True)
        raise SystemExit(1)
    if not BUCKY_ENABLED:
        print("[Bot] BUCKY_ENABLED=0 — inbox-only 모드.", flush=True)

    intents = Intents.default()
    intents.message_content = True
    BuckyDiscordBot(intents=intents).run(TOKEN)


if __name__ == "__main__":
    # --check: 문법 검사만 하고 Discord 연결 없이 즉시 종료 (Claude Code 훅 등 외부 헬스체크용)
    if "--check" in sys.argv:
        print("discord_bot.py syntax OK", flush=True)
        raise SystemExit(0)
    main()
