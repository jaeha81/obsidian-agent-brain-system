#!/usr/bin/env python3
"""Bucky Agent OS — Mission Control API.

Flask Blueprint serving /agent-os/* endpoints.
Register in bucky_chat_server.py:
    from bucky_agent_os_api import agent_os_bp
    app.register_blueprint(agent_os_bp)

Contrast with bucky_os_api.py (Claude Code version):
  - Focus: operational health, tasks, skills, dream report
  - Prefix: /agent-os/*
  - No graph data (uses bucky_os_api for that)
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
import subprocess
import time
from pathlib import Path

from flask import Blueprint, jsonify

ROOT = Path(__file__).resolve().parent.parent
VAULT = ROOT / "ObsidianVault"
SYSTEM_DIR = VAULT / "00_System"
CONTEXT_PACKS_DIR = VAULT / "06_Context_Packs"
CHECKLIST_JSON = ROOT / "data" / "user_checklist.json"
SKILL_SUGGESTED = ROOT / ".claude" / "skills" / "suggested"
SKILL_INDEX = ROOT / "skills" / "skill_index.json"
HANDOFF_LOG = SYSTEM_DIR / "HANDOFF_LOG.md"
BUCKY_STATUS = SYSTEM_DIR / "BUCKY_STATUS.md"
WISHKET_LOOP = ROOT / "data" / "wishket_loop_history.json"
DISCORD_BOT = ROOT / "scripts" / "discord_bot.py"
MEMORY_DB = ROOT / "data" / "bucky_memory.db"
ACTIVE_GOAL = SYSTEM_DIR / "active_goal.json"
CLI_TOOLS_LOG = VAULT / "05_Logs" / "cli-tools.jsonl"

LIMIT_EVENT_RE = re.compile(
    r"(usage limit|rate limit|subscription limit|out of .*usage|quota exceeded|429|resets .*(am|pm))",
    re.IGNORECASE,
)

agent_os_bp = Blueprint("agent_os", __name__, url_prefix="/agent-os")


def _ts_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S")


def _file_age_min(p: Path) -> float:
    try:
        return (time.time() - p.stat().st_mtime) / 60
    except Exception:
        return 9999.0


def _sqlite_count(conn: sqlite3.Connection, sql: str) -> int:
    try:
        row = conn.execute(sql).fetchone()
        return int(row[0]) if row else 0
    except Exception:
        return 0


def _sqlite_rows(conn: sqlite3.Connection, sql: str, limit: int = 5) -> list[dict]:
    try:
        rows = conn.execute(sql, (limit,)).fetchall()
        return [dict(row) for row in rows]
    except Exception:
        return []


def _goal_summary(data: dict) -> dict:
    subtasks = data.get("subtasks", [])
    total = len(subtasks)
    done = sum(1 for item in subtasks if item.get("status") in ("done", "completed"))
    pending = sum(1 for item in subtasks if item.get("status") not in ("done", "completed", "skipped"))
    return {
        "total": total,
        "done": done,
        "pending": pending,
        "progress_percent": int(done / total * 100) if total else 0,
    }


@agent_os_bp.get("/health")
def health():
    """Agent & process health check."""
    agents = []

    # Discord bot — check running python processes for discord_bot.py
    bot_alive = False
    bot_pid = None
    try:
        result = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq python.exe", "/FO", "CSV", "/NH"],
            capture_output=True, text=True, timeout=5
        )
        if "python" in result.stdout.lower():
            bot_alive = True
    except Exception:
        pass

    # Check PID lock file
    pid_lock = ROOT / "scripts" / "bucky_bot.pid"
    if pid_lock.exists():
        try:
            bot_pid = int(pid_lock.read_text().strip())
            bot_alive = True
        except Exception:
            pass

    agents.append({
        "name": "Bucky Discord Bot",
        "id": "discord_bot",
        "status": "online" if bot_alive else "offline",
        "pid": bot_pid,
        "detail": f"PID {bot_pid}" if bot_pid else "No PID lock",
    })

    # Wishket agent — check loop history recency
    wishket_ok = False
    wishket_detail = "No history"
    if WISHKET_LOOP.exists():
        age = _file_age_min(WISHKET_LOOP)
        wishket_ok = age < 60
        wishket_detail = f"Last run {age:.0f}m ago"
    agents.append({
        "name": "Wishket Agent",
        "id": "wishket_agent",
        "status": "active" if wishket_ok else "idle",
        "detail": wishket_detail,
    })

    # Flask server self (always alive if this endpoint responds)
    agents.append({
        "name": "Bucky Chat Server",
        "id": "bucky_server",
        "status": "online",
        "detail": "Self-reporting",
    })

    # Vault freshness
    handoff_age = _file_age_min(HANDOFF_LOG)
    agents.append({
        "name": "Knowledge Vault",
        "id": "vault",
        "status": "fresh" if handoff_age < 1440 else "stale",
        "detail": f"HANDOFF_LOG {handoff_age:.0f}m ago",
    })

    return jsonify({"agents": agents, "checked_at": _ts_now()})


@agent_os_bp.get("/tasks")
def tasks():
    """Task board — user_checklist.json with priority grouping."""
    try:
        data = json.loads(CHECKLIST_JSON.read_text(encoding="utf-8"))
    except Exception:
        return jsonify({"error": "checklist not found", "tasks": [], "summary": {}})

    all_tasks = data.get("tasks", [])

    # Group
    pending = [t for t in all_tasks if t.get("status") not in ("done", "completed", "skipped")]
    done = [t for t in all_tasks if t.get("status") in ("done", "completed")]

    # Priority order for pending
    pri_order = {"P0": 0, "P1": 1, "P2": 2, "P3": 3, "대기": 4}
    pending.sort(key=lambda t: pri_order.get(t.get("priority", "대기"), 5))

    return jsonify({
        "pending": pending,
        "done": done[-5:],  # last 5 completed
        "summary": {
            "total": len(all_tasks),
            "pending": len(pending),
            "done": len(done),
            "p0_count": sum(1 for t in pending if t.get("priority") == "P0"),
            "p1_count": sum(1 for t in pending if t.get("priority") == "P1"),
        },
        "meta": data.get("meta", {}),
    })


@agent_os_bp.get("/skills")
def skills():
    """Skill registry — suggested skills + skill_index.json."""
    skill_list = []

    # Suggested skills (auto-generated)
    if SKILL_SUGGESTED.exists():
        for f in sorted(SKILL_SUGGESTED.glob("*.md")):
            name = f.stem
            category = name.split("-")[1] if "-" in name else "general"
            skill_list.append({
                "name": name,
                "category": category,
                "source": "suggested",
                "path": str(f.relative_to(ROOT)),
            })

    # Skill index (named skills)
    if SKILL_INDEX.exists():
        try:
            idx = json.loads(SKILL_INDEX.read_text(encoding="utf-8"))
            for sk_id, sk_data in idx.items():
                skill_list.append({
                    "name": sk_id,
                    "category": "named",
                    "source": "index",
                    "description": sk_data.get("description", "")[:80],
                    "path": sk_data.get("path", ""),
                })
        except Exception:
            pass

    # Context packs (Bucky-managed)
    cp_count = 0
    cp_names = []
    if CONTEXT_PACKS_DIR.exists():
        cp_files = sorted(CONTEXT_PACKS_DIR.glob("*.md"))
        cp_count = len(cp_files)
        cp_names = [f.stem for f in cp_files]

    return jsonify({
        "skills": skill_list,
        "summary": {
            "suggested_count": sum(1 for s in skill_list if s["source"] == "suggested"),
            "named_count": sum(1 for s in skill_list if s["source"] == "index"),
            "total": len(skill_list),
            "context_packs": cp_count,
        },
        "context_pack_names": cp_names,
    })


@agent_os_bp.get("/dream")
def dream():
    """Dream report — last HANDOFF_LOG session summary."""
    if not HANDOFF_LOG.exists():
        return jsonify({"error": "HANDOFF_LOG not found", "sessions": []})

    content = HANDOFF_LOG.read_text(encoding="utf-8")
    lines = content.splitlines()

    # Split into sessions by ## heading
    sessions = []
    current: list[str] = []
    current_title = ""
    for line in lines:
        if line.startswith("## "):
            if current_title and current:
                sessions.append({"title": current_title, "body": "\n".join(current)})
            current_title = line[3:].strip()
            current = []
        else:
            current.append(line)
    if current_title and current:
        sessions.append({"title": current_title, "body": "\n".join(current)})

    # Return last 3 sessions
    latest = sessions[-3:] if len(sessions) >= 3 else sessions
    for s in latest:
        s["body"] = s["body"][:400]  # trim for API payload

    return jsonify({
        "sessions": list(reversed(latest)),
        "total_sessions": len(sessions),
        "last_updated": time.strftime(
            "%Y-%m-%dT%H:%M:%S", time.localtime(HANDOFF_LOG.stat().st_mtime)
        ),
    })


@agent_os_bp.get("/memory")
def memory():
    """Memory stack — 4-layer structured view: short-term, episodic, semantic, procedural."""
    summary = {"fact_count": 0, "session_count": 0, "message_count": 0}
    short_term: list[dict] = []
    episodic: list[dict] = []
    semantic: dict[str, list] = {}
    procedural: list[dict] = []

    try:
        conn = sqlite3.connect(str(MEMORY_DB), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")

        summary["fact_count"] = _sqlite_count(conn, "SELECT COUNT(*) FROM learned_facts")
        summary["session_count"] = _sqlite_count(conn, "SELECT COUNT(*) FROM sessions")
        summary["message_count"] = _sqlite_count(conn, "SELECT COUNT(*) FROM conv_history")

        # Short-term: most recent messages across all channels (latest 8)
        rows = conn.execute(
            """
            SELECT channel, role, content, ts, session_id
            FROM conv_history
            ORDER BY id DESC
            LIMIT 8
            """
        ).fetchall()
        short_term = [
            {
                "channel": r["channel"],
                "role": r["role"],
                "content": r["content"][:120],
                "ts": r["ts"],
                "session_id": r["session_id"],
            }
            for r in rows
        ]

        # Episodic: recent sessions with message count and label
        sess_rows = conn.execute(
            """
            SELECT s.id, s.channel, s.started, s.label, s.external_key,
                   COUNT(c.id) as msg_count
            FROM sessions s
            LEFT JOIN conv_history c ON c.session_id = s.id
            GROUP BY s.id
            ORDER BY s.id DESC
            LIMIT 10
            """
        ).fetchall()
        for s in sess_rows:
            first = conn.execute(
                "SELECT content FROM conv_history WHERE session_id=? AND role='user' ORDER BY id LIMIT 1",
                (s["id"],),
            ).fetchone()
            preview = ""
            if first:
                txt = first["content"]
                preview = txt[:70] + ("…" if len(txt) > 70 else "")
            episodic.append({
                "id": s["id"],
                "channel": s["channel"],
                "started": s["started"],
                "label": s["label"] or s["external_key"] or "",
                "msg_count": s["msg_count"],
                "preview": preview,
            })

        # Semantic: facts grouped by category
        cat_rows = conn.execute(
            "SELECT DISTINCT category FROM learned_facts ORDER BY category"
        ).fetchall()
        for cat_row in cat_rows:
            cat = cat_row["category"]
            facts = conn.execute(
                "SELECT fact, ts FROM learned_facts WHERE category=? ORDER BY id DESC LIMIT 5",
                (cat,),
            ).fetchall()
            semantic[cat] = [{"fact": f["fact"], "ts": f["ts"]} for f in facts]

        # Procedural: instruction-type facts (explicit recurring rules)
        proc_rows = conn.execute(
            """
            SELECT category, fact, ts
            FROM learned_facts
            WHERE category IN ('instruction', 'tech')
            ORDER BY id DESC
            LIMIT 8
            """
        ).fetchall()
        procedural = [{"category": r["category"], "fact": r["fact"], "ts": r["ts"]} for r in proc_rows]

        conn.close()
    except Exception:
        pass

    return jsonify({
        "summary": summary,
        "layers": {
            "short_term": short_term,
            "episodic": episodic,
            "semantic": semantic,
            "procedural": procedural,
        },
        "db_path": str(MEMORY_DB.relative_to(ROOT)) if MEMORY_DB.is_relative_to(ROOT) else str(MEMORY_DB),
        "checked_at": _ts_now(),
    })


@agent_os_bp.get("/goals")
def goals():
    """Mission Control goal mode - active goal and subtask progress."""
    if not ACTIVE_GOAL.exists():
        return jsonify({
            "active": False,
            "goal": "",
            "focus": False,
            "summary": {"total": 0, "done": 0, "pending": 0, "progress_percent": 0},
            "subtasks": [],
            "checked_at": _ts_now(),
        })

    try:
        data = json.loads(ACTIVE_GOAL.read_text(encoding="utf-8"))
    except Exception:
        data = {}

    subtasks = data.get("subtasks", [])
    return jsonify({
        "active": bool(data.get("goal")),
        "goal": data.get("goal", ""),
        "created": data.get("created", ""),
        "focus": bool(data.get("focus")),
        "summary": _goal_summary(data),
        "subtasks": subtasks[:10],
        "checked_at": _ts_now(),
    })


@agent_os_bp.get("/spend")
def spend():
    """AI spend and usage pressure - local CLI call log summary."""
    models: dict[str, dict[str, int]] = {}
    latest_limit_event: dict | None = None
    summary = {
        "total_calls": 0,
        "successes": 0,
        "failures": 0,
        "limit_events": 0,
    }

    def model_bucket(model: str) -> dict[str, int]:
        key = model or "unknown"
        if key not in models:
            models[key] = {"calls": 0, "successes": 0, "failures": 0, "limit_events": 0}
        return models[key]

    try:
        lines = CLI_TOOLS_LOG.read_text(encoding="utf-8", errors="ignore").splitlines()
    except Exception:
        lines = []

    for line in lines:
        if not line.strip():
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue

        model = str(rec.get("model") or "unknown")
        success = bool(rec.get("success"))
        detail = " ".join(
            str(rec.get(key) or "")
            for key in ("response_summary", "stderr", "error", "detail")
        )
        limited = bool(LIMIT_EVENT_RE.search(detail))
        bucket = model_bucket(model)

        summary["total_calls"] += 1
        bucket["calls"] += 1
        if success:
            summary["successes"] += 1
            bucket["successes"] += 1
        else:
            summary["failures"] += 1
            bucket["failures"] += 1
        if limited:
            summary["limit_events"] += 1
            bucket["limit_events"] += 1
            latest_limit_event = {
                "timestamp": rec.get("timestamp", ""),
                "model": model,
                "detail": detail[:180],
            }

    return jsonify({
        "summary": summary,
        "models": models,
        "latest_limit_event": latest_limit_event,
        "log_path": str(CLI_TOOLS_LOG.relative_to(ROOT)) if CLI_TOOLS_LOG.is_relative_to(ROOT) else str(CLI_TOOLS_LOG),
        "checked_at": _ts_now(),
    })


@agent_os_bp.get("/spend/remaining")
def spend_remaining():
    """T025: Anthropic 구독 잔여량 추정 — limit 이벤트 빈도 기반 압력 레벨.

    Anthropic 구독(Claude Code)은 공식 API 잔여량 조회 불가.
    로컬 cli-tools.jsonl의 limit 이벤트 빈도로 압력(pressure)을 추정함.

    pressure levels:
      ok       — limit 이벤트 없음, 정상 사용 중
      moderate — 최근 24h 내 limit 이벤트 1~2회
      high     — 최근 3h 내 limit 이벤트 1회 이상 / 24h 3회 이상
      critical — 최근 1h 내 limit 이벤트 발생
    """
    import time as _time
    now_ts = _time.time()
    ONE_HOUR   = 3600
    THREE_HOUR = 10800
    ONE_DAY    = 86400

    # ── 수동 설정 파일 (사용자가 직접 입력한 메모) ──
    REMAINING_OVERRIDE = ROOT / "data" / "spend_remaining_override.json"
    manual: dict = {}
    if REMAINING_OVERRIDE.exists():
        try:
            manual = json.loads(REMAINING_OVERRIDE.read_text(encoding="utf-8"))
        except Exception:
            pass

    # ── cli-tools.jsonl 분석 ──────────────────────────────
    try:
        lines = CLI_TOOLS_LOG.read_text(encoding="utf-8", errors="ignore").splitlines()
    except Exception:
        lines = []

    limit_1h = limit_3h = limit_24h = 0
    latest_limit_ts: str = ""
    latest_limit_model: str = ""

    for line in lines:
        if not line.strip():
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        detail = " ".join(
            str(rec.get(k) or "") for k in ("response_summary", "stderr", "error", "detail")
        )
        if not LIMIT_EVENT_RE.search(detail):
            continue

        # 타임스탬프 파싱
        raw_ts = str(rec.get("timestamp") or "")
        try:
            from datetime import datetime as _dt, timezone as _tz
            if raw_ts:
                if "T" in raw_ts:
                    ev_dt = _dt.fromisoformat(raw_ts.replace("Z", "+00:00"))
                else:
                    ev_dt = _dt.fromtimestamp(float(raw_ts), tz=_tz.utc)
                age_sec = now_ts - ev_dt.timestamp()
            else:
                age_sec = ONE_DAY + 1  # 타임스탬프 없으면 24h 초과로 처리
        except Exception:
            age_sec = ONE_DAY + 1

        if age_sec <= ONE_HOUR:
            limit_1h += 1
        if age_sec <= THREE_HOUR:
            limit_3h += 1
        if age_sec <= ONE_DAY:
            limit_24h += 1
            if not latest_limit_ts:
                latest_limit_ts = raw_ts
                latest_limit_model = str(rec.get("model") or "")

    # ── 압력 레벨 결정 ──────────────────────────────────────
    if limit_1h >= 1:
        pressure = "critical"
        pressure_note = f"최근 1h 내 {limit_1h}회 limit — 호출 일시 중단 권고"
    elif limit_3h >= 1 or limit_24h >= 3:
        pressure = "high"
        pressure_note = f"최근 3h {limit_3h}회 / 24h {limit_24h}회 limit — 속도 조절 필요"
    elif limit_24h >= 1:
        pressure = "moderate"
        pressure_note = f"최근 24h {limit_24h}회 limit — 사용 주의"
    else:
        pressure = "ok"
        pressure_note = "limit 이벤트 없음 — 정상 사용 중"

    # ── 수동 override 병합 ───────────────────────────────────
    result = {
        "pressure": pressure,
        "pressure_note": pressure_note,
        "limit_1h": limit_1h,
        "limit_3h": limit_3h,
        "limit_24h": limit_24h,
        "latest_limit_event": {
            "timestamp": latest_limit_ts,
            "model": latest_limit_model,
        } if latest_limit_ts else None,
        "note": "Claude Code 구독 방식 — 공식 API 잔여량 조회 불가. limit 이벤트 빈도로 추정.",
        "checked_at": _ts_now(),
    }

    # 수동 입력 메모가 있으면 추가
    if manual:
        result["manual_override"] = manual

    return jsonify(result)


@agent_os_bp.post("/spend/remaining")
def set_spend_remaining():
    """사용자가 현재 잔여량/메모를 수동으로 기록하는 엔드포인트.

    POST body: {"note": "오늘 100회 남음", "remaining_estimate": 100}
    data/spend_remaining_override.json 에 저장됨.
    """
    REMAINING_OVERRIDE = ROOT / "data" / "spend_remaining_override.json"
    data = request.get_json(silent=True) or {}
    from datetime import datetime as _dt, timezone as _tz
    payload = {**data, "updated_at": _dt.now(_tz.utc).isoformat()}
    REMAINING_OVERRIDE.parent.mkdir(parents=True, exist_ok=True)
    REMAINING_OVERRIDE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return jsonify({"status": "saved", "data": payload}), 200


@agent_os_bp.get("/overview")
def overview():
    """Single-call overview combining health + task summary."""
    # Inline lightweight versions
    pending_count = done_count = 0
    try:
        data = json.loads(CHECKLIST_JSON.read_text(encoding="utf-8"))
        all_tasks = data.get("tasks", [])
        pending_count = sum(1 for t in all_tasks if t.get("status") not in ("done", "completed", "skipped"))
        done_count = sum(1 for t in all_tasks if t.get("status") in ("done", "completed"))
    except Exception:
        pass

    skill_count = len(list(SKILL_SUGGESTED.glob("*.md"))) if SKILL_SUGGESTED.exists() else 0

    cp_count = len(list(CONTEXT_PACKS_DIR.glob("*.md"))) if CONTEXT_PACKS_DIR.exists() else 0

    bot_alive = False
    pid_lock = ROOT / "scripts" / "bucky_bot.pid"
    if pid_lock.exists():
        try:
            int(pid_lock.read_text().strip())
            bot_alive = True
        except Exception:
            pass

    return jsonify({
        "system": "Bucky Agent OS",
        "version": "v1.0",
        "checked_at": _ts_now(),
        "agents": {
            "discord_bot": "online" if bot_alive else "offline",
            "bucky_server": "online",
        },
        "tasks": {"pending": pending_count, "done": done_count},
        "knowledge": {"skills": skill_count, "context_packs": cp_count},
    })
