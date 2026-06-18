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
# pytest 프로세스 내에서는 pytest의 capture tmpfile을 보호하기 위해 stdout 수정 전체 스킵
import io as _io
_UNDER_PYTEST = (
    "pytest" in sys.modules
    or "_pytest" in sys.modules
    or "PYTEST_CURRENT_TEST" in os.environ
    or "_PYTEST_ACTIVE" in os.environ
)
if sys.platform == "win32" and not _UNDER_PYTEST:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
    except Exception:
        pass

# stdout/stderr 닫혀 있을 때(콘솔 없이 실행, 창 닫힘 등) print 크래시 방지
if not _UNDER_PYTEST:
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

try:
    from agent_keyword_router import classify as _kw_classify, format_routing_hint as _kw_hint
    _KW_ROUTER_ENABLED = True
except ImportError:
    _KW_ROUTER_ENABLED = False
    def _kw_classify(text: str):  # type: ignore[misc]
        return None, []
    def _kw_hint(agent, matched) -> str:  # type: ignore[misc]
        return ""

_ROOT = Path(__file__).parent.parent
load_dotenv(_ROOT / ".env", encoding="utf-8-sig")

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
# 대시보드 intake 전용 채널
JH_REPO_DASHBOARD_CHANNEL_ID: str = os.getenv("JH_REPO_DASHBOARD_CHANNEL_ID", "").strip()
JH_WISHKET_CHANNEL_ID: str        = os.getenv("JH_WISHKET_CHANNEL_ID", "").strip()
JH_KMONG_CHANNEL_ID: str          = os.getenv("JH_KMONG_CHANNEL_ID", "").strip()
JH_MYINTRO_CHANNEL_ID: str        = os.getenv("JH_MYINTRO_CHANNEL_ID", "").strip()
JH_DAILYPLUS_CHANNEL_ID: str      = os.getenv("JH_DAILYPLUS_CHANNEL_ID", "").strip()
JH_TASKBOARD_CHANNEL_ID: str      = os.getenv("JH_TASKBOARD_CHANNEL_ID", "").strip()
JH_CHRIS_CHANNEL_ID: str          = os.getenv("JH_CHRIS_CHANNEL_ID", "").strip()
JH_CHARLIE_CHANNEL_ID: str        = os.getenv("JH_CHARLIE_CHANNEL_ID", "").strip()
# 앱 세션 채널: Claude Code / Codex 앱 세션 요청/상태 보고
JH_CLAUDE_CODE_CHANNEL_ID: str = os.getenv("JH_CLAUDE_CODE_CHANNEL_ID", "").strip()
JH_CODEX_CHANNEL_ID: str       = os.getenv("JH_CODEX_CHANNEL_ID", "").strip()
# 내 개발 채널: 사용자 자체 사이드 프로젝트 전용
JH_MYDEV_CHANNEL_ID: str = os.getenv("JH_MYDEV_CHANNEL_ID", "").strip()
# 쇼츠 수익화 전용 채널 (Vercel 대시보드 → Discord → 로컬 스킬)
JH_SHORTS_CHANNEL_ID: str = os.getenv("JH_SHORTS_CHANNEL_ID", "").strip()
_SHORTS_LOCAL_AGENT = Path(os.getenv(
    "SHORTS_LOCAL_AGENT_PATH",
    r"D:\ai프로젝트\쇼츠자동화\shorts-local-agent"
))
# 작업 채널: 채널 = 독립 Claude Code 인스턴스 (tools 허용, 병렬 실행)
JH_WORK_CHANNEL_IDS: set[str] = {
    c.strip() for c in os.getenv("JH_WORK_CHANNEL_IDS", "").split(",") if c.strip()
}

# ── 환경변수 ───────────────────────────────────────────────────────────────────

TOKEN: str = os.getenv("DISCORD_BOT_TOKEN", "")
GUILD_ID: str = os.getenv("DISCORD_GUILD_ID", "")
ALLOWED_CHANNELS: set[str] = {
    c.strip() for c in os.getenv("DISCORD_CHANNEL_IDS", "").split(",") if c.strip()
} | {
    c
    for c in (
        JH_CHAT_CHANNEL_ID,
        JH_REPO_DASHBOARD_CHANNEL_ID,
        JH_WISHKET_CHANNEL_ID,
        JH_KMONG_CHANNEL_ID,
        JH_MYINTRO_CHANNEL_ID,
        JH_DAILYPLUS_CHANNEL_ID,
        JH_TASKBOARD_CHANNEL_ID,
        JH_CHRIS_CHANNEL_ID,
        JH_CHARLIE_CHANNEL_ID,
        JH_CLAUDE_CODE_CHANNEL_ID,
        JH_CODEX_CHANNEL_ID,
        JH_MYDEV_CHANNEL_ID,
        JH_SHORTS_CHANNEL_ID,
    )
    if c
} | JH_WORK_CHANNEL_IDS  # 작업 채널 자동 포함
VAULT = Path(os.getenv("VAULT_PATH", str(_ROOT / "ObsidianVault")))
INBOX = VAULT / "10_AgentBus" / "inbox"
DAILY_PLUS_OUTBOX = VAULT / "10_AgentBus" / "outbox" / "Bucky"
DAILY_PLUS_BRIDGE_STATE = VAULT / "10_AgentBus" / "signals" / "daily_plus_discord_bridge.json"
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
_voice_paused: dict[int, bool] = {}  # guild_id → STT 일시정지 여부

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
_VAULT = VAULT  # VAULT_PATH 환경변수 준수 (Multi-Vault 대비)
_CONTEXT_FILE = _VAULT / "00_System" / "BUCKY_CONTEXT.md"
_REQUIRED_CONTEXT_PACKS = [
    _VAULT / "06_Context_Packs" / "bucky-agent-os-legacy-rules.md",
    _VAULT / "06_Context_Packs" / "bucky-migration-build-charter.md",
    _VAULT / "06_Context_Packs" / "bucky-context-efficiency-goal-mode.md",
    _VAULT / "00_System" / "GDRIVE_SCRIPT_CLASSIFICATION_2026-05-30.md",
    _VAULT / "05_Frameworks" / "LegalizeKR" / "legalize_update_policy.md",
]
_CONTEXT_PACK_CHAR_LIMIT = int(os.getenv("BUCKY_CONTEXT_PACK_CHAR_LIMIT", "18000"))
_LATEST_GRAPHIFY_SUMMARY = _VAULT / "10_AgentBus" / "completed" / "latest_daily_graphify_evolution.md"
_GRAPHIFY_SUMMARY_CHAR_LIMIT = int(os.getenv("BUCKY_GRAPHIFY_SUMMARY_CHAR_LIMIT", "4000"))
_CHRIS_ROLE_FILE = Path(
    os.getenv(
        "CHRIS_ROLE_FILE",
        str(_VAULT / "03_Projects" / "agents" / "chris.md"),
    )
)
_CHRIS_CONTEXT_CHAR_LIMIT = int(os.getenv("CHRIS_CONTEXT_CHAR_LIMIT", "6000"))
_context_cache: dict = {"text": "", "loaded_at": 0.0}
_chris_context_cache: dict = {"text": "", "loaded_at": 0.0}
_charlie_context_cache: dict = {"text": "", "loaded_at": 0.0}
_CONTEXT_TTL = 300  # 5분
_CHRIS_CONTEXT_TTL = 300

# ── Checklist 헬퍼 ─────────────────────────────────────────────────────────
_CHECKLIST_JSON = _ROOT / "data" / "user_checklist.json"
_CHECKLIST_DOCS_JSON = _ROOT / "docs" / "data" / "user_checklist.json"


def _cl_load() -> dict:
    try:
        return _json_mod.loads(_CHECKLIST_JSON.read_text(encoding="utf-8"))
    except Exception:
        return {"meta": {"version": "2.0", "last_updated": ""}, "tasks": []}


def _cl_save(data: dict) -> None:
    from datetime import date
    data.setdefault("meta", {})["last_updated"] = str(date.today())
    text = _json_mod.dumps(data, ensure_ascii=False, indent=2)
    _CHECKLIST_JSON.write_text(text, encoding="utf-8")
    try:
        _CHECKLIST_DOCS_JSON.parent.mkdir(parents=True, exist_ok=True)
        _CHECKLIST_DOCS_JSON.write_text(text, encoding="utf-8")
    except Exception as e:
        print(f"[Checklist] docs/ 동기화 실패: {e}", flush=True)


def _cl_next_id(tasks: list) -> str:
    nums = [int(t["id"].replace("CL-", "")) for t in tasks if t.get("id", "").startswith("CL-")]
    return f"CL-{(max(nums) + 1 if nums else 1):03d}"


def _cl_add(title: str, description: str = "", priority: str = "대기",
             category: str = "기타", source: str = "discord") -> dict:
    data = _cl_load()
    tasks = data.get("tasks", [])
    if any(t["title"].lower() == title.lower() for t in tasks):
        return {}
    task = {
        "id": _cl_next_id(tasks),
        "title": title,
        "description": description,
        "priority": priority,
        "category": category,
        "status": "pending",
        "added": str(__import__("datetime").date.today()),
        "source": source,
        "refs": []
    }
    tasks.append(task)
    data["tasks"] = tasks
    _cl_save(data)
    return task


def _cl_set_status(cl_id: str, status: str) -> dict | None:
    data = _cl_load()
    for t in data.get("tasks", []):
        if t["id"].upper() == cl_id.upper():
            t["status"] = status
            _cl_save(data)
            return t
    return None


def _cl_list(status_filter: str = "") -> list:
    data = _cl_load()
    tasks = data.get("tasks", [])
    if status_filter:
        tasks = [t for t in tasks if t.get("status", "pending") == status_filter]
    return tasks


def _cl_format_list(tasks: list, max_items: int = 15) -> str:
    if not tasks:
        return "📭 태스크 없음"
    pri_order = {"P0": 0, "P1": 1, "P2": 2, "대기": 3}
    sorted_tasks = sorted(tasks, key=lambda t: (pri_order.get(t.get("priority", "대기"), 4),))
    lines = []
    status_icons = {"pending": "⏳", "in_progress": "🔄", "done": "✅", "rejected": "❌"}
    for t in sorted_tasks[:max_items]:
        icon = status_icons.get(t.get("status", "pending"), "⏳")
        lines.append(f"`{t['id']}` {icon} **[{t.get('priority','?')}]** {t['title']}")
    if len(sorted_tasks) > max_items:
        lines.append(f"_... 외 {len(sorted_tasks) - max_items}개_")
    return "\n".join(lines)


import re as _re
_CL_INCOMPLETE_PATTERNS = [
    _re.compile(r'미완료\s*:\s*(.+?)(?:\n|$)', _re.IGNORECASE),
    _re.compile(r'\*\*미완료\*\*\s*:\s*(.+?)(?:\n|$)', _re.IGNORECASE),
    _re.compile(r'⏳\s+(.{10,80})(?:\n|$)'),
    _re.compile(r'대기\s*:\s*(.+?)(?:\n|$)', _re.IGNORECASE),
    _re.compile(r'- \[ \]\s+(.+?)(?:\n|$)'),
    _re.compile(r'다음 세션[에서]?\s*:\s*(.+?)(?:\n|$)', _re.IGNORECASE),
]


async def _auto_detect_checklist(reply: str, channel) -> None:
    """Bucky 응답에서 미완료 패턴 감지 → 체크리스트 자동 추가 (백그라운드)."""
    try:
        detected = []
        for pat in _CL_INCOMPLETE_PATTERNS:
            for m in pat.findall(reply):
                item = m.strip().strip('*').strip('`').strip()
                if 8 <= len(item) <= 120 and item not in detected:
                    detected.append(item)

        if not detected:
            return

        added = []
        for title in detected[:3]:
            task = await asyncio.to_thread(_cl_add, title, "", "대기", "자동감지", "discord-auto")
            if task:
                added.append(task["id"])

        if added:
            await channel.send(
                f"📋 **미완료 항목 자동 등록** → {', '.join(added)}\n"
                + "\n".join(f"> {t}" for t in detected[:len(added)])
                + "\n_태스크 보드에서 관리: `/task-board.html`_"
            )
    except Exception as e:
        print(f"[Checklist] 자동감지 실패: {e}", flush=True)


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

def _read_latest_graphify_summary() -> str:
    try:
        text = _LATEST_GRAPHIFY_SUMMARY.read_text(encoding="utf-8", errors="replace").strip()
    except Exception:
        return ""
    if not text:
        return ""
    excerpt = text[:_GRAPHIFY_SUMMARY_CHAR_LIMIT]
    if len(text) > len(excerpt):
        excerpt += "\n\n[TRUNCATED: Graphify summary char limit reached]"
    return "\n\n---\n\n# Latest Daily Graphify Evolution\n\n" + excerpt

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
        graphify_summary = _read_latest_graphify_summary()
        if graphify_summary:
            text = f"{text}\n\n{graphify_summary}"
        _context_cache["text"] = text
        _context_cache["loaded_at"] = now
        return text
    except Exception:
        return BUCKY_SYSTEM_PROMPT

# ── 사용자 접근제어 ─────────────────────────────────────────────────────────────

def _read_chris_role_context() -> str:
    import time
    now = time.time()
    if now - _chris_context_cache["loaded_at"] < _CHRIS_CONTEXT_TTL and _chris_context_cache["text"]:
        return _chris_context_cache["text"]
    try:
        text = _CHRIS_ROLE_FILE.read_text(encoding="utf-8", errors="replace").strip()
    except Exception:
        return ""
    if not text:
        return ""
    excerpt = text[:_CHRIS_CONTEXT_CHAR_LIMIT]
    if len(text) > len(excerpt):
        excerpt += "\n\n[TRUNCATED: Chris role char limit reached]"
    context = "\n\n---\n\n# Chris Role Instructions\n\n" + excerpt
    _chris_context_cache["text"] = context
    _chris_context_cache["loaded_at"] = now
    return context


def _uses_chris_context(channel_id: str, user_message: str = "") -> bool:
    if JH_CHRIS_CHANNEL_ID and str(channel_id) == str(JH_CHRIS_CHANNEL_ID):
        return True
    text = (user_message or "").lower()
    return (
        "knowledge_intake" in text
        or "daily plus knowledge intake" in text
        or "target_channel: jh-chris" in text
        or "jh-chris" in text
    )


def _read_charlie_context() -> str:
    import time
    now = time.time()
    if now - _charlie_context_cache["loaded_at"] < _CONTEXT_TTL and _charlie_context_cache["text"]:
        return _charlie_context_cache["text"]
    paths = [
        _ROOT / "OPERATING_INTENT.md",
        _VAULT / "00_System" / "USER_OPERATING_INTENT.md",
        _VAULT / "03_Projects" / "agents" / "charlie.md",
        _VAULT / "00_System" / "CHARLIE_AGENT_COORDINATION.md",
        _VAULT / "00_System" / "CHARLIE_EXPERT_AGENT_ROSTER.md",
        _VAULT / "00_System" / "CHARLIE_HERMES_LEVEL_ROADMAP.md",
    ]
    sections: list[str] = []
    remaining = int(os.getenv("CHARLIE_CONTEXT_CHAR_LIMIT", "10000"))
    for path in paths:
        if remaining <= 0:
            break
        try:
            text = path.read_text(encoding="utf-8", errors="replace").strip()
        except Exception:
            continue
        if not text:
            continue
        excerpt = text[:remaining]
        if len(text) > len(excerpt):
            excerpt += "\n\n[TRUNCATED: Charlie context char limit reached]"
        sections.append(f"## {path.name}\n\n{excerpt}")
        remaining -= len(excerpt)
    context = "\n\n---\n\n# Charlie System Audit Context\n\n" + "\n\n---\n\n".join(sections) if sections else ""
    _charlie_context_cache["text"] = context
    _charlie_context_cache["loaded_at"] = now
    return context


def _uses_charlie_context(channel_id: str, user_message: str = "") -> bool:
    if JH_CHARLIE_CHANNEL_ID and str(channel_id) == str(JH_CHARLIE_CHANNEL_ID):
        return True
    text = (user_message or "").lower()
    return (
        "target_channel: jh-charlie" in text
        or "jh-charlie" in text
        or "charlie audit" in text
        or "찰리" in text
    )


def _load_agent_context(channel_id: str, user_message: str = "") -> str:
    context = _load_bucky_context()
    if _uses_charlie_context(channel_id, user_message):
        charlie_context = _read_charlie_context()
        if charlie_context:
            return f"{context}\n\n{charlie_context}"
    if not _uses_chris_context(channel_id, user_message):
        return context
    chris_context = _read_chris_role_context()
    if not chris_context:
        return context
    return f"{context}\n\n{chris_context}"


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


def _pending_daily_plus_briefings(paths: list[Path], sent_names: set[str]) -> list[Path]:
    pending: list[Path] = []
    for path in sorted(paths):
        if not path.name.endswith("_090000_daily_plus_dashboard_bucky.md"):
            continue
        if path.name in sent_names:
            continue
        pending.append(path)
    return pending


def _build_daily_plus_briefing_message(filename: str, text: str) -> str:
    body = text
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) == 3:
            body = parts[2].strip()
    header = f"📰 **[Daily Plus 09:00 Report]** `{filename}`"
    return f"{header}\n\n{body.strip()}".strip()


def _load_daily_plus_bridge_state() -> set[str]:
    try:
        payload = _json_mod.loads(DAILY_PLUS_BRIDGE_STATE.read_text(encoding="utf-8"))
    except Exception:
        return set()
    sent = payload.get("sent_files") or []
    return {str(item) for item in sent if str(item).strip()}


def _save_daily_plus_bridge_state(sent_names: set[str]) -> None:
    DAILY_PLUS_BRIDGE_STATE.parent.mkdir(parents=True, exist_ok=True)
    payload = {"sent_files": sorted(sent_names)}
    DAILY_PLUS_BRIDGE_STATE.write_text(
        _json_mod.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


_SHORTS_CMD_PREFIX = "[SHORTS_CMD]"


async def _handle_shorts_command(message: Message, content: str) -> None:
    """#jh-shorts 채널 전용 핸들러.
    Vercel 대시보드 버튼이 Discord Webhook으로 전송한 명령을 수신하여
    D:\\ai프로젝트\\쇼츠자동화\\shorts-local-agent\\skill_router.py 를 실행한다.
    """
    import json as _json_local

    if content.startswith("!shorts"):
        # 사용자 직접 명령: !shorts status / !shorts run_pipeline 등
        cmd_body = content[len("!shorts"):].strip() or "status"
        payload = {"action": cmd_body, "params": {}}
    elif content.startswith(_SHORTS_CMD_PREFIX):
        # Vercel 대시보드 Webhook 명령: [SHORTS_CMD] {"action": "..."}
        payload_str = content[len(_SHORTS_CMD_PREFIX):].strip()
        try:
            payload = _json_local.loads(payload_str)
        except _json_local.JSONDecodeError:
            payload = {"action": payload_str, "params": {}}
    else:
        # 일반 대화 메시지 — 안내만
        await message.channel.send(
            "이 채널은 쇼츠 자동화 전용입니다.\n"
            "`!shorts status` — 현황\n"
            "`!shorts run_pipeline` — 전체 파이프라인 실행\n"
            "`!shorts product_discovery` / `content_generation` / `revenue_sync`"
        )
        return

    action = payload.get("action", "status")
    print(f"[Shorts] 명령 수신: {action}", flush=True)
    await message.channel.send(f"⚙️ `{action}` 처리 중...")

    skill_router_path = _SHORTS_LOCAL_AGENT / "skill_router.py"
    if not skill_router_path.exists():
        await message.channel.send(
            f"⚠️ skill_router.py 없음: `{skill_router_path}`\n"
            "shorts-local-agent 설치를 확인하세요."
        )
        return

    import subprocess as _sp
    try:
        proc = await asyncio.to_thread(
            lambda: _sp.run(
                [sys.executable, str(skill_router_path), action,
                 _json_local.dumps(payload.get("params", {}))],
                capture_output=True, text=True, timeout=600,
                encoding="utf-8", errors="replace",
                cwd=str(_SHORTS_LOCAL_AGENT),
            )
        )
        output = (proc.stdout or "").strip()
        err = (proc.stderr or "").strip()

        if proc.returncode != 0:
            err_short = err[-800:] if len(err) > 800 else err
            await message.channel.send(f"❌ **[SHORTS]** `{action}` 실패\n```\n{err_short}\n```")
        else:
            try:
                result = _json_local.loads(output)
                summary = result.get("summary", output[:400])
            except Exception:
                summary = output[:400]
            await message.channel.send(f"✅ **[SHORTS]** `{action}` 완료\n{summary}")
    except asyncio.TimeoutError:
        await message.channel.send(f"⏱️ **[SHORTS]** `{action}` 타임아웃 (10분 초과)")
    except Exception as e:
        await message.channel.send(f"❌ **[SHORTS]** 실행 오류: {e}")


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


def _extract_json_objects(text: str) -> list[dict]:
    """Extract small JSON objects from Discord message content."""
    candidates: list[str] = []
    for block in text.split("```"):
        stripped = block.strip()
        if stripped.startswith("json"):
            candidates.append(stripped[4:].strip())
        elif stripped.startswith("{") and stripped.endswith("}"):
            candidates.append(stripped)
    if text.strip().startswith("{") and text.strip().endswith("}"):
        candidates.append(text.strip())

    objects: list[dict] = []
    for candidate in candidates:
        try:
            parsed = _json_mod.loads(candidate)
        except Exception:
            continue
        if isinstance(parsed, dict):
            objects.append(parsed)
    return objects


async def _wishket_dev_request_to_queue(payload_dict: dict) -> dict:
    """Common handler: normalize → split_actions → dispatch or queue.

    Returns {"payload", "plan", "routed_path", "codex_path", "route_mode", "actions"}.
    Both _on_dev_request and _handle_wishket_development_payload use this.
    """
    from wishket_development_request import (
        build_plan, dispatch_request, normalize_payload, split_actions,
    )
    payload = normalize_payload(payload_dict)
    actions = split_actions(payload["requested_actions"])
    payload["immediate_actions"] = actions["immediate"]
    payload["approval_required_actions"] = actions["approval_required"]
    plan = build_plan(payload)
    route_mode, routed_path, codex_path = await asyncio.to_thread(dispatch_request, payload)
    return {
        "payload": payload,
        "plan": plan,
        "routed_path": routed_path,
        "codex_path": codex_path,
        "route_mode": route_mode,
        "actions": actions,
    }


def _format_wishket_route_instruction(route_mode: str) -> str:
    if route_mode == "immediate":
        return "Immediate route: AgentBus inbox request created. Bucky can start without `!approve`."
    return "Approval route: use `!pending` to review, then `!approve <number>` to approve."


async def _handle_wishket_development_payload(message: Message, content: str) -> bool:
    """Queue Wishket development payloads behind the existing approval gate."""
    for obj in _extract_json_objects(content):
        if obj.get("type") != "wishket_development_request":
            continue
        try:
            result = await _wishket_dev_request_to_queue(obj)
            payload, plan, routed_path, codex_path, route_mode, actions = (
                result["payload"], result["plan"], result["routed_path"],
                result["codex_path"], result["route_mode"], result["actions"]
            )
            if route_mode == "immediate":
                codex_line = f"- codex review: `{codex_path.name}`\n" if codex_path else ""
                await message.channel.send(
                    "**Wishket development request accepted**\n"
                    f"- slug: `{payload['project_slug']}`\n"
                    f"- local folder: `{plan['local_project']['target']}`\n"
                    f"- claude code: `{routed_path.name}`\n"
                    f"{codex_line}"
                    f"- immediate: {', '.join(actions['immediate']) or 'none'}\n"
                    f"- approval_required: {', '.join(actions['approval_required']) or 'none'}\n\n"
                    f"{_format_wishket_route_instruction(route_mode)}"
                )
                return True
            await message.channel.send(
                "**Wishket 개발요청 접수**\n"
                f"- slug: `{payload['project_slug']}`\n"
                f"- local folder: `{plan['local_project']['target']}`\n"
                f"- route: `{route_mode}` → `{routed_path.name}`\n"
                f"- 즉시: {', '.join(actions['immediate']) or '없음'}\n"
                f"- 승인필요: {', '.join(actions['approval_required']) or '없음'}\n\n"
                "`!pending`으로 승인 대기 목록 확인, `!approve <번호>`로 승인."
            )
            return True
        except Exception as e:
            await message.channel.send(f"Wishket 개발요청 처리 실패: {e}")
            return True
    return False


async def _handle_wishket_proposal_request(payload: dict, channel) -> bool:
    if payload.get("type") != "wishket_proposal_request":
        return False
    from wishket_development_request import normalize_payload
    import wishket_proposal_workflow as proposal_workflow

    normalized = normalize_payload(payload)
    proposal_workflow.ensure_project_workspace(normalized)
    proposal_workflow.mark_proposal_started(normalized, "proposal_started")
    if channel:
        await channel.send(
            "**Wishket proposal started**\n"
            f"- slug: `{normalized['project_slug']}`\n"
            f"- title: {normalized['project_title']}\n"
            "- next: draft proposal and gather feedback"
        )
    return True


async def _handle_wishket_feedback_payload(payload: dict, channel) -> bool:
    if payload.get("type") != "wishket_feedback":
        return False
    from wishket_development_request import normalize_payload
    import wishket_proposal_workflow as proposal_workflow

    normalized = normalize_payload(payload)
    proposal_workflow.record_feedback(normalized, str(payload.get("summary") or payload.get("body") or "").strip())
    if channel:
        await channel.send(
            f"**Wishket feedback received**\n- slug: `{normalized['project_slug']}`\n- state: feedback_in_progress"
        )
    return True


async def _handle_wishket_proposal_approval_payload(payload: dict, channel) -> bool:
    if payload.get("type") != "wishket_proposal_approval":
        return False
    from wishket_development_request import normalize_payload
    import wishket_proposal_workflow as proposal_workflow

    normalized = normalize_payload(payload)
    proposal_workflow.record_approval(normalized, "discord")
    if channel:
        await channel.send(
            f"**Wishket proposal approved**\n- slug: `{normalized['project_slug']}`\n- development request unlocked"
        )
    return True


async def _handle_collab_proposal_request(payload: dict, channel) -> bool:
    if payload.get("type") != "collab_proposal_request":
        return False
    from collab_development_request import normalize_payload
    import collab_proposal_workflow as workflow

    normalized = normalize_payload(payload)
    workflow.ensure_workspace(normalized)
    workflow.mark_proposal_started(normalized, "discord")
    if channel:
        await channel.send(
            "**Collaboration proposal started**\n"
            f"- slug: `{normalized['request_slug']}`\n"
            f"- title: {normalized['project_title']}\n"
            "- source: collaboration inquiry inbox"
        )
    return True


async def _handle_collab_feedback_payload(payload: dict, channel) -> bool:
    if payload.get("type") != "collab_feedback":
        return False
    from collab_development_request import normalize_payload
    import collab_proposal_workflow as workflow

    normalized = normalize_payload(payload)
    workflow.record_feedback(normalized, "discord")
    if channel:
        await channel.send(
            f"**Collaboration feedback received**\n- slug: `{normalized['request_slug']}`\n- state: feedback_in_progress"
        )
    return True


async def _handle_collab_proposal_approval_payload(payload: dict, channel) -> bool:
    if payload.get("type") != "collab_proposal_approval":
        return False
    from collab_development_request import normalize_payload
    import collab_proposal_workflow as workflow

    normalized = normalize_payload(payload)
    workflow.record_approval(normalized, "discord")
    if channel:
        await channel.send(
            f"**Collaboration proposal approved**\n- slug: `{normalized['request_slug']}`\n- development request unlocked"
        )
    return True


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
_DAILY_PLUS_INTAKE_MARKER = "[Daily Plus Knowledge Intake]"


def parse_daily_plus_intake_content(content: str) -> dict | None:
    """Parse Daily Plus dashboard intake webhook content."""
    if _DAILY_PLUS_INTAKE_MARKER not in content:
        return None

    lines = content.splitlines()
    first_line = lines[0].strip() if lines else ""
    capture_target = ""
    if first_line.startswith("!capture "):
        capture_target = first_line[len("!capture "):].strip()

    try:
        marker_index = next(i for i, line in enumerate(lines) if line.strip() == _DAILY_PLUS_INTAKE_MARKER)
    except StopIteration:
        return None

    meta: dict[str, str] = {}
    body_lines: list[str] = []
    in_body = False
    for line in lines[marker_index + 1:]:
        stripped = line.strip()
        if not in_body and not stripped:
            in_body = True
            continue
        if not in_body and ":" in line:
            key, value = line.split(":", 1)
            meta[key.strip().lower()] = value.strip()
            continue
        body_lines.append(line)

    if not capture_target:
        capture_target = meta.get("title", "").strip()

    return {
        "capture_target": capture_target,
        "body": "\n".join(body_lines).strip(),
        "type": meta.get("type", "auto"),
        "title": meta.get("title", "(untitled)"),
        "tags": meta.get("tags", ""),
        "source": meta.get("source", "daily-plus-dashboard"),
        "session_id": meta.get("session_id", ""),
        "follow_up_state": meta.get("follow_up_state", ""),
        "files": meta.get("files", ""),
    }


def _extract_attachment_paths_from_content(content: str) -> list[str]:
    marker = "[Discord attachment capture]"
    if marker not in content:
        return []
    after = content.split(marker, 1)[1]
    first_line = after.strip().splitlines()[0] if after.strip() else ""
    return [part.strip() for part in first_line.split(",") if part.strip()]


def _extract_youtube_url_from_text(text: str) -> str:
    """Return the first YouTube URL in free text, with common punctuation trimmed."""
    for raw_url in _URL_PATTERN.findall(str(text or "")):
        url = raw_url.rstrip(").,]}>\"'")
        if _YOUTUBE_PATTERN.search(url):
            return url
    return ""


def _extract_youtube_url_from_payload(payload: dict) -> str:
    for key in ("capture_target", "watch_command", "url", "link", "body", "summary", "title"):
        value = payload.get(key)
        if isinstance(value, (list, tuple)):
            value = "\n".join(str(item) for item in value)
        url = _extract_youtube_url_from_text(str(value or ""))
        if url:
            return url
    return ""


def _dashboard_watch_tags(payload: dict) -> list[str]:
    raw_tags = payload.get("tags") or []
    if isinstance(raw_tags, str):
        tags = [tag.strip() for tag in raw_tags.split(",") if tag.strip() and tag.strip().lower() != "(none)"]
    elif isinstance(raw_tags, (list, tuple, set)):
        tags = [str(tag).strip() for tag in raw_tags if str(tag).strip()]
    else:
        tags = []
    for tag in ("dashboard-watch", "youtube"):
        if tag not in tags:
            tags.append(tag)
    dashboard_type = str(payload.get("dashboard_type") or "").strip()
    if dashboard_type and dashboard_type not in tags:
        tags.append(dashboard_type)
    return tags


_VIDEO_GENERATION_KEYWORDS = (
    "higgsfield", "히그스필드", "힉스필드", "video generation", "text to video",
    "image to video", "ai video", "영상제작", "영상 제작", "영상 만들어",
    "영상 만들", "쇼츠", "릴스", "틱톡", "광고 영상", "유튜브 인트로",
)


def _payload_text_for_intent(payload: dict) -> str:
    values: list[str] = []
    for key in (
        "dashboard_type", "action", "title", "summary", "body", "note",
        "capture_target", "watch_command", "url", "link", "tags",
    ):
        value = payload.get(key)
        if isinstance(value, (list, tuple, set)):
            values.extend(str(item) for item in value)
        else:
            values.append(str(value or ""))
    return "\n".join(values)


def _looks_like_video_generation_request(payload: dict) -> bool:
    text = _payload_text_for_intent(payload).lower()
    return any(keyword.lower() in text for keyword in _VIDEO_GENERATION_KEYWORDS)


def _build_higgsfield_video_prompt(payload: dict, reference_url: str = "") -> str:
    dashboard_type = str(payload.get("dashboard_type") or "unknown")
    action = str(payload.get("action") or "")
    title = str(payload.get("title") or payload.get("summary") or "").strip()
    body = str(payload.get("body") or payload.get("note") or "").strip()
    request_id = str(payload.get("request_id") or "").strip()
    source_assets = str(payload.get("source_assets") or payload.get("files") or "").strip()
    prompt = str(payload.get("prompt") or payload.get("video_prompt") or "").strip()

    lines = [
        "[Bucky Higgsfield Video Production Intake]",
        f"dashboard_type: {dashboard_type}",
        f"action: {action}",
    ]
    if request_id:
        lines.append(f"request_id: {request_id}")
    if title:
        lines.append(f"title: {title}")
    if reference_url:
        lines.append(f"reference_url: {reference_url}")
    if source_assets:
        lines.append(f"source_assets: {source_assets}")
    if prompt:
        lines.append(f"video_prompt: {prompt}")
    if body:
        lines.append("")
        lines.append(body)
    lines.extend(
        [
            "",
            "## Required behavior",
            "Load `ObsidianVault/06_Context_Packs/bucky-higgsfield-video-production-mcp-2026-06-10.md`.",
            "Treat this as a video production request, not a generic chat summary.",
            "Normalize goal, platform, duration, aspect_ratio, source_assets, style, script, negative_constraints, approval_state, and evidence.",
            "If a reference URL is present, use it only as benchmark/style evidence after capture; do not copy protected content.",
            "Use the configured `higgsfield` MCP server when available. If auth, credit, or MCP tool access is missing, report `blocked_auth_required` or `approval_required` with the exact next action.",
            "Return a concise Korean status with: MCP state, normalized payload, execution/approval state, and next action.",
        ]
    )
    return "\n".join(lines)


async def _handle_higgsfield_video_payload(payload: dict, channel) -> bool:
    if not _looks_like_video_generation_request(payload):
        return False

    reference_url = _extract_youtube_url_from_payload(payload)
    dashboard_type = str(payload.get("dashboard_type") or "dashboard")
    action = str(payload.get("action") or "video")
    title = str(payload.get("title") or payload.get("summary") or "AI video production").strip()
    request_id = str(payload.get("request_id") or "").strip()

    if channel:
        lines = [
            f"🎞️ **[Video Production Intake] Higgsfield MCP 준비** (`{dashboard_type}/{action}`)",
            f"- title: {title[:160]}",
        ]
        if reference_url:
            lines.append(f"- reference: {reference_url}")
        if request_id:
            lines.append(f"- request_id: `{request_id[:12]}`")
        await channel.send("\n".join(lines))

    if not channel:
        return True

    try:
        timeout_s = int(os.getenv("HIGGSFIELD_VIDEO_BUCKY_TIMEOUT", "120"))
        reply = await asyncio.wait_for(
            ask_bucky(
                str(channel.id),
                _build_higgsfield_video_prompt(payload, reference_url),
                session_key=_dashboard_session_key(payload),
                session_label=_dashboard_session_label(payload),
            ),
            timeout=timeout_s,
        )
        for chunk in split_message(reply):
            await channel.send(chunk)
    except asyncio.TimeoutError:
        await channel.send("⚠️ Higgsfield 영상 제작 요청은 수신됐지만 Bucky 응답 시간이 초과됐습니다. 같은 채널에서 이어서 지시하세요.")
    except Exception as exc:
        print(f"[VideoProduction] Bucky 라우팅 실패: {exc}", flush=True)
        await channel.send(f"⚠️ Higgsfield 영상 제작 라우팅 실패: `{exc}`")
    return True


async def _handle_dashboard_watch_payload(payload: dict, channel) -> bool:
    watch_url = _extract_youtube_url_from_payload(payload)
    if not watch_url:
        return False

    dashboard_type = str(payload.get("dashboard_type") or "dashboard")
    action = str(payload.get("action") or "watch")
    title = str(payload.get("title") or "YouTube watch intake").strip()
    request_id = str(payload.get("request_id") or "").strip()
    tags = _dashboard_watch_tags(payload)

    if channel:
        lines = [
            f"🎬 **[Watch Intake] YouTube 분석 시작** (`{dashboard_type}/{action}`)",
            f"- title: {title[:160]}",
            f"- url: {watch_url}",
        ]
        if request_id:
            lines.append(f"- request_id: `{request_id[:12]}`")
        await channel.send("\n".join(lines))

    try:
        from bucky_youtube_capture import capture_youtube
        if channel:
            async with channel.typing():
                yt_result = await asyncio.to_thread(lambda: capture_youtube(watch_url, tags))
        else:
            yt_result = await asyncio.to_thread(lambda: capture_youtube(watch_url, tags))
    except Exception as exc:
        if channel:
            await channel.send(f"⚠️ YouTube watch 처리 실패: `{type(exc).__name__}: {exc}`")
        return True

    if not yt_result.get("success"):
        if channel:
            await channel.send(f"⚠️ YouTube watch 저장 실패: `{yt_result.get('error', '')}`")
        return True

    reply_lines = [
        "✅ **YouTube 지식 저장 완료**",
        f"- title: {yt_result.get('title') or title}",
        f"- path: `{yt_result.get('filepath', '')}`",
        f"- transcript: {'yes' if yt_result.get('has_transcript') else 'no'}",
    ]
    if yt_result.get("summary"):
        reply_lines.append(f"\n```text\n{str(yt_result['summary'])[:500]}\n```")
    if channel:
        for chunk in split_message("\n".join(reply_lines)):
            await channel.send(chunk)
        ch_id = str(channel.id)
        conversation_history[ch_id].append({"role": "user", "content": f"YouTube 저장 요청: {watch_url}"})
        conversation_history[ch_id].append({"role": "assistant", "content": f"YouTube '{yt_result.get('title') or watch_url}' 저장 완료. 이 영상에 대해 무엇이 필요하신가요?"})
    return True


def build_daily_plus_intake_session_prompt(
    payload: dict,
    saved_paths: list[str] | None = None,
    attachment_paths: list[str] | None = None,
) -> str:
    """Build the Bucky chat prompt for an intake that must continue as a session."""
    saved_paths = saved_paths or []
    attachment_paths = attachment_paths or []
    saved_block = "\n".join(f"- {path}" for path in saved_paths) or "- (none)"
    attachment_block = "\n".join(f"- {path}" for path in attachment_paths) or "- (none)"

    return "\n".join(
        [
            "[Daily Plus Knowledge Intake]",
            f"session_id: {payload.get('session_id') or 'daily-plus-intake'}",
            f"source: {payload.get('source') or 'daily-plus-dashboard'}",
            f"type: {payload.get('type') or 'auto'}",
            f"title: {payload.get('title') or '(untitled)'}",
            f"tags: {payload.get('tags') or '(none)'}",
            f"follow_up_state: {payload.get('follow_up_state') or 'awaiting_user_instruction'}",
            "",
            "## Intake 원본",
            str(payload.get("body") or payload.get("capture_target") or "").strip(),
            "",
            "## 저장 증거",
            saved_block,
            "",
            "## 첨부 저장 증거",
            attachment_block,
            "",
            "## Bucky 작업 지시",
            "이 입력은 단순 저장 완료 로그가 아니라 Discord 사용자 세션으로 이어지는 작업입니다.",
            "1. 원본 데이터, 링크, YouTube, 지식베이스, 첨부 정보를 분석하세요.",
            "2. 저장된 Obsidian raw 경로를 참조해 분석 브리핑을 작성하세요.",
            "3. 분석 브리핑 끝에 다음 사용자 작업 지시를 기다리는 상태임을 명시하세요.",
            "4. 필요한 후속 질문이 있으면 Discord에서 바로 사용자에게 물어보세요.",
            "",
            "완료 형식: 요약 -> 핵심 분석 -> 저장 위치 -> 다음 행동/질문 -> 다음 사용자 작업 지시를 기다리는 상태",
        ]
    )


def build_daily_plus_intake_fallback_reply(
    payload: dict,
    saved_paths: list[str] | None = None,
    reason: str = "",
) -> str:
    saved_paths = saved_paths or []
    saved_block = "\n".join(f"- {path}" for path in saved_paths) or "- (none)"
    body = str(payload.get("body") or payload.get("capture_target") or "").strip()
    reason_line = f"\n- fallback reason: {reason}" if reason else ""
    return "\n".join(
        [
            "## 분석 브리핑",
            "",
            "### 요약",
            "Daily Plus Knowledge Intake 입력을 수신했고 원본 저장 흐름까지 처리했습니다.",
            reason_line.strip(),
            "",
            "### 핵심 분석",
            body or "(본문 없음)",
            "",
            "### 저장 위치",
            saved_block,
            "",
            "### 다음 행동/질문",
            "Bucky CLI 응답이 지연되거나 실패해 fallback briefing으로 기록했습니다. 사용자가 다음 지시를 주면 같은 Discord 채널 세션에서 이어서 처리합니다.",
            "",
            "**다음 사용자 작업 지시를 기다리는 상태입니다.**",
        ]
    )


def _dashboard_session_key(payload: dict) -> str:
    dashboard_type = str(payload.get("dashboard_type") or payload.get("source") or "dashboard").strip()
    for key in ("session_id", "item_id", "project_slug", "repo", "title", "request_id"):
        value = str(payload.get(key) or "").strip()
        if value:
            return f"{dashboard_type}:{value}"
    return dashboard_type


def _dashboard_session_label(payload: dict) -> str:
    dashboard_type = str(payload.get("dashboard_type") or payload.get("source") or "dashboard").strip()
    action = str(payload.get("action") or "").strip()
    title = str(payload.get("title") or payload.get("summary") or payload.get("body") or "").strip()
    parts = [part for part in (dashboard_type, action, title[:80]) if part]
    return " | ".join(parts)


def _checklist_requires_manual_action(payload: dict) -> bool:
    explicit = payload.get("requires_user_approval")
    if isinstance(explicit, bool):
        return explicit
    execution_mode = str(payload.get("execution_mode") or "").strip().lower()
    if execution_mode in {"approval_required", "manual", "user_approved_pc_control"}:
        return True
    if execution_mode in {"auto_executable", "immediate"}:
        return False

    text = " ".join(
        str(payload.get(key) or "")
        for key in ("title", "summary", "body", "note", "priority", "status")
    ).lower()
    manual_markers = (
        "requires_approval=true",
        "requires_user_approval=true",
        "approval_required",
        "user approval",
        "manual",
        "login",
        "password",
        "credential",
        "oauth",
        "chrome extension",
        "vercel",
        "supabase",
        "local pc control",
        "bot restart",
        "zero trust",
        "api key",
        "credit",
    )
    return any(marker in text for marker in manual_markers)


async def _activate_dashboard_session(channel_id: str, payload: dict) -> int | None:
    try:
        import bucky_memory as _mem
        return await asyncio.to_thread(
            _mem.get_or_create_session_for_key,
            channel_id,
            _dashboard_session_key(payload),
            _dashboard_session_label(payload),
        )
    except Exception as exc:
        print(f"[Session] dashboard session activation failed: {exc}", flush=True)
        return None


async def _handle_daily_plus_intake_payload(message: Message, content: str, channel_id: str) -> bool:
    payload = parse_daily_plus_intake_content(content)
    if not payload:
        return False

    _dbg_log = _ROOT / "discord_intake_debug.log"
    _dbg_lines = [
        f"[DailyPlus][DEBUG] raw content (first 300 chars): {repr(content[:300])}",
        f"[DailyPlus][DEBUG] parsed body: {repr((payload.get('body') or '')[:150])}",
        f"[DailyPlus][DEBUG] parsed target: {repr((payload.get('capture_target') or '')[:100])}",
    ]
    for _l in _dbg_lines:
        print(_l, flush=True)
    try:
        import datetime as _dt
        with _dbg_log.open("a", encoding="utf-8") as _f:
            _ts = _dt.datetime.now().isoformat(timespec="seconds")
            for _l in _dbg_lines:
                _f.write(f"{_ts} {_l}\n")
    except Exception:
        pass

    saved_paths: list[str] = []
    attachment_paths = _extract_attachment_paths_from_content(content)
    target = (payload.get("capture_target") or "").strip()
    body = (payload.get("body") or "").strip()
    tags = [
        tag.strip()
        for tag in (payload.get("tags") or "").split(",")
        if tag.strip() and tag.strip().lower() != "(none)"
    ]
    if "daily-plus-intake" not in tags:
        tags.append("daily-plus-intake")

    await message.channel.send("Daily Plus Intake 수신: 원본 저장 후 Bucky 분석 브리핑을 시작합니다.")
    async with message.channel.typing():
        try:
            if getattr(message, "attachments", None):
                notes = await capture_discord_attachments(message, message.attachments)
                attachment_paths.extend(str(note) for note in notes)

            if target.startswith("http") and _YOUTUBE_PATTERN.search(target):
                from bucky_youtube_capture import capture_youtube
                yt_result = await asyncio.to_thread(capture_youtube, target, tags)
                if yt_result.get("success") and yt_result.get("filepath"):
                    saved_paths.append(str(yt_result["filepath"]))
                else:
                    saved_paths.append(f"YouTube capture failed: {yt_result.get('error', '')}")
            elif target.startswith("http") and _KNOWLEDGE_CAPTURE_ENABLED:
                fp = await asyncio.to_thread(_kc_capture_url, target)
                saved_paths.append(str(fp))
            elif _KNOWLEDGE_CAPTURE_ENABLED:
                text = body or target or content
                fp = await asyncio.to_thread(_kc_capture_text, text, message.author.name)
                saved_paths.append(str(fp))

            prompt = build_daily_plus_intake_session_prompt(
                payload,
                saved_paths=saved_paths,
                attachment_paths=attachment_paths,
            )
            timeout_s = int(os.getenv("DAILY_PLUS_INTAKE_BUCKY_TIMEOUT", "90"))
            try:
                reply = await asyncio.wait_for(
                    ask_bucky(
                        channel_id,
                        prompt,
                        session_key=_dashboard_session_key({"dashboard_type": "daily_plus", **payload}),
                        session_label=_dashboard_session_label({"dashboard_type": "daily_plus", **payload}),
                    ),
                    timeout=timeout_s,
                )
            except Exception as exc:
                reply = build_daily_plus_intake_fallback_reply(
                    payload,
                    saved_paths=saved_paths + attachment_paths,
                    reason=f"{type(exc).__name__}: {exc}",
                )
        except Exception as e:
            await message.channel.send(f"Daily Plus Intake 처리 실패: {e}")
            return True

    append_to_bucky_chat(message.author.name, content, reply)
    write_discord_message(message, reply, status="answered")
    intake_label = f"[Daily Plus Intake] {payload.get('title', '(untitled)')} 저장 완료"
    conversation_history[channel_id].append({"role": "user", "content": intake_label})
    conversation_history[channel_id].append({"role": "assistant", "content": reply[:600] + ("..." if len(reply) > 600 else "")})
    for chunk in split_message(reply):
        await message.channel.send(chunk)
    return True

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

def _safe_attachment_name(name: str) -> str:
    safe = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in (name or "attachment"))
    return safe[:120] or "attachment"


async def capture_discord_attachments(
    message: Message,
    attachments: list[discord.Attachment],
    *,
    skip_urls: set[str] | None = None,
) -> list[Path]:
    """Persist generic Discord attachments so non-image/non-audio files are not lost."""
    skip_urls = skip_urls or set()
    max_bytes = int(os.getenv("DISCORD_ATTACHMENT_MAX_MB", "25")) * 1024 * 1024
    now = datetime.now()
    day = now.strftime("%Y-%m-%d")
    raw_dir = _ROOT / "RAW_IMPORT" / "Discord" / day
    note_dir = VAULT / "01_RAW" / "DiscordAttachments"
    raw_dir.mkdir(parents=True, exist_ok=True)
    note_dir.mkdir(parents=True, exist_ok=True)

    saved_notes: list[Path] = []
    channel_name = getattr(message.channel, "name", str(message.channel.id))
    author_name = getattr(message.author, "name", "unknown")
    timestamp = now.strftime("%Y%m%d_%H%M%S")

    for idx, attachment in enumerate(attachments, 1):
        if attachment.url in skip_urls:
            continue
        if attachment.size and attachment.size > max_bytes:
            print(
                f"[AttachmentCapture] skipped oversized file: {attachment.filename} "
                f"({attachment.size} bytes)",
                flush=True,
            )
            continue

        safe_name = _safe_attachment_name(attachment.filename)
        raw_path = raw_dir / f"{timestamp}_{idx}_{safe_name}"
        data = await attachment.read()
        raw_path.write_bytes(data)

        note_path = note_dir / f"{timestamp}_discord_attachment_{idx}.md"
        note = f"""---
type: discord_attachment
source: discord
channel: "{channel_name}"
channel_id: "{message.channel.id}"
author: "{author_name}"
author_id: "{message.author.id}"
message_id: "{message.id}"
filename: "{safe_name}"
content_type: "{attachment.content_type or ''}"
size_bytes: {attachment.size or len(data)}
captured_at: {now.isoformat(timespec='seconds')}
status: raw
---

# Discord attachment: {safe_name}

## Context

{message.content.strip() or "(no message text)"}

## Stored File

- Local raw import: `{raw_path.relative_to(_ROOT).as_posix()}`
- Discord CDN: {attachment.url}
"""
        note_path.write_text(note, encoding="utf-8")
        saved_notes.append(note_path)
        print(f"[AttachmentCapture] saved: {raw_path}", flush=True)

    return saved_notes


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
            # 60초 타임아웃 — 텍스트 채널에 오류 알림
            text_ch = _voice_text_ch.get(guild_id)
            if text_ch:
                try:
                    await text_ch.send("⚠️ [TTS] 음성 재생 타임아웃 (60초 초과). 텍스트로 응답합니다.")
                except Exception:
                    pass
            print("[TTS] 재생 타임아웃 (60s)", flush=True)
        except Exception as e:
            # 재생 오류 — 텍스트 채널에 오류 알림
            text_ch = _voice_text_ch.get(guild_id)
            if text_ch:
                try:
                    await text_ch.send(f"⚠️ [TTS] 음성 재생 오류: {e}")
                except Exception:
                    pass
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
            # STT 일시정지 중이면 오디오 수집 무시
            if _voice_paused.get(self.guild_id, False):
                return
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

                # 음성 태스크 자동 감지: 태스크 키워드 포함 시 AgentBus에 자동 등록
                if _is_voice_task(text) and _WORKER_POOL_ENABLED and tq:
                    try:
                        vtask = tq.add(text[:60], text, None, "voice")
                        pool = _get_worker_pool()
                        pool.submit(vtask)
                        await ch.send(
                            f"📋 **음성 태스크 감지** — `{vtask['id']}` 자동 등록\n"
                            f"> {vtask['title'][:60]}"
                        )
                    except Exception as _ve2:
                        print(f"[VoiceOrchestrator] 태스크 자동 등록 실패: {_ve2}", flush=True)

                thinking_msg = await ch.send("🔍 RAG 지식 검색 중... _(⏱ 0초)_")
                _stop = asyncio.Event()
                _anim = asyncio.create_task(_animate_thinking(thinking_msg, _stop))
                try:
                    voice_channel_id = str(ch.id)
                    reply = await ask_bucky(voice_channel_id, text)
                finally:
                    _stop.set()
                    _anim.cancel()
                voice_chunks = split_message(reply)
                try:
                    await thinking_msg.edit(content=voice_chunks[0])
                except discord.errors.NotFound:
                    await ch.send(voice_chunks[0])
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
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=15,
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


def _classify_intent_sync(user_message: str, recent_history: list[dict]) -> dict:
    """Pass 1 — Haiku로 메시지 의도 분류 (빠른 사전 호출).

    Returns dict with keys:
      intent: COMMAND | QUESTION | AMBIGUOUS | SMALL_TALK | EMOTIONAL
      context_need: HIGH | MEDIUM | LOW
      tone: FORMAL | CASUAL
      topic: list[str]
      quick_answer: str  (context_need=LOW일 때 직접 답변 후보)
    """
    recent_turns = "\n".join(
        f"{item['role'].title()}: {item['content'][:300]}"
        for item in recent_history[-4:]
    )
    classify_prompt = (
        "사용자 메시지 의도를 분류하라. JSON 한 줄만 출력하라. 설명 없이.\n\n"
        f"최근 대화:\n{recent_turns}\n\n"
        f"새 메시지: {user_message[:600]}\n\n"
        '출력 형식 (반드시 이 JSON 한 줄만):\n'
        '{"intent":"COMMAND|QUESTION|AMBIGUOUS|SMALL_TALK|EMOTIONAL",'
        '"context_need":"HIGH|MEDIUM|LOW","tone":"FORMAL|CASUAL",'
        '"topic":["project"|"system"|"general"|"code"|"deploy"|"architecture"|"strategy"],'
        '"difficulty":"simple|medium|complex",'
        '"quick_answer":""}\n\n'
        "분류 기준:\n"
        "- COMMAND: 구체적 실행 요청 (만들어/수정/배포/고쳐 등)\n"
        "- QUESTION: 정보 조회, how/what/why\n"
        "- AMBIGUOUS: 여러 해석 가능, 불명확\n"
        "- SMALL_TALK: 짧은 확인/감사/단순 yes-no\n"
        "- EMOTIONAL: 감정/의견/불만/칭찬\n"
        "- context_need HIGH: 시스템 상태·프로젝트 지식 필수\n"
        "- context_need MEDIUM: 일부 프로젝트 배경 있으면 좋음\n"
        "- context_need LOW: 일반 지식으로 답변 가능\n"
        "- difficulty simple: 짧은 답변, 상태 확인, yes/no, 간단한 설명\n"
        "- difficulty medium: 일반 코딩·편집·대화·문서 작성\n"
        "- difficulty complex: 아키텍처 설계·디버깅·전략·멀티스텝 추론·보안 분석\n"
        "- quick_answer: LOW일 때 짧게 답변 가능하면 채움, 아니면 빈 문자열"
    )
    try:
        raw = run_bucky(classify_prompt, task_type="classify")
        import json as _json, re as _re
        m = _re.search(r"\{[^{}]+\}", raw, _re.DOTALL)
        if m:
            parsed = _json.loads(m.group())
            parsed.setdefault("intent", "AMBIGUOUS")
            parsed.setdefault("context_need", "HIGH")
            parsed.setdefault("tone", "CASUAL")
            parsed.setdefault("topic", [])
            parsed.setdefault("difficulty", "medium")
            parsed.setdefault("quick_answer", "")
            return parsed
    except Exception as _e:
        print(f"[2-pass] 분류 실패: {_e}", flush=True)
    return {"intent": "AMBIGUOUS", "context_need": "HIGH", "tone": "CASUAL", "topic": [], "difficulty": "medium", "quick_answer": ""}


def _trim_context_for_medium(full_context: str, max_chars: int = 4000) -> str:
    """MEDIUM context_need: 사용자 프로필 + 라우팅 기준 + 현재 임무 섹션만 발췌."""
    lines = full_context.splitlines()
    result, chars = [], 0
    keep_sections = {"1.", "2.", "5.", "6.", "9.", "##"}
    in_keep = False
    for line in lines:
        stripped = line.strip()
        if any(stripped.startswith(s) for s in keep_sections) or stripped.startswith("## "):
            in_keep = True
        if in_keep:
            result.append(line)
            chars += len(line)
            if chars >= max_chars:
                break
    return "\n".join(result) if result else full_context[:max_chars]


async def ask_bucky(
    channel_id: str,
    user_message: str,
    session_key: str | None = None,
    session_label: str | None = None,
) -> str:
    """Bucky Agent에 질문하고 답변 반환. 2-pass: Haiku 의도 분류 → Sonnet 응답."""
    prev_session_context = ""
    try:
        import bucky_memory as _mem
        if session_key:
            session_id = await asyncio.to_thread(
                _mem.get_or_create_session_for_key,
                channel_id,
                session_key,
                session_label or "",
            )
        else:
            session_id = await asyncio.to_thread(_mem.get_active_session, channel_id)
        history = await asyncio.to_thread(_mem.load_session_history, channel_id, session_id)
        if not history:
            prev_ctx = await asyncio.to_thread(_mem.get_prev_session_context, channel_id, session_id)
            if prev_ctx:
                prev_session_context = prev_ctx
        _use_mem = True
    except Exception:
        history = conversation_history[channel_id]
        _use_mem = False

    # ── Pass 1: Haiku 의도 분류 (NLP hint와 병행) ────────────────────────────
    intent_result = await asyncio.to_thread(_classify_intent_sync, user_message, list(history))
    intent = intent_result.get("intent", "AMBIGUOUS")
    context_need = intent_result.get("context_need", "HIGH")
    tone = intent_result.get("tone", "CASUAL")
    difficulty = intent_result.get("difficulty", "medium")
    topic = intent_result.get("topic", [])
    quick_answer = intent_result.get("quick_answer", "").strip()

    # Pass 2 task_type 결정: intent + difficulty + topic → 모델 라우팅
    _topic_set = set(topic) if isinstance(topic, list) else set()
    if intent in ("SMALL_TALK",) or (context_need == "LOW" and difficulty == "simple"):
        _p2_task_type = "status"           # Haiku
    elif difficulty == "complex" or "architecture" in _topic_set or "strategy" in _topic_set:
        _p2_task_type = "reasoning"        # Opus
    elif intent == "COMMAND" and "deploy" in _topic_set:
        _p2_task_type = "implementation"   # Sonnet
    elif intent == "COMMAND" or "code" in _topic_set:
        _p2_task_type = "code"             # Sonnet
    else:
        _p2_task_type = "chat"             # Sonnet

    print(f"[2-pass] intent={intent} context={context_need} tone={tone} difficulty={difficulty} → task={_p2_task_type}", flush=True)

    # NLP 전처리 (기존 COMMAND 감지 — 보완적으로 유지)
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

    # ── SMALL_TALK + LOW + quick_answer → Pass 2 생략 (히스토리 없을 때만) ─────
    if intent == "SMALL_TALK" and context_need == "LOW" and quick_answer and len(history) <= 1:
        reply = quick_answer
        if _use_mem:
            await asyncio.to_thread(_mem.save_message, channel_id, "assistant", reply)
        else:
            history.append({"role": "assistant", "content": reply})
        return reply

    transcript = "\n".join(
        f"{item['role'].title()}: {item['content']}" for item in history
    )

    # RAG: LOW context 또는 단순 메시지는 생략
    if context_need == "LOW" or _should_skip_rag(user_message):
        rag_block = ""
    else:
        rag_context = await asyncio.to_thread(_get_rag_context, user_message)
        rag_block = f"\n\n{rag_context}" if rag_context else ""

    # ── Pass 2 컨텍스트 선택 (context_need 기반) ────────────────────────────
    full_context = _load_agent_context(channel_id, user_message)
    if context_need == "LOW":
        bucky_context = ""
    elif context_need == "MEDIUM":
        bucky_context = _trim_context_for_medium(full_context)
    else:
        bucky_context = full_context

    # Pass 1 결과를 Pass 2 지시문에 주입 — Bucky가 맥락/어조를 정확히 파악하게
    intent_hint = (
        f"[의도 분석: {intent} | 컨텍스트 필요도: {context_need} | 어조: {tone}]\n"
        f"응답 지침: "
        + {
            "COMMAND": "구체적 실행 계획과 증거를 포함해 답하라.",
            "QUESTION": "핵심 정보를 먼저, 배경은 그 다음에 제시하라.",
            "AMBIGUOUS": "먼저 이해한 내용을 한 문장으로 확인하고 답하라.",
            "SMALL_TALK": "1~2문장으로 간결하게 답하라.",
            "EMOTIONAL": "사용자의 감정/의견을 먼저 인정하고, 실질적 도움을 제안하라.",
        }.get(intent, "상황에 맞게 판단해 답하라.")
    )

    session_anchor = (
        "# Active dashboard session\n\n"
        f"- key: {session_key}\n"
        f"- label: {session_label or ''}\n\n"
        "---\n\n"
        if session_key else ""
    )
    prev_ctx_block = (
        f"\n\n# 이전 세션 컨텍스트 (참고용)\n\n{prev_session_context}\n\n---\n\n"
        if prev_session_context else ""
    )

    context_section = (
        "# Bucky 운영 컨텍스트\n\n"
        f"{bucky_context}\n\n"
        "---\n\n"
        if bucky_context else ""
    )

    prompt = (
        f"{context_section}"
        f"{prev_ctx_block}"
        f"{session_anchor}"
        "# Discord 대화\n\n"
        f"{intent_hint}\n"
        "실행 작업이면 '요약→실행안→저장위치→다음행동' 순서로, 단순 질문이면 간결하게."
        f"{rag_block}\n\n"
        f"{transcript}"
    )
    # task_type은 Pass 1 분류 결과로 결정. 한도 초과 시 자동 폴백 체인 작동
    reply = await asyncio.to_thread(run_bucky, prompt, task_type=_p2_task_type)

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

        dev_btn = discord.ui.Button(
            label="개발요청",
            style=discord.ButtonStyle.primary,
            custom_id="wk_dev_request",
        )
        dev_btn.callback = self._on_dev_request

        link = p.get("link", "")
        if link and link.startswith("http"):
            link_btn = discord.ui.Button(
                label="🔗 공고 보기",
                style=discord.ButtonStyle.link,
                url=link,
            )
            self.add_item(link_btn)

        self.add_item(apply_btn)
        self.add_item(dev_btn)
        self.add_item(skip_btn)

    def _make_embed(self) -> discord.Embed:
        p = self.projects[self.idx]
        source_tag = "📧 Gmail" if p.get("source") == "gmail" else "🌐 Web"
        score = p.get("score", 0)
        priority = p.get("priority", "")
        priority_color = {
            "P1": 0x3FB950,  # green
            "P2": 0x58A6FF,  # blue
            "P3": 0xD29922,  # yellow
            "P4": 0x8B949E,  # grey
        }.get(priority, 0x00B4D8)
        embed = discord.Embed(
            title=p["title"][:256],
            url=p.get("link") or discord.utils.MISSING,
            color=priority_color,
        )
        score_val = f"{priority} {score}점" if score and priority else p.get("budget", "미정")
        embed.add_field(name="적합도", value=score_val, inline=True)
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

    async def _on_dev_request(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(thinking=True)
        p = self.projects[self.idx]
        try:
            result = await _wishket_dev_request_to_queue(
                {
                    "type": "wishket_development_request",
                    "source": "wishket_discord_dashboard",
                    "project_title": p.get("title", ""),
                    "summary": p.get("description", ""),
                    "budget": p.get("budget", ""),
                    "url": p.get("link", ""),
                }
            )
            payload, plan, routed_path, route_mode, actions = (
                result["payload"], result["plan"], result["routed_path"], result["route_mode"], result["actions"]
            )
            if route_mode == "immediate":
                await interaction.followup.send(
                    "**Wishket development request accepted**\n"
                    f"- slug: `{payload['project_slug']}`\n"
                    f"- local folder: `{plan['local_project']['target']}`\n"
                    f"- route: `{route_mode}` -> `{routed_path.name}`\n"
                    f"- immediate: {', '.join(actions['immediate']) or 'none'}\n"
                    f"- approval_required: {', '.join(actions['approval_required']) or 'none'}\n\n"
                    f"{_format_wishket_route_instruction(route_mode)}"
                )
                return
            await interaction.followup.send(
                "**Wishket 개발요청 접수**\n"
                f"- slug: `{payload['project_slug']}`\n"
                f"- local folder: `{plan['local_project']['target']}`\n"
                f"- route: `{route_mode}` → `{routed_path.name}`\n"
                f"- 즉시: {', '.join(actions['immediate']) or '없음'}\n"
                f"- 승인필요: {', '.join(actions['approval_required']) or '없음'}\n\n"
                "`!pending` / `!approve <번호>`로 처리."
            )
        except Exception as e:
            await interaction.followup.send(f"Wishket 개발요청 처리 실패: {e}")

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
                    capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=str(ROOT),
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
                capture_output=True, text=True, encoding="utf-8", errors="replace",
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

    @voice_group.command(name="pause", description="STT 인식 일시정지 — 채널에 있지만 Bucky가 음성을 처리하지 않습니다")
    async def cmd_voice_pause(interaction: discord.Interaction) -> None:
        guild_id = interaction.guild_id or 0
        if guild_id not in _voice_clients:
            await interaction.response.send_message("ℹ️ 현재 음성 채널에 연결되어 있지 않습니다.", ephemeral=True)
            return
        if _voice_paused.get(guild_id, False):
            await interaction.response.send_message("⏸️ 이미 음성 휴식 중입니다. `/voice resume` 으로 재개하세요.", ephemeral=True)
            return
        _voice_paused[guild_id] = True
        await interaction.response.send_message("⏸️ **음성 휴식 시작** — STT 처리를 일시정지했습니다.\n채널에 머물면서 말씀하셔도 기록하지 않습니다.\n재개하려면 `/voice resume` 을 사용하세요.", ephemeral=False)

    @voice_group.command(name="resume", description="STT 인식 재개 — 음성 휴식 종료 후 다시 Bucky가 응답합니다")
    async def cmd_voice_resume(interaction: discord.Interaction) -> None:
        guild_id = interaction.guild_id or 0
        if guild_id not in _voice_clients:
            await interaction.response.send_message("ℹ️ 현재 음성 채널에 연결되어 있지 않습니다.", ephemeral=True)
            return
        if not _voice_paused.get(guild_id, False):
            await interaction.response.send_message("▶️ 이미 음성 인식 활성 상태입니다.", ephemeral=True)
            return
        _voice_paused[guild_id] = False
        await interaction.response.send_message("▶️ **음성 인식 재개** — 이제 말씀하시면 Bucky가 다시 응답합니다.", ephemeral=False)

    @voice_group.command(name="status", description="현재 음성 채널 연결 상태를 확인합니다")
    async def cmd_voice_status(interaction: discord.Interaction) -> None:
        guild_id = interaction.guild_id or 0
        vc = _voice_clients.get(guild_id)
        lines = ["**[음성 채널 상태]**"]
        if vc and vc.is_connected():
            members_in_vc = [m.display_name for m in vc.channel.members if not m.bot]
            paused = _voice_paused.get(guild_id, False)
            lines.append(f"🔊 채널: **{vc.channel.name}**")
            lines.append(f"🎤 참여자: {', '.join(members_in_vc) if members_in_vc else '없음'}")
            lines.append(f"⏸️ STT 상태: {'**휴식 중** (일시정지)' if paused else '▶️ 활성'}")
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
    """jh-chat + intake 채널 자동 생성. (deprecated: jh-tasks/jh-status/jh-results/jh-briefing 삭제 2026-06-09)"""
    global JH_CHAT_CHANNEL_ID
    global JH_REPO_DASHBOARD_CHANNEL_ID, JH_WISHKET_CHANNEL_ID, JH_KMONG_CHANNEL_ID, JH_MYINTRO_CHANNEL_ID, JH_DAILYPLUS_CHANNEL_ID, JH_TASKBOARD_CHANNEL_ID
    global JH_CHRIS_CHANNEL_ID, JH_CHARLIE_CHANNEL_ID
    global JH_CLAUDE_CODE_CHANNEL_ID, JH_CODEX_CHANNEL_ID
    if not client.guilds:
        return
    guild = client.guilds[0]
    _specs = [
        ("jh-chat",         "JH_CHAT_CHANNEL_ID",           "💬 JH ↔ Bucky 대화 전용"),
        ("jh-레포대시보드",  "JH_REPO_DASHBOARD_CHANNEL_ID", "📦 Repo 대시보드 → Bucky 라우팅"),
        ("jh-위시켓",        "JH_WISHKET_CHANNEL_ID",        "💼 Wishket 개발요청 전용"),
        ("jh-크몽수익화",    "JH_KMONG_CHANNEL_ID",          "Kmong monetization dashboard and Bucky workflow"),
        ("jh-내소개",        "JH_MYINTRO_CHANNEL_ID",        "🤝 내 소개 페이지 협업 문의"),
        ("jh-오늘의플러스",  "JH_DAILYPLUS_CHANNEL_ID",      "📅 Daily Plus → Bucky 브리핑"),
        ("jh-태스크보드",    "JH_TASKBOARD_CHANNEL_ID",      "📋 태스크보드 → Bucky 라우팅"),
        ("jh-chris",         "JH_CHRIS_CHANNEL_ID",          "💡 Chris Graphify 지식 입력/태그 선택 요청"),
        ("jh-charlie",       "JH_CHARLIE_CHANNEL_ID",        "Charlie system audit, home PC continuity, drift warnings, and user confirmations"),
        ("jh-클로드코드앱",  "JH_CLAUDE_CODE_CHANNEL_ID",    "🤖 Claude Code 앱 세션 요청/상태 보고"),
        ("jh-코덱스앱",      "JH_CODEX_CHANNEL_ID",          "🔍 Codex 앱 세션 요청/상태 보고"),
    ]
    _globals = globals()
    for ch_name, env_key, topic in _specs:
        ch_id = _globals[env_key]
        if ch_id:
            existing = discord.utils.get(guild.text_channels, id=int(ch_id))
            if existing and existing.name != ch_name:
                try:
                    await existing.edit(name=ch_name)
                    print(f"[Setup] #{existing.name} -> #{ch_name} rename OK", flush=True)
                except Exception as e:
                    print(f"[Setup] #{ch_name} rename FAIL: {e}", flush=True)
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

    # ── 핵심 JH 채널(chat): ALLOWED_CHANNELS 등록 + .env 영구 저장 ──
    if JH_CHAT_CHANNEL_ID:
        ALLOWED_CHANNELS.add(JH_CHAT_CHANNEL_ID)
        _persist_env_key("JH_CHAT_CHANNEL_ID", JH_CHAT_CHANNEL_ID)

    # ── intake 채널: ALLOWED_CHANNELS 등록 + .env 영구 저장 ──────────────────────
    _intake_env_keys = [
        ("JH_REPO_DASHBOARD_CHANNEL_ID", JH_REPO_DASHBOARD_CHANNEL_ID),
        ("JH_WISHKET_CHANNEL_ID",        JH_WISHKET_CHANNEL_ID),
        ("JH_KMONG_CHANNEL_ID",          JH_KMONG_CHANNEL_ID),
        ("JH_MYINTRO_CHANNEL_ID",        JH_MYINTRO_CHANNEL_ID),
        ("JH_DAILYPLUS_CHANNEL_ID",      JH_DAILYPLUS_CHANNEL_ID),
        ("JH_TASKBOARD_CHANNEL_ID",      JH_TASKBOARD_CHANNEL_ID),
        ("JH_CHRIS_CHANNEL_ID",          JH_CHRIS_CHANNEL_ID),
        ("JH_CHARLIE_CHANNEL_ID",        JH_CHARLIE_CHANNEL_ID),
        ("JH_CLAUDE_CODE_CHANNEL_ID",    JH_CLAUDE_CODE_CHANNEL_ID),
        ("JH_CODEX_CHANNEL_ID",          JH_CODEX_CHANNEL_ID),
    ]
    for _env_key, _ch_id in _intake_env_keys:
        if _ch_id:
            ALLOWED_CHANNELS.add(_ch_id)
            _persist_env_key(_env_key, _ch_id)

    # ── [deprecated] 레거시 작업 채널 (jh-work-1, jh-work-2) ────────────────────
    # 폐기됨: 앱 채널(jh-클로드코드앱, jh-코덱스앱)로 대체.
    # 신규 생성 중단. 기존 채널이 남아있으면 .env에서 JH_WORK_CHANNEL_IDS 항목을 직접 제거하세요.
    _legacy_work_names = {"jh-work-1", "jh-work-2"}
    known_work_channel_ids: set[str] = set()
    for ch_name in _legacy_work_names:
        existing = discord.utils.get(guild.text_channels, name=ch_name)
        if existing:
            ch_id = str(existing.id)
            known_work_channel_ids.add(ch_id)
            if ch_id not in JH_WORK_CHANNEL_IDS:
                JH_WORK_CHANNEL_IDS.add(ch_id)
                ALLOWED_CHANNELS.add(ch_id)
            print(
                f"[Setup] #{ch_name} 발견(레거시): {existing.id} — "
                ".env JH_WORK_CHANNEL_IDS 에서 이 ID를 제거하면 비활성화됩니다.",
                flush=True,
            )

    stale_work_channel_ids = JH_WORK_CHANNEL_IDS - known_work_channel_ids
    if stale_work_channel_ids:
        JH_WORK_CHANNEL_IDS.intersection_update(known_work_channel_ids)
        ALLOWED_CHANNELS.difference_update(stale_work_channel_ids)
        print(
            "[Setup] stale JH_WORK_CHANNEL_IDS ignored: "
            + ",".join(sorted(stale_work_channel_ids)),
            flush=True,
        )

    # 작업 채널 ID .env 영구 저장 (재시작 시 유지)
    # stale_work_channel_ids가 있으면 JH_WORK_CHANNEL_IDS가 빈 set이 돼도 .env를 갱신해야 한다.
    # 갱신하지 않으면 .env에 stale 값이 남아 다음 재시작 시 재로드된다.
    if JH_WORK_CHANNEL_IDS or stale_work_channel_ids:
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


def _build_dashboard_execution_body(payload: dict) -> str:
    dashboard_type = str(payload.get("dashboard_type") or "dashboard")
    action = str(payload.get("action") or "execute")
    title = str(payload.get("title") or payload.get("summary") or action)
    request_id = str(payload.get("request_id") or "")
    source_url = str(payload.get("source_dashboard_url") or "")
    body = str(payload.get("body") or payload.get("summary") or "")
    return (
        f"[Dashboard Execution]\n"
        f"dashboard_type: {dashboard_type}\n"
        f"action: {action}\n"
        f"request_id: {request_id}\n"
        f"title: {title}\n"
        + (f"source_dashboard_url: {source_url}\n" if source_url else "")
        + "\n"
        + body
    ).strip()


async def _dispatch_dashboard_execution_task(payload: dict, channel) -> dict | None:
    """Dashboard execute action: enqueue real worker task instead of waiting for chat reply."""
    if not _WORKER_POOL_ENABLED or tq is None or _get_worker_pool is None:
        if channel:
            await channel.send("⚠️ 작업 큐가 비활성화되어 실행 태스크를 시작할 수 없습니다.")
        return None

    task_body = _build_dashboard_execution_body(payload)
    title = str(payload.get("title") or payload.get("action") or "dashboard execute")
    task = tq.add(title[:80], task_body, "claude", source="dashboard-intake")
    pool = _get_worker_pool()
    origin_ch_id = int(channel.id) if channel else None
    pool.register_task(task, origin_channel_id=origin_ch_id)
    pool.submit(task)
    if channel:
        await channel.send(
            f"🚀 **실행 태스크 등록 완료** `{task['id']}` → Claude worker\n"
            f"- request_id: `{str(payload.get('request_id') or '')[:12]}`\n"
            "작업 시작/완료 상태는 이 채널에 이어서 표시됩니다."
        )
    return task


def _build_repo_intake_ack(payload: dict) -> str:
    action = str(payload.get("action") or "start")
    request_id = str(payload.get("request_id") or "")
    title = str(payload.get("title") or payload.get("repo") or payload.get("item_id") or "repo")
    summary = str(payload.get("summary") or "").strip()
    url = str(payload.get("url") or "").strip()
    score = payload.get("score")

    lines = [
        f"**[Repo Dashboard] 작업구현 브리핑 준비** `{action}`",
        f"- 레포: `{title}`",
    ]
    if summary:
        lines.append(f"- 요청 액션: {summary[:240]}")
    if url:
        lines.append(f"- 링크: {url}")
    if score not in (None, ""):
        lines.append(f"- 대시보드 점수: {score}")
    if request_id:
        lines.append(f"- request_id: `{request_id[:12]}`")
    lines.append("")
    lines.append("Bucky가 구현 목표와 첫 작업 단계를 브리핑합니다. 사용자는 이 채널에서 음성 또는 채팅으로 다음 지시를 이어가면 됩니다.")
    return "\n".join(lines)


def _build_repo_intake_prompt(payload: dict) -> str:
    action = str(payload.get("action") or "start")
    request_id = str(payload.get("request_id") or "")
    title = str(payload.get("title") or payload.get("repo") or payload.get("item_id") or "repo")
    instruction = str(payload.get("briefing_instruction") or "").strip()
    summary = str(payload.get("summary") or "").strip()
    description = str(payload.get("repo_description") or payload.get("description") or "").strip()
    reason = str(payload.get("reason") or "").strip()
    url = str(payload.get("url") or "").strip()
    source_url = str(payload.get("source_dashboard_url") or "").strip()
    dashboard_context = payload.get("dashboard_context")
    items = payload.get("items")

    lines = [
        "[Repo Dashboard Implementation Briefing]",
        f"action: {action}",
        f"request_id: {request_id}",
        f"repo: {title}",
    ]
    if url:
        lines.append(f"url: {url}")
    if source_url:
        lines.append(f"source_dashboard_url: {source_url}")
    for key in ("language", "status", "tier", "category", "completion", "market", "score"):
        value = payload.get(key)
        if value not in (None, ""):
            lines.append(f"{key}: {value}")
    if summary:
        lines.extend(["", "## Requested action", summary])
    if description:
        lines.extend(["", "## Repo description", description])
    if reason:
        lines.extend(["", "## Dashboard reason", reason])
    if isinstance(dashboard_context, dict):
        lines.append("")
        lines.append("## Overall repo dashboard context")
        for key in ("total_repos", "active_repos", "tier_counts", "planning_goal"):
            value = dashboard_context.get(key)
            if value not in (None, ""):
                lines.append(f"{key}: {value}")
        top_repos = dashboard_context.get("top_repos")
        if isinstance(top_repos, list) and top_repos:
            lines.append("top_repos:")
            for idx, repo in enumerate(top_repos[:8], 1):
                if not isinstance(repo, dict):
                    continue
                lines.append(
                    f"{idx}. {repo.get('name') or repo.get('id')} "
                    f"(score={repo.get('score')}, tier={repo.get('tier')}) - {repo.get('action') or ''}"
                )
    if instruction:
        lines.extend(["", "## Required user-facing behavior", instruction])
    if isinstance(items, list) and items:
        lines.append("")
        lines.append("## Batch items")
        for idx, item in enumerate(items, 1):
            if not isinstance(item, dict):
                continue
            item_line = f"{idx}. {item.get('name') or item.get('id')}: {item.get('action') or ''}"
            if item.get("url"):
                item_line += f" ({item.get('url')})"
            lines.append(item_line)
    lines.extend(
        [
            "",
            "## Output",
            "한국어로 사용자에게 바로 보여줄 작업구현 브리핑을 작성하세요.",
            "먼저 전체 개발 레포 현황을 요약하고, 그 다음 선택된 레포 또는 일괄 항목의 다음 플랜을 미리 정의하세요.",
            "포함: 전체 포트폴리오 우선순위, 구현 목표, 첫 작업 후보 2-3개, 확인해야 할 질문, 사용자가 음성/채팅으로 지시하면 이어서 진행한다는 안내.",
            "아직 코드를 수정하거나 외부 배포를 시작하지 말고, 사용자의 다음 지시를 기다리는 형태로 끝내세요.",
        ]
    )
    return "\n".join(lines).strip()


async def _handle_jh_tasks(message: Message) -> None:
    """#jh-tasks 전용 핸들러 — Claude 거치지 않고 즉시 태스크 배정."""
    content = message.content.strip()

    # ── 현황 ──────────────────────────────────────────────────────────────────
    if content in ("!현황", "!status", "!tasks"):
        pool = _get_worker_pool()
        await message.channel.send(pool.get_board_text())
        return

    # ── AgentBus 승인 게이트 ───────────────────────────────────────────────────
    if content in ("!pending", "!승인목록", "!approval"):
        try:
            import approve_task as _at
            items = await asyncio.to_thread(_at.list_pending_dicts)
            if not items:
                await message.channel.send("⏸ 승인 대기 태스크 없음.")
                return
            lines = [f"⏸ **승인 대기 태스크** ({len(items)}개)\n"]
            for it in items:
                queued = it["queued_at"][:16] if it["queued_at"] else "-"
                lines.append(
                    f"`[{it['idx']}]` `{it['type']}` — {it['stem'][:50]}\n"
                    f"      queued: {queued}  {it['approval_note'][:50]}"
                )
            lines.append("\n`!approve <번호>` / `!reject <번호>` 로 처리")
            await message.channel.send("\n".join(lines))
        except Exception as e:
            await message.channel.send(f"⚠️ 승인 목록 조회 실패: {e}")
        return

    if content.startswith("!approve ") or content.startswith("!승인 "):
        key = content.split(None, 1)[1].strip() if len(content.split(None, 1)) > 1 else ""
        if not key:
            await message.channel.send("사용법: `!approve <번호 또는 이름>`")
            return
        try:
            import approve_task as _at
            result = await asyncio.to_thread(_at.approve_by_key, key)
            if result["ok"]:
                await message.channel.send(
                    f"✅ **승인 완료** — `{result['name']}`\n"
                    f"   → inbox/ 로 이동 (재처리 예약)"
                )
            else:
                await message.channel.send(f"⚠️ 승인 실패: {result['error']}")
        except Exception as e:
            await message.channel.send(f"⚠️ 오류: {e}")
        return

    if content.startswith("!reject ") or content.startswith("!거절 "):
        parts = content.split(None, 2)
        key = parts[1].strip() if len(parts) > 1 else ""
        reason = parts[2].strip() if len(parts) > 2 else ""
        if not key:
            await message.channel.send("사용법: `!reject <번호 또는 이름> [사유]`")
            return
        try:
            import approve_task as _at
            result = await asyncio.to_thread(_at.reject_by_key, key, reason)
            if result["ok"]:
                reason_str = f" — {reason}" if reason else ""
                await message.channel.send(
                    f"❌ **거절 완료** — `{result['name']}`{reason_str}\n"
                    f"   → failed/ 로 이동"
                )
            else:
                await message.channel.send(f"⚠️ 거절 실패: {result['error']}")
        except Exception as e:
            await message.channel.send(f"⚠️ 오류: {e}")
        return

    # ── 승인 게이트: 태스크 상세 조회 (!show) ─────────────────────────────────
    if content.startswith("!show ") or content.startswith("!pending-show "):
        prefix = "!pending-show " if content.startswith("!pending-show ") else "!show "
        key = content[len(prefix):].strip()
        if not key:
            await message.channel.send("사용법: `!show <번호 또는 이름>`")
            return
        try:
            import approve_task as _at
            tasks = sorted(_at.PENDING.glob("*.md"))
            if key.isdigit():
                idx = int(key)
                if 1 <= idx <= len(tasks):
                    path = tasks[idx - 1]
                else:
                    await message.channel.send(f"⚠️ 번호 범위 초과 (1~{len(tasks)})")
                    return
            else:
                key_lower = key.lower()
                matches = [t for t in tasks if key_lower in t.stem.lower()]
                if not matches:
                    await message.channel.send(f"⚠️ `{key}` 해당 태스크 없음.")
                    return
                if len(matches) > 1:
                    await message.channel.send(f"⚠️ `{key}` 모호한 키 — {len(matches)}개 매칭")
                    return
                path = matches[0]
            text = path.read_text(encoding="utf-8", errors="replace")
            if len(text) > 1800:
                text = text[:1800] + "\n... (이하 생략)"
            await message.channel.send(f"📄 **{path.name}**\n```yaml\n{text}\n```")
        except Exception as e:
            await message.channel.send(f"⚠️ 태스크 조회 실패: {e}")
        return

    # ── 태스크 취소 ───────────────────────────────────────────────────────────
    if content.startswith(("!취소 ", "!cancel ")):
        prefix = "!취소 " if content.startswith("!취소 ") else "!cancel "
        tid = content[len(prefix):].strip()
        if not tid:
            await message.channel.send("사용법: `!취소 <태스크ID>`")
            return
        if not _WORKER_POOL_ENABLED:
            await message.channel.send("⚠️ 워커풀 비활성화")
            return
        try:
            pool = _get_worker_pool()
            result = pool.cancel_task(tid)
            if result["ok"]:
                await message.channel.send(f"🚫 **취소 완료** — `{tid}`")
            else:
                await message.channel.send(f"⚠️ 취소 실패: {result['error']}")
        except Exception as e:
            await message.channel.send(f"⚠️ 오류: {e}")
        return

    # ── 태스크 재시도 ──────────────────────────────────────────────────────────
    if content.startswith(("!재시도 ", "!retry ")):
        prefix = "!재시도 " if content.startswith("!재시도 ") else "!retry "
        tid = content[len(prefix):].strip()
        if not tid:
            await message.channel.send("사용법: `!재시도 <태스크ID>`")
            return
        if not _WORKER_POOL_ENABLED:
            await message.channel.send("⚠️ 워커풀 비활성화")
            return
        try:
            pool = _get_worker_pool()
            result = pool.retry_task(tid)
            if result["ok"]:
                await message.channel.send(
                    f"🔄 **재시도 등록** — 새 ID: `{result['new_id']}`\n"
                    f"원본: `{tid}` → 자동 라우팅 재배정"
                )
            else:
                await message.channel.send(f"⚠️ 재시도 실패: {result['error']}")
        except Exception as e:
            await message.channel.send(f"⚠️ 오류: {e}")
        return

    # ── !buki 서브커맨드 ───────────────────────────────────────────────────────
    if content.startswith("!buki ") or content == "!buki":
        subcmd = content[6:].strip() if content.startswith("!buki ") else ""

        # !buki startproject <name> [— desc]
        if subcmd.startswith("startproject"):
            body = subcmd[12:].strip()
            if not body:
                await message.channel.send(
                    "사용법: `!buki startproject <프로젝트명>`\n"
                    "또는: `!buki startproject <이름> — <설명>`"
                )
                return
            if " — " in body:
                project_name, project_desc = body.split(" — ", 1)
                project_name = project_name.strip()
                project_desc = project_desc.strip()
            elif " - " in body:
                project_name, project_desc = body.split(" - ", 1)
                project_name = project_name.strip()
                project_desc = project_desc.strip()
            else:
                project_name = body
                project_desc = ""
            thinking_msg = await message.channel.send(
                f"🚀 **!buki startproject** — `{project_name}` 계획 생성 중..."
            )
            try:
                bucky_prompt = (
                    f"새 프로젝트를 시작한다: **{project_name}**\n"
                    + (f"설명: {project_desc}\n" if project_desc else "")
                    + "\n아래 형식으로 프로젝트 계획을 Obsidian 마크다운으로 작성하라:\n"
                    "## 목표\n(2~3줄 목적 설명)\n\n"
                    "## 핵심 기능\n(5개 이내 bullet)\n\n"
                    "## 기술 스택\n(제안)\n\n"
                    "## 마일스톤\n"
                    "- Phase 0: ...\n- Phase 1: ...\n- Phase 2: ...\n\n"
                    "## 즉시 액션\n(첫 번째 작업 1개)\n"
                )
                plan_text = await ask_bucky(str(message.channel.id), bucky_prompt)
                import re as _re
                from datetime import datetime as _dt_sp
                slug = _re.sub(r"[^\w가-힣]", "-", project_name).strip("-")[:40]
                today_str = _dt_sp.now().strftime("%Y-%m-%d")
                note_fname = f"{today_str}-{slug}.md"
                fm_desc = project_desc.replace('"', "'") if project_desc else ""
                note_content = (
                    f"---\ntitle: {project_name}\ndate: {today_str}\nstatus: planning\n"
                    + (f'description: "{fm_desc}"\n' if fm_desc else "")
                    + "tags:\n  - project\n  - planning\nsource: buki-startproject\n---\n\n"
                    f"# {project_name}\n\n{plan_text}"
                )
                note_path = VAULT / "03_Projects" / note_fname
                await asyncio.to_thread(
                    note_path.write_text, note_content, "utf-8"
                )
                preview = plan_text[:700] + ("..." if len(plan_text) > 700 else "")
                _msg = (
                    f"✅ **프로젝트 계획 생성 완료** — `{project_name}`\n"
                    f"저장: `03_Projects/{note_fname}`\n\n{preview}"
                )
                try:
                    await thinking_msg.edit(content=_msg)
                except discord.errors.NotFound:
                    await message.channel.send(_msg)
            except Exception as e:
                _err_msg = f"⚠️ startproject 오류: {e}"
                try:
                    await thinking_msg.edit(content=_err_msg)
                except discord.errors.NotFound:
                    await message.channel.send(_err_msg)
            return

        # !buki checkpoint [note]
        if subcmd.startswith("checkpoint"):
            note_text = subcmd[10:].strip()
            thinking_msg = await message.channel.send("💾 **체크포인트 저장 중...**")
            try:
                from datetime import datetime as _dt_cp
                now_cp = _dt_cp.now()
                ts_cp = now_cp.strftime("%Y-%m-%d %H:%M")
                fname_cp = now_cp.strftime("checkpoint-%Y-%m-%d-%H%M.md")
                try:
                    cl_data = await asyncio.to_thread(_cl_list)
                    pending_cl = [t for t in cl_data if t.get("status", "pending") == "pending"][:5]
                    done_cl = [t for t in cl_data if t.get("status") == "done"][-3:]
                except Exception:
                    pending_cl = []
                    done_cl = []
                try:
                    import approve_task as _at2
                    pending_approvals = await asyncio.to_thread(_at2.list_pending_dicts)
                except Exception:
                    pending_approvals = []
                lines_cp = [
                    "---",
                    f"created: {ts_cp}",
                    "type: checkpoint",
                    "tags:",
                    "  - checkpoint",
                    "  - session-log",
                    "---",
                    "",
                    f"# Checkpoint — {ts_cp}",
                    "",
                ]
                if note_text:
                    lines_cp += ["## 메모", "", note_text, ""]
                lines_cp += ["## 체크리스트 현황", ""]
                if pending_cl:
                    lines_cp.append("**미완료**")
                    for t in pending_cl:
                        lines_cp.append(f"- [{t['id']}] {t['title']}")
                if done_cl:
                    lines_cp += ["", "**최근 완료**"]
                    for t in done_cl:
                        lines_cp.append(f"- [{t['id']}] ~~{t['title']}~~")
                if pending_approvals:
                    lines_cp += ["", "## 승인 대기", ""]
                    for it in pending_approvals:
                        lines_cp.append(
                            f"- [{it['idx']}] `{it['type']}` {it['stem'][:50]}"
                        )
                note_path_cp = VAULT / "05_Logs" / fname_cp
                await asyncio.to_thread(
                    note_path_cp.write_text, "\n".join(lines_cp), "utf-8"
                )
                _cp_msg = (
                    f"💾 **체크포인트 저장 완료**\n"
                    f"파일: `05_Logs/{fname_cp}`\n"
                    f"미완료 {len(pending_cl)}개 · 승인대기 {len(pending_approvals)}개"
                )
                try:
                    await thinking_msg.edit(content=_cp_msg)
                except discord.errors.NotFound:
                    await message.channel.send(_cp_msg)
            except Exception as e:
                _cp_err = f"⚠️ checkpoint 오류: {e}"
                try:
                    await thinking_msg.edit(content=_cp_err)
                except discord.errors.NotFound:
                    await message.channel.send(_cp_err)
            return

        # !buki (도움말)
        await message.channel.send(
            "**!buki 서브커맨드**\n"
            "`!buki startproject <이름>` — 새 프로젝트 계획 생성 → Obsidian 저장\n"
            "`!buki startproject <이름> — <설명>` — 설명 포함 계획 생성\n"
            "`!buki checkpoint` — 현재 세션 체크포인트 → `05_Logs/` 저장\n"
            "`!buki checkpoint <메모>` — 메모 포함 체크포인트 저장\n"
        )
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

    # ── 음성 첨부파일 처리 (#jh-chat과 동일한 STT 파이프라인) ──────────────────────
    _AUDIO_EXTS = {".ogg", ".mp3", ".wav", ".m4a", ".webm", ".aac", ".flac"}
    if VOICE_ENABLED and message.attachments:
        for att in message.attachments:
            _is_audio = (
                (att.content_type and att.content_type.startswith("audio/"))
                or Path(att.filename).suffix.lower() in _AUDIO_EXTS
            )
            if _is_audio:
                async with message.channel.typing():
                    try:
                        transcript = await transcribe_discord_audio(att)
                        if transcript:
                            if _NLP_ENABLED:
                                try:
                                    import sys as _sys
                                    if str(Path(__file__).parent) not in _sys.path:
                                        _sys.path.insert(0, str(Path(__file__).parent))
                                    from bucky_nlp_preprocessor import preprocess
                                    nlp_result = await asyncio.to_thread(preprocess, transcript)
                                    voice_text = nlp_result.get("structured_prompt", transcript)
                                    voice_text = f"[음성] {voice_text}"
                                except Exception:
                                    voice_text = f"[음성] {transcript}"
                            else:
                                voice_text = f"[음성] {transcript}"
                            content = f"{content} {voice_text}".strip() if content else voice_text
                        else:
                            await message.channel.send("⚠️ 음성을 인식하지 못했습니다.")
                            return
                    except Exception as e:
                        await message.channel.send(f"⚠️ 음성 인식 실패: {e}")
                        return
                break

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

    # ── !gpt-login: ChatGPT 세션 재연결 (jh-코덱스앱 전용) ───────────────────────
    if content.strip() in ("!gpt-login", "!gpt_login", "!gptlogin"):
        if str(message.channel.id) != JH_CODEX_CHANNEL_ID:
            await message.channel.send("⚠️ `!gpt-login`은 **#jh-코덱스앱** 채널에서만 사용 가능합니다.")
            return
        await message.channel.send("🔐 GPT 크롬 로그인 창을 엽니다. 로그인 완료 후 수집이 자동 재시작됩니다...")
        try:
            import subprocess as _sp
            import sys as _sys
            _scripts = str(Path(__file__).resolve().parent)
            _collector = str(Path(_scripts) / "chatgpt_daily_collector.py")
            _proc = _sp.Popen(
                [_sys.executable, _collector, "--login"],
                cwd=_scripts,
                stdout=_sp.PIPE,
                stderr=_sp.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            await message.channel.send(
                "✅ Chrome 로그인 창 실행됨\n"
                "1. 열린 Chrome에서 ChatGPT에 Google 계정으로 로그인\n"
                "2. 로그인 완료 후 Chrome 닫기\n"
                "3. 다음 수집(06:00 AM)부터 자동 실행됩니다"
            )
        except Exception as _gpt_err:
            await message.channel.send(f"❌ GPT 로그인 실행 실패: {_gpt_err}")
        return

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
    try:
        await thinking_msg.edit(content=chunks[0])
    except discord.errors.NotFound:
        await message.channel.send(chunks[0])
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
            asyncio.create_task(self._daily_briefing_task())

        # 6시간마다 패턴 분석 자동 실행
        asyncio.create_task(self._periodic_pattern_task())
        # 매일 1회 자기 반성 (P2)
        asyncio.create_task(self._periodic_reflection_task())
        # 매일 오전 8:30 Wishket 공고 자동 스캔
        asyncio.create_task(self._wishket_auto_scan_task())
        # 대시보드 intake 큐 소비자 (bucky_chat_server POST /intake → queue file)
        asyncio.create_task(self._intake_queue_consumer_task())
        asyncio.create_task(self._daily_plus_outbox_bridge_task())

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

    async def _daily_plus_outbox_bridge_task(self) -> None:
        """Relay Daily Plus Bucky outbox briefings to the dedicated Discord channel."""
        await self.wait_until_ready()
        sent_names = _load_daily_plus_bridge_state()
        print("[DailyPlusBridge] outbox monitor started", flush=True)

        while not self.is_closed():
            try:
                channel = self.get_channel(int(JH_DAILYPLUS_CHANNEL_ID)) if JH_DAILYPLUS_CHANNEL_ID else None
                if channel and DAILY_PLUS_OUTBOX.exists():
                    files = list(DAILY_PLUS_OUTBOX.glob("*_090000_daily_plus_dashboard_bucky.md"))
                    pending = _pending_daily_plus_briefings(files, sent_names)
                    for path in pending:
                        text = path.read_text(encoding="utf-8", errors="replace")
                        message = _build_daily_plus_briefing_message(path.name, text)
                        for chunk in split_message(message):
                            await channel.send(chunk)
                        sent_names.add(path.name)
                        _save_daily_plus_bridge_state(sent_names)
                        print(f"[DailyPlusBridge] posted {path.name}", flush=True)
            except Exception as exc:
                print(f"[DailyPlusBridge] error: {exc}", flush=True)

            await asyncio.sleep(15)

    async def _intake_queue_consumer_task(self) -> None:
        """Poll data/intake_queue/*.json and route payloads to Discord channels.

        Picks up files written atomically by bucky_chat_server POST /intake.
        Processed files are moved to data/intake_queue/processed/.
        Failed files are moved to data/intake_queue/failed/.
        """
        await self.wait_until_ready()
        import json as _json
        _queue_dir = _ROOT / "data" / "intake_queue"
        _processed_dir = _queue_dir / "processed"
        _failed_dir = _queue_dir / "failed"

        _channel_map = {
            "repo":        lambda: JH_REPO_DASHBOARD_CHANNEL_ID,
            "wishket":     lambda: JH_WISHKET_CHANNEL_ID,
            "kmong":       lambda: JH_KMONG_CHANNEL_ID,
            "collab":      lambda: JH_MYINTRO_CHANNEL_ID or JH_CHAT_CHANNEL_ID,
            "daily_plus":  lambda: JH_DAILYPLUS_CHANNEL_ID,
            "task_board":  lambda: JH_TASKBOARD_CHANNEL_ID,
            "taskboard":   lambda: JH_TASKBOARD_CHANNEL_ID,   # alias: task-board.html
            "checklist":   lambda: JH_TASKBOARD_CHANNEL_ID,   # alias: checklist.html
            "knowledge_intake": lambda: JH_CHRIS_CHANNEL_ID or JH_CHAT_CHANNEL_ID,
            "charlie":     lambda: JH_CHARLIE_CHANNEL_ID or JH_CHAT_CHANNEL_ID,
        }

        print("[IntakeConsumer] 시작", flush=True)
        while not self.is_closed():
            try:
                _queue_dir.mkdir(parents=True, exist_ok=True)
                _processed_dir.mkdir(parents=True, exist_ok=True)
                _failed_dir.mkdir(parents=True, exist_ok=True)

                for queue_file in sorted(_queue_dir.glob("*.json")):
                    try:
                        payload = _json.loads(queue_file.read_text(encoding="utf-8"))
                    except Exception as exc:
                        print(f"[IntakeConsumer] 파일 읽기 실패 {queue_file.name}: {exc}", flush=True)
                        queue_file.rename(_failed_dir / queue_file.name)
                        continue

                    dashboard_type = str(payload.get("dashboard_type") or "").strip()
                    if dashboard_type == "app_session":
                        _target_app = str(payload.get("target_app") or "").strip()
                        ch_id = JH_CODEX_CHANNEL_ID if _target_app == "codex" else JH_CLAUDE_CODE_CHANNEL_ID
                    else:
                        ch_id_getter = _channel_map.get(dashboard_type)
                        ch_id = ch_id_getter() if ch_id_getter else JH_CHAT_CHANNEL_ID
                    channel = self.get_channel(int(ch_id)) if ch_id else None

                    try:
                        await self._process_intake_payload(payload, channel)
                        queue_file.rename(_processed_dir / queue_file.name)
                    except Exception as exc:
                        print(f"[IntakeConsumer] 처리 실패 {queue_file.name}: {exc}", flush=True)
                        try:
                            with (_queue_dir / "consumer_errors.log").open("a", encoding="utf-8") as _f:
                                _f.write(f"{queue_file.name}\t{type(exc).__name__}\t{exc}\tch_id={ch_id!r}\n")
                        except Exception:
                            pass
                        queue_file.rename(_failed_dir / queue_file.name)

            except Exception as exc:
                print(f"[IntakeConsumer] 폴링 오류: {exc}", flush=True)

            await asyncio.sleep(2)

    async def _process_intake_payload(self, payload: dict, channel) -> None:
        """Route a single intake payload to the appropriate Discord channel."""
        dashboard_type = str(payload.get("dashboard_type") or "unknown")
        action = str(payload.get("action") or "")
        title = str(payload.get("title") or payload.get("summary") or "")
        request_id = str(payload.get("request_id") or "")

        # Repo dashboard intake should brief the user with portfolio context,
        # not stop at the generic three-line intake acknowledgement.
        if dashboard_type == "repo" and action in {"start", "batch_start", "analyze", "review"} and channel:
            await _activate_dashboard_session(str(channel.id), payload)
            for chunk in split_message(_build_repo_intake_ack(payload)):
                await channel.send(chunk)
            try:
                timeout_s = int(os.getenv("REPO_INTAKE_BUCKY_TIMEOUT", "60"))
                reply = await asyncio.wait_for(
                    ask_bucky(
                        str(channel.id),
                        _build_repo_intake_prompt(payload),
                        session_key=_dashboard_session_key(payload),
                        session_label=_dashboard_session_label(payload),
                    ),
                    timeout=timeout_s,
                )
                for chunk in split_message(reply):
                    await channel.send(chunk)
            except asyncio.TimeoutError:
                repo_name = title or payload.get("repo", "") or payload.get("item_id", "")
                await channel.send(f"⚠️ Bucky 응답 시간이 초과되었습니다. `{repo_name}` 요청은 수신됐고, 이 채널에서 음성/채팅으로 다음 지시를 이어가면 됩니다.")
            except Exception as exc:
                print(f"[IntakeConsumer] Repo Bucky flow failed: {exc}", flush=True)
                await channel.send(f"⚠️ Bucky 브리핑 실패: `{exc}`")
            return

        briefing = (
            f"**[Intake: {dashboard_type}]** `{action}`\n"
            + (f"> {title[:200]}\n" if title else "")
            + (f"request_id: `{request_id[:8]}`" if request_id else "")
        )

        if channel:
            await _activate_dashboard_session(str(channel.id), payload)
            for chunk in split_message(briefing):
                await channel.send(chunk)
        else:
            print(f"[IntakeConsumer] 채널 없음 — {dashboard_type}/{action}: {title[:60]}", flush=True)

        # health_check는 Bucky 호출 없이 즉시 ACK
        if action == "health_check":
            if channel:
                await channel.send("✅ intake 채널 정상 — Bucky 연결 대기 중. 작업은 이 채널에서 이어서 대화하세요.")
            return

        # 영상 제작 요청 — Higgsfield MCP용 Bucky 프로토콜로 우선 라우팅.
        if await _handle_higgsfield_video_payload(payload, channel):
            return

        # Daily Plus 대시보드 intake — Bucky에게 라우팅해서 응답 전송 (대화 가능 상태)
        if await _handle_dashboard_watch_payload(payload, channel):
            return

        if await _handle_wishket_proposal_request(payload, channel):
            return

        if await _handle_wishket_feedback_payload(payload, channel):
            return

        if await _handle_wishket_proposal_approval_payload(payload, channel):
            return

        if await _handle_collab_proposal_request(payload, channel):
            return

        if await _handle_collab_feedback_payload(payload, channel):
            return

        if await _handle_collab_proposal_approval_payload(payload, channel):
            return

        if dashboard_type == "kmong" and channel:
            safe_actions = payload.get("requested_actions") or []
            if not isinstance(safe_actions, list):
                safe_actions = [str(safe_actions)]
            approval_required = bool(payload.get("approval_required"))
            prompt = (
                "[Kmong monetization dashboard intake]\n"
                f"action: {action}\n"
                f"title: {title}\n"
                f"request_id: {request_id[:12]}\n"
                f"work_state: {payload.get('work_state') or '(none)'}\n"
                f"requested_actions: {', '.join(str(a) for a in safe_actions) or 'none'}\n"
                f"approval_required: {approval_required}\n\n"
                "Rules: use KMONG_EMAIL / KMONG_PASSWORD from runtime only; never ask for or print secrets. "
                "Stop with manual_auth_required on captcha, OTP, 2FA, suspicious-login, or policy challenge. "
                "Draft customer-facing replies, but do not send, accept orders, deliver files, or handle payment without explicit approval.\n\n"
                f"Summary:\n{payload.get('summary') or ''}"
            ).strip()
            try:
                timeout_s = int(os.getenv("KMONG_INTAKE_BUCKY_TIMEOUT", "90"))
                reply = await asyncio.wait_for(
                    ask_bucky(
                        str(channel.id),
                        prompt,
                        session_key=_dashboard_session_key(payload),
                        session_label=_dashboard_session_label(payload),
                    ),
                    timeout=timeout_s,
                )
                for chunk in split_message(reply):
                    await channel.send(chunk)
            except asyncio.TimeoutError:
                await channel.send("Kmong Bucky response timed out. The request was received; continue in #jh-크몽수익화.")
            except Exception as exc:
                print(f"[IntakeConsumer] Kmong Bucky flow failed: {exc}", flush=True)
                await channel.send(f"Kmong Bucky flow failed: `{exc}`")
            return

        if dashboard_type == "daily_plus" and channel:
            if action in {"execute", "approve_execute"}:
                await _dispatch_dashboard_execution_task(payload, channel)
                return

            body = str(payload.get("body") or "")
            bucky_prompt = (
                f"[Daily Plus 대시보드 intake]\n"
                f"action: {action}\n"
                + (f"title: {title}\n" if title else "")
                + (f"\n{body}" if body else "")
            ).strip()
            try:
                ch_id_for_bucky = str(channel.id)
                timeout_s = int(os.getenv("DAILY_PLUS_INTAKE_BUCKY_TIMEOUT", "90"))
                reply = await asyncio.wait_for(
                    ask_bucky(
                        ch_id_for_bucky,
                        bucky_prompt,
                        session_key=_dashboard_session_key(payload),
                        session_label=_dashboard_session_label(payload),
                    ),
                    timeout=timeout_s,
                )
                for chunk in split_message(reply):
                    await channel.send(chunk)
            except asyncio.TimeoutError:
                await channel.send("⚠️ Bucky 응답 시간 초과 — 메시지는 수신됐습니다. **#jh-오늘의플러스** 채널에서 직접 이어서 대화하세요.")
            except Exception as exc:
                print(f"[IntakeConsumer] Daily Plus Bucky 라우팅 실패: {exc}", flush=True)
                await channel.send(f"⚠️ Bucky 라우팅 실패: `{exc}`\n**#jh-오늘의플러스** 채널에서 직접 이어서 대화하세요.")
            return

        # Repo 대시보드 intake — Bucky에게 라우팅해서 응답 전송
        if dashboard_type == "repo" and action in {"start", "batch_start", "analyze", "review"} and channel:
            repo_name = title or payload.get("repo", "") or "알 수 없음"
            bucky_prompt = (
                f"레포 대시보드에서 `{repo_name}` 레포 요청이 들어왔습니다 (action: {action}, request_id: {request_id[:8]}).\n"
                f"이 레포에 대해 어떤 작업을 진행할지 간략히 안내해 주세요."
            )
            try:
                ch_id_for_bucky = str(channel.id)
                timeout_s = int(os.getenv("REPO_INTAKE_BUCKY_TIMEOUT", "60"))
                reply = await asyncio.wait_for(
                    ask_bucky(
                        ch_id_for_bucky,
                        bucky_prompt,
                        session_key=_dashboard_session_key(payload),
                        session_label=_dashboard_session_label(payload),
                    ),
                    timeout=timeout_s,
                )
                for chunk in split_message(reply):
                    await channel.send(chunk)
            except asyncio.TimeoutError:
                await channel.send(f"⚠️ Bucky 응답 시간 초과 — `{repo_name}` 요청은 수신됐습니다.")
            except Exception as exc:
                print(f"[IntakeConsumer] Repo Bucky 라우팅 실패: {exc}", flush=True)
                await channel.send(f"⚠️ Bucky 라우팅 실패: `{exc}`")
            return

        # Wishket 개발요청은 기존 승인 큐에도 등록 (split_actions 적용)
        if dashboard_type == "wishket" and action in {"start", "approve_execute"}:
            try:
                result = await _wishket_dev_request_to_queue({**payload, "source": "intake_queue"})
                payload_n, plan, routed_path, route_mode, actions = (
                    result["payload"], result["plan"], result["routed_path"], result["route_mode"], result["actions"]
                )
                if channel:
                    if route_mode == "immediate":
                        await channel.send(
                            "**Wishket development request accepted**\n"
                            f"- slug: `{payload_n['project_slug']}`\n"
                            f"- local folder: `{plan['local_project']['target']}`\n"
                            f"- route: `{route_mode}` -> `{routed_path.name}`\n"
                            f"- immediate: {', '.join(actions['immediate']) or 'none'}\n"
                            f"- approval_required: {', '.join(actions['approval_required']) or 'none'}\n\n"
                            f"{_format_wishket_route_instruction(route_mode)}"
                        )
                        return
                    await channel.send(
                        "**Wishket 개발요청 접수**\n"
                        f"- slug: `{payload_n['project_slug']}`\n"
                        f"- local folder: `{plan['local_project']['target']}`\n"
                        f"- route: `{route_mode}` → `{routed_path.name}`\n"
                        f"- 즉시: {', '.join(actions['immediate']) or '없음'}\n"
                        f"- 승인필요: {', '.join(actions['approval_required']) or '없음'}\n\n"
                        "`!pending`으로 승인 대기 목록 확인, `!approve <번호>`로 승인."
                    )
            except Exception as exc:
                print(f"[IntakeConsumer] Wishket 큐 등록 실패: {exc}", flush=True)
                if channel:
                    await channel.send(f"⚠️ Wishket 승인 큐 등록 실패: `{exc}`")
                raise

        # App Session — 요청 파일 + 상태 파일 저장 후 고정 메시지 전송.
        # 앱 세션을 직접 생성하는 API가 없다. codex exec / CLI 실행을 세션 생성으로 보고하지 않는다.
        # 실제 세션 시작은 사용자가 PC에서 수동으로 승인·실행한다.
        if dashboard_type == "app_session":
            import json as _json_mod
            import time as _time_mod
            import sys as _sys_mod
            target_app = str(payload.get("target_app") or "claude_code").strip()
            app_action = str(payload.get("action") or "status").strip()
            workspace = str(payload.get("workspace_path") or "").strip()
            repo_name = str(payload.get("repo_name") or title or "").strip()
            handoff_path = str(payload.get("handoff_path") or "").strip()
            start_prompt = str(payload.get("start_prompt") or "").strip()
            req_id = str(payload.get("request_id") or request_id)

            req_dir = _ROOT / "data" / "app_session_requests"
            req_dir.mkdir(parents=True, exist_ok=True)

            # 요청 파일
            req_file = req_dir / f"{req_id}.json"
            req_payload = {
                "type": "app_session_request",
                "request_id": req_id,
                "target_app": target_app,
                "target_channel": str(channel.id) if channel else "",
                "workspace_path": workspace,
                "repo_name": repo_name,
                "handoff_path": handoff_path,
                "start_prompt": start_prompt,
                "action": app_action,
                "requires_user_approval": True,
                "execution_mode": "user_approved_pc_control",
                "status": "pending_approval",
                "enqueued_at": _time_mod.time(),
            }
            try:
                req_file.write_text(_json_mod.dumps(req_payload, ensure_ascii=False, indent=2), encoding="utf-8")
            except Exception as exc:
                print(f"[IntakeConsumer] App Session 요청 파일 저장 실패: {exc}", flush=True)

            # 상태 파일은 app_session_bridge.write_status() 규약(*.status.json)으로 기록
            try:
                _bridge_path = str(_ROOT / "scripts")
                if _bridge_path not in _sys_mod.path:
                    _sys_mod.path.insert(0, _bridge_path)
                import app_session_bridge as _asb
                _asb.write_status(req_id, "pending_approval", manual_action_required=True,
                                  next_action=f"PC에서 {'Claude Code' if target_app == 'claude_code' else 'Codex'} 직접 실행")
            except Exception as exc:
                print(f"[IntakeConsumer] App Session 상태 파일 저장 실패: {exc}", flush=True)

            if channel:
                app_display = "Claude Code" if target_app == "claude_code" else "Codex"
                lines = [
                    f"**앱 세션 요청 접수** (`{req_id[:8]}`)",
                    f"- 대상: {app_display}",
                ]
                if repo_name:
                    lines.append(f"- 레포: `{repo_name}`")
                if workspace:
                    lines.append(f"- 워크스페이스: `{workspace}`")
                if handoff_path:
                    lines.append(f"- handoff: `{handoff_path}`")
                lines += [
                    f"- 요청 파일: `data/app_session_requests/{req_id}.json`",
                    f"- 상태: **pending_approval** — 세션은 자동으로 시작되지 않습니다.",
                    f"PC에서 {app_display}를 직접 열고 위 요청 파일을 참고해 세션을 시작하세요.",
                ]
                await channel.send("\n".join(lines))
            return

        # Daily Plus / Task Board / Checklist — Bucky에게 라우팅해서 응답 전송
        if dashboard_type == "checklist" and action == "resume_task" and channel:
            if not _checklist_requires_manual_action(payload):
                await channel.send(
                    f"?? **[Intake: checklist] 자동 처리 가능 항목 감지** `{request_id[:12]}`\n"
                    f"- 제목: {title[:160]}\n"
                    "- worker queue에 등록해 Bucky가 처리합니다."
                )
                await _dispatch_dashboard_execution_task({**payload, "action": "execute"}, channel)
                return

        if dashboard_type in {"daily_plus", "task_board", "taskboard", "checklist"} and channel:
            summary = str(payload.get("summary") or payload.get("body") or "")
            item_id = str(payload.get("item_id") or "")
            status_val = str(payload.get("status") or "")
            note = str(payload.get("note") or "")
            priority = str(payload.get("priority") or "")
            parts = [f"`{dashboard_type}` 대시보드에서 `{action}` 요청이 들어왔습니다."]
            if title:
                parts.append(f"- 제목: {title[:200]}")
            if item_id:
                parts.append(f"- ID: {item_id}")
            if status_val:
                parts.append(f"- 상태: {status_val}")
            if priority:
                parts.append(f"- 우선순위: {priority}")
            if summary:
                parts.append(f"- 내용: {summary[:400]}")
            if note:
                parts.append(f"- 노트: {note[:200]}")
            parts.append("\n이 항목을 어떻게 처리할지 안내해 주세요.")
            bucky_prompt = "\n".join(parts)
            ack_lines = [
                f"📥 **[Intake: {dashboard_type}] `{action}` 수신 — Bucky 처리 시작**",
            ]
            if title:
                ack_lines.append(f"- 제목: {title[:120]}")
            if item_id:
                ack_lines.append(f"- ID: `{item_id}`")
            if status_val:
                ack_lines.append(f"- 상태: `{status_val}`")
            if request_id:
                ack_lines.append(f"- request_id: `{request_id[:12]}`")
            await channel.send("\n".join(ack_lines))
            try:
                ch_id_for_bucky = str(channel.id)
                timeout_s = int(os.getenv("INTAKE_BUCKY_TIMEOUT", "60"))
                reply = await asyncio.wait_for(
                    ask_bucky(
                        ch_id_for_bucky,
                        bucky_prompt,
                        session_key=_dashboard_session_key(payload),
                        session_label=_dashboard_session_label(payload),
                    ),
                    timeout=timeout_s,
                )
                for chunk in split_message(reply):
                    await channel.send(chunk)
            except asyncio.TimeoutError:
                await channel.send(f"⚠️ Bucky 응답 시간 초과 — `{title[:60]}` 요청은 수신됐습니다.")
            except Exception as exc:
                print(f"[IntakeConsumer] {dashboard_type} Bucky 라우팅 실패: {exc}", flush=True)
                await channel.send(f"⚠️ Bucky 라우팅 실패: `{exc}`")

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
        if False and not BUCKY_STATUS_CHANNEL_ID and self.guilds:
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
            notify_ch_id = BUCKY_STATUS_CHANNEL_ID
            if not notify_ch_id:
                return
            ch = self.get_channel(int(notify_ch_id))
            if ch:
                full_msg = (
                    f"🔔 **봇 재시작 — 미완료 작업 있음**\n{report}\n\n"
                    f"`!재개 [작업내용]` 으로 재실행 가능"
                )
                for chunk in split_message(full_msg):
                    await ch.send(chunk)
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

        # ── #jh-shorts: Vercel 버튼 → Webhook → 로컬 스킬 실행 ──────────────────
        if JH_SHORTS_CHANNEL_ID and channel_id == JH_SHORTS_CHANNEL_ID:
            await _handle_shorts_command(message, content)
            return

        if await _handle_daily_plus_intake_payload(message, content, channel_id):
            return

        if await _handle_wishket_development_payload(message, content):
            return

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

        # ── 앱 작업 채널: jh-클로드코드앱 / jh-코덱스앱 (독립 Claude Code 인스턴스) ─────
        _work_app_ids = {c for c in (JH_CLAUDE_CODE_CHANNEL_ID, JH_CODEX_CHANNEL_ID) if c} | JH_WORK_CHANNEL_IDS
        if _work_app_ids and channel_id in _work_app_ids:
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
        if message.attachments:
            try:
                image_urls = {a.url for a in image_atts} if "image_atts" in locals() else set()
                generic_atts = []
                for att in message.attachments:
                    suffix = Path(att.filename or "").suffix.lower()
                    is_audio = (
                        (att.content_type and att.content_type.startswith("audio/"))
                        or suffix in _AUDIO_EXTS
                    )
                    if not is_audio and att.url not in image_urls:
                        generic_atts.append(att)
                if generic_atts:
                    notes = await capture_discord_attachments(message, generic_atts, skip_urls=image_urls)
                    if notes:
                        rels = ", ".join(n.relative_to(VAULT).as_posix() for n in notes[:3])
                        content = (
                            f"{content}\n\n[Discord attachment capture]\n{rels}"
                            if content
                            else f"[Discord attachment capture]\n{rels}"
                        )
                        await message.channel.send(
                            f"Saved {len(notes)} attachment file(s) to Obsidian raw intake."
                        )
            except Exception as _att_err:
                print(f"[AttachmentCapture] failed: {_att_err}", flush=True)

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

        if content in ("!링크", "!links", "!대시보드", "!dashboard"):
            # 모바일(폰)에서 탭해서 바로 들어가는 대시보드 링크.
            # /launch가 자동 로그인 쿠키를 심고 next 페이지로 보냄 (localhost/Tailscale 기기 전용).
            base = os.getenv("JH_DASH_BASE", "https://p0517a-22h2t8.tail3b2b6d.ts.net:8443")
            fallback = os.getenv("JH_DASH_BASE_FALLBACK", "http://100.88.158.108:8765")
            await message.channel.send(
                "**📱 대시보드 바로가기** (Tailscale 연결된 기기 전용)\n"
                f"🧠 Bucky OS — <{base}/launch>\n"
                f"📋 태스크보드 — <{base}/launch?next=/task-board.html>\n"
                f"✅ 체크리스트 — <{base}/launch?next=/checklist.html>\n"
                f"📰 데일리플러스 — <{base}/launch?next=/daily-plus.html>\n"
                f"💼 위시켓 — <{base}/launch?next=/wishket.html>\n"
                f"📊 AI사용량 — <{base}/launch?next=/ai-usage.html>\n"
                f"🎙 Bucky Voice — <{base}/launch?next=/bucky-voice.html>\n"
                f"🏠 레포 허브 — <{base}/launch?next=/index.html>\n"
                f"_HTTPS 주소는 폰 PWA 설치 가능 · 안 열리면 폴백: <{fallback}/launch>_"
            )
            return

        if content == "!help":
            vc_status = "활성화" if VOICE_CHANNEL_ENABLED else "비활성화"
            tts_status = "활성화" if _gtts_available else "비활성화 (pip install gTTS)"
            recv_status = "활성화" if _voice_recv else "비활성화 (pip install discord-ext-voice-recv)"
            await message.channel.send(
                "**Bucky 명령어**\n"
                "`!status` — 봇 상태 및 내 역할 확인\n"
                "`!링크` / `!대시보드` — 📱 폰에서 여는 대시보드 바로가기\n"
                "`!reset` — 대화 기록 초기화\n"
                "`!session list` / `!세션목록` — 세션 목록 (시간대별 대화 분리)\n"
                "`!session resume <번호>` / `!세션복원 <번호>` — 이전 세션 맥락 복원\n"
                "`!session new` / `!새세션` — 새 세션 강제 시작\n"
                "`!session help` / `!세션도움말` — 세션 기능 도움말\n"
                "`!queue` / `!agentbus` / `!큐상태` — AgentBus 큐 읽기 전용 점검\n"
                "`!context-pack <내용>` / `!pack <내용>` / `!팩 <내용>` — 최소 컨텍스트 팩 선택\n"
                "**[AgentBus 승인 게이트]**\n"
                "`!pending` / `!승인목록` — 승인 대기 태스크 목록\n"
                "`!show <번호|이름>` — 대기 태스크 상세 내용 조회\n"
                "`!approve <번호|이름>` / `!승인 <번호|이름>` — 태스크 승인 → inbox 복귀\n"
                "`!reject <번호|이름> [사유]` / `!거절 <번호|이름>` — 태스크 거절 → failed\n"
                "**[!buki 워크플로우]**\n"
                "`!buki startproject <이름>` — 새 프로젝트 계획 생성 → Obsidian 저장\n"
                "`!buki checkpoint [메모]` — 세션 상태 체크포인트 → `05_Logs/` 저장\n"
                "**[멀티태스크 — 워커풀]**\n"
                "`!task <내용>` — 자동 라우팅 (Claude/Codex/Bucky) 백그라운드 실행\n"
                "`!code <내용>` — Codex 강제 배정 (검수/디버깅/분석)\n"
                "`!think <내용>` — Claude 강제 배정 (분석/설계/전략)\n"
                "`!취소 <태스크ID>` / `!cancel` — 실행 중/대기 중 태스크 취소\n"
                "`!재시도 <태스크ID>` / `!retry` — 실패/취소된 태스크 재시도\n"
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
                "`!체크` / `!체크리스트` — 태스크 보드 현황 조회\n"
                "`!체크추가 <제목>` — 태스크 수동 추가\n"
                "`!체크완료 CL-001` — 태스크 완료 처리\n"
                "`!체크진행 CL-001` — 태스크 진행중 처리\n"
                "`!체크삭제 CL-001` — 태스크 거절 처리\n"
                "`!capture <url>` / `!저장 <url>` — URL/텍스트를 Obsidian 01_RAW에 저장\n"
                "`!캡처 <텍스트>` — 텍스트 메모 Obsidian 01_RAW에 저장\n"
                "`!patterns` / `!패턴` — 반복 패턴 분석 → 스킬 자동 제안 (P1)\n"
                "`!reflect` / `!반성` — 자기 반성 분석 (P2)\n"
                f"`!입장` / `!join` — 내가 있는 음성 채널 입장 ({vc_status})\n"
                f"`!퇴장` / `!leave` — 음성 채널 퇴장\n"
                f"TTS: {tts_status} | 실시간 수신: {recv_status}\n"
                "`!봇재시작` / `!restart` — 봇 프로세스 재시작 (관리자 전용)\n"
                "`!help` — 도움말\n"
                "_그 외 메시지는 Bucky가 답변합니다._"
            )
            return

        if content in ("!봇재시작", "!restart", "!reload"):
            # 서버 관리자 또는 서버 소유자만 허용
            is_admin = (
                message.guild
                and message.guild.get_member(message.author.id)
                and (
                    message.guild.get_member(message.author.id).guild_permissions.administrator
                    or message.author.id == message.guild.owner_id
                )
            )
            if not is_admin:
                await message.channel.send("⚠️ 관리자 권한이 필요합니다.")
                return
            await message.channel.send("🔄 봇 재시작 중... (5초 후 복귀)")
            await asyncio.sleep(1)
            os.execv(sys.executable, [sys.executable] + sys.argv)

        if content == "!reset":
            conversation_history[channel_id].clear()
            try:
                import bucky_memory as _mem
                await asyncio.to_thread(_mem.clear_history, channel_id)
            except Exception:
                pass
            await message.channel.send("🔄 대화 기록을 초기화했습니다.")
            return

        # ── 세션 관리 명령어 ───────────────────────────────────────────────────
        if content in ("!session list", "!세션목록", "!sessions"):
            try:
                import bucky_memory as _mem
                sessions = await asyncio.to_thread(_mem.list_sessions, channel_id)
                if not sessions:
                    await message.channel.send("📭 저장된 세션 없음")
                else:
                    lines = ["**세션 목록** (최신 순)"]
                    cur_sid = await asyncio.to_thread(_mem.get_active_session, channel_id)
                    for i, s in enumerate(sessions):
                        ts = s["started"][:16]
                        preview = s["first_msg"] or "(비어있음)"
                        marker = " ◀ 현재" if s["id"] == cur_sid else ""
                        lines.append(f"`{i + 1}.` [{ts}] {preview} ({s['count']}개){marker}")
                    lines.append("\n_복원: `!session resume <번호>` | 새 세션: `!session new`_")
                    await message.channel.send("\n".join(lines))
            except Exception as e:
                await message.channel.send(f"⚠️ 세션 목록 오류: {e}")
            return

        if content.startswith(("!session resume ", "!세션복원 ")):
            try:
                import bucky_memory as _mem
                num_str = content.split()[-1]
                idx = int(num_str) - 1
                sessions = await asyncio.to_thread(_mem.list_sessions, channel_id)
                if idx < 0 or idx >= len(sessions):
                    await message.channel.send(f"⚠️ 1~{len(sessions)} 범위의 번호를 입력하세요")
                    return
                target = sessions[idx]
                history = await asyncio.to_thread(
                    _mem.load_session_history, channel_id, target["id"]
                )
                await asyncio.to_thread(_mem.resume_session, channel_id, target["id"])
                conversation_history[channel_id] = history.copy()
                ts = target["started"][:16]
                await message.channel.send(
                    f"✅ 세션 **{num_str}** ({ts}) 복원 완료 — {len(history)}개 메시지 로드됨\n"
                    "_이 세션의 맥락으로 계속 대화할 수 있습니다. `!session new`로 새 세션 시작 가능_"
                )
            except ValueError:
                await message.channel.send("⚠️ 사용법: `!session resume <번호>` (예: `!session resume 2`)")
            except Exception as e:
                await message.channel.send(f"⚠️ 세션 복원 오류: {e}")
            return

        if content in ("!session new", "!새세션"):
            try:
                import bucky_memory as _mem
                new_sid = await asyncio.to_thread(_mem.new_session, channel_id)
                conversation_history[channel_id].clear()
                await message.channel.send(f"🆕 새 세션 시작 (세션 ID: {new_sid})\n_이전 세션은 `!session list`로 확인 가능_")
            except Exception as e:
                await message.channel.send(f"⚠️ 새 세션 오류: {e}")
            return

        if content in ("!session help", "!세션도움말"):
            try:
                import bucky_memory as _mem
                gap = getattr(_mem, "SESSION_GAP_MINUTES", 90)
            except Exception:
                gap = 90
            await message.channel.send(
                "**세션 관리 명령어**\n"
                "`!session list` / `!세션목록` — 저장된 세션 목록 보기\n"
                "`!session resume <번호>` / `!세션복원 <번호>` — 이전 세션 맥락 복원\n"
                "`!session new` / `!새세션` — 새 세션 강제 시작\n\n"
                f"_세션은 {gap}분 이상 대화 공백 시 자동 분리됩니다. (`.env` BUCKY_SESSION_GAP으로 조정)_"
            )
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

        if content.startswith("/watch ") or content.startswith("!watch "):
            watch_url = _extract_youtube_url_from_text(content)
            if not watch_url:
                await message.channel.send("⚠️ 사용법: `/watch <YouTube URL>`")
                return
            await _handle_dashboard_watch_payload(
                {
                    "dashboard_type": "discord_watch",
                    "action": "watch",
                    "title": "Discord /watch",
                    "capture_target": watch_url,
                    "tags": "discord-watch",
                    "request_id": f"discord-watch-{message.id}",
                },
                message.channel,
            )
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

        # ── 체크리스트 명령어 ─────────────────────────────────────────────────────
        if content in ("!체크", "!체크리스트", "!cl", "!checklist", "!task-board"):
            tasks = await asyncio.to_thread(_cl_list)
            pending = [t for t in tasks if t.get("status", "pending") == "pending"]
            in_prog = [t for t in tasks if t.get("status") == "in_progress"]
            done = [t for t in tasks if t.get("status") == "done"]
            lines = [
                f"📋 **태스크 보드** — 전체 {len(tasks)}개",
                f"⏳ 미처리 {len(pending)} · 🔄 진행중 {in_prog and len(in_prog) or 0} · ✅ 완료 {len(done)}",
                "",
            ]
            if in_prog:
                lines.append("**진행중**")
                lines.append(_cl_format_list(in_prog, 5))
                lines.append("")
            if pending:
                lines.append("**미처리 (우선순위 순)**")
                lines.append(_cl_format_list(pending, 10))
            await message.channel.send("\n".join(lines))
            return

        if content.startswith(("!체크추가 ", "!cl+ ", "!cl추가 ")):
            prefix = next(p for p in ("!체크추가 ", "!cl+ ", "!cl추가 ") if content.startswith(p))
            body = content[len(prefix):].strip()
            if not body:
                await message.channel.send("사용법: `!체크추가 <제목>`")
                return
            task = await asyncio.to_thread(_cl_add, body, "", "대기", "기타", "discord")
            if task:
                await message.channel.send(f"✅ `{task['id']}` 체크리스트 추가됨\n> {body}")
            else:
                await message.channel.send("⚠️ 이미 동일한 제목이 있습니다.")
            return

        if content.startswith(("!체크완료 ", "!cl완료 ", "!cl-done ")):
            prefix = next(p for p in ("!체크완료 ", "!cl완료 ", "!cl-done ") if content.startswith(p))
            cl_id = content[len(prefix):].strip().upper()
            task = await asyncio.to_thread(_cl_set_status, cl_id, "done")
            if task:
                await message.channel.send(f"✅ `{cl_id}` 완료 처리됨\n> {task['title']}")
            else:
                await message.channel.send(f"⚠️ `{cl_id}` 를 찾을 수 없습니다.")
            return

        if content.startswith(("!체크진행 ", "!cl진행 ", "!cl-start ")):
            prefix = next(p for p in ("!체크진행 ", "!cl진행 ", "!cl-start ") if content.startswith(p))
            cl_id = content[len(prefix):].strip().upper()
            task = await asyncio.to_thread(_cl_set_status, cl_id, "in_progress")
            if task:
                await message.channel.send(f"🔄 `{cl_id}` 진행중으로 변경됨\n> {task['title']}")
            else:
                await message.channel.send(f"⚠️ `{cl_id}` 를 찾을 수 없습니다.")
            return

        if content.startswith(("!체크삭제 ", "!cl삭제 ", "!cl-reject ")):
            prefix = next(p for p in ("!체크삭제 ", "!cl삭제 ", "!cl-reject ") if content.startswith(p))
            cl_id = content[len(prefix):].strip().upper()
            task = await asyncio.to_thread(_cl_set_status, cl_id, "rejected")
            if task:
                await message.channel.send(f"❌ `{cl_id}` 거절 처리됨\n> {task['title']}")
            else:
                await message.channel.send(f"⚠️ `{cl_id}` 를 찾을 수 없습니다.")
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
                    agent_icon = {"claude": "🧠", "codex": "⚡", "bucky": "🤖", "gemini": "🔭", "chris": "🧭"}.get(task["agent"], "")
                    tid = task["id"]
                    title_short = task["title"][:40]

                    # 키워드 라우팅 힌트
                    kw_agent, kw_matched = _kw_classify(body)
                    kw_hint_str = _kw_hint(kw_agent, kw_matched)
                    routing_line = (
                        f"→ `{task['agent'].upper()}` 배정"
                        + (f" | {kw_hint_str}" if kw_hint_str else "")
                        + " · 백그라운드 실행 시작"
                    )
                    if kw_hint_str:
                        print(f"[KeywordRouter] !task → {kw_agent} | {kw_matched[:3]}", flush=True)

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
                        f"{routing_line}{thread_mention}"
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
                            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=600
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
                ctx = _load_agent_context(str(message.channel.id), content)
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
                            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=int(os.getenv("BUCKY_TIMEOUT", "900"))
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
                        timeout=float(os.getenv("BUCKY_TIMEOUT", "900")),
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
                try:
                    await thinking_msg.edit(content=chunks[0])
                except discord.errors.NotFound:
                    await message.channel.send(chunks[0])
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

                # 미완료 태스크 자동 감지 (백그라운드)
                asyncio.ensure_future(_auto_detect_checklist(reply, message.channel))

                out_path = write_discord_message(message, reply, status="answered")
        else:
            out_path = write_discord_message(message, status="pending")

        print(f"[Bot] Saved: {out_path.name}", flush=True)


# ── 진입점 ─────────────────────────────────────────────────────────────────────

def main() -> None:
    import os as _pid_os, atexit as _atexit, subprocess as _sp, sys as _sys
    _PID_FILE = Path(__file__).parent.parent / "logs" / "discord_bot.pid"
    _PID_FILE.parent.mkdir(parents=True, exist_ok=True)

    def _pid_alive(pid: int) -> bool:
        # os.kill(pid, 0) raises WinError 87 on Windows Python 3.14 — use tasklist
        if _sys.platform == "win32":
            try:
                r = _sp.run(
                    ["tasklist", "/FI", f"PID eq {pid}", "/NH", "/FO", "CSV"],
                    capture_output=True, text=True, encoding="utf-8", errors="replace",
                )
                return f'"{pid}"' in r.stdout
            except Exception:
                return False
        try:
            _pid_os.kill(pid, 0)
            return True
        except OSError:
            return False

    if _PID_FILE.exists():
        try:
            _old_pid = int(_PID_FILE.read_text().strip())
            if _pid_alive(_old_pid):
                print(f"[Bot] 이미 실행 중 (PID {_old_pid}). 종료합니다.", flush=True)
                raise SystemExit(0)
        except (ValueError, SystemExit):
            raise
        except Exception:
            pass  # PID 파싱 실패 또는 기타 오류 → 파일 덮어쓰기
    _PID_FILE.write_text(str(_pid_os.getpid()))
    _atexit.register(lambda: _PID_FILE.unlink(missing_ok=True))

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
