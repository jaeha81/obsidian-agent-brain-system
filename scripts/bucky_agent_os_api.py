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
AGENTS_REGISTRY = ROOT / "data" / "agents_registry.json"
SKILL_SUGGESTED = ROOT / ".claude" / "skills" / "suggested"
SKILL_INDEX = ROOT / "skills" / "skill_index.json"
HANDOFF_LOG = SYSTEM_DIR / "HANDOFF_LOG.md"
BUCKY_STATUS = SYSTEM_DIR / "BUCKY_STATUS.md"
WISHKET_LOOP = ROOT / "data" / "wishket_loop_history.json"
DISCORD_BOT = ROOT / "scripts" / "discord_bot.py"
MEMORY_DB = ROOT / "data" / "bucky_memory.db"
ACTIVE_GOAL = SYSTEM_DIR / "active_goal.json"
CLI_TOOLS_LOG = VAULT / "05_Logs" / "cli-tools.jsonl"
GRAPH_REPORT = VAULT / "graphify-out" / "GRAPH_REPORT.md"
KNOWLEDGE_DIR = VAULT / "03_Knowledge"

def _parse_graph_report() -> dict[str, int]:
    """Parse Nodes/Clusters from GRAPH_REPORT.md."""
    result = {"kb_nodes": 0, "kb_clusters": 0}
    if not GRAPH_REPORT.exists():
        return result
    try:
        text = GRAPH_REPORT.read_text(encoding="utf-8")
        for key, pattern in [
            ("kb_nodes",    r"Nodes:\s*(\d+)"),
            ("kb_clusters", r"Clusters:\s*(\d+)"),
        ]:
            m = re.search(pattern, text)
            if m:
                result[key] = int(m.group(1))
    except Exception:
        pass
    return result


def _count_kb_intake_today() -> int:
    """Count markdown files in 03_Knowledge modified today."""
    if not KNOWLEDGE_DIR.exists():
        return 0
    today = time.strftime("%Y-%m-%d")
    count = 0
    try:
        for f in KNOWLEDGE_DIR.glob("*.md"):
            if time.strftime("%Y-%m-%d", time.localtime(f.stat().st_mtime)) == today:
                count += 1
    except Exception:
        pass
    return count


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
    summary: dict = {"fact_count": 0, "session_count": 0, "message_count": 0}
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

    # KB stats from Graphify
    graph_stats = _parse_graph_report()
    summary["kb_nodes"] = graph_stats["kb_nodes"]
    summary["kb_clusters"] = graph_stats["kb_clusters"]
    summary["kb_intake_today"] = _count_kb_intake_today()

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


@agent_os_bp.get("/agents")
def agents_room():
    """Agent Room — all registered agents with live status and callable metadata."""
    # Live status checks
    bot_alive = False
    pid_lock = ROOT / "scripts" / "bucky_bot.pid"
    if pid_lock.exists():
        try:
            int(pid_lock.read_text().strip())
            bot_alive = True
        except Exception:
            pass

    wishket_ok = False
    if WISHKET_LOOP.exists():
        wishket_ok = _file_age_min(WISHKET_LOOP) < 60

    # System/operational agents with live status
    system_agents = [
        {
            "id": "bucky",
            "name": "Bucky",
            "emoji": "🧠",
            "role": "오케스트레이터",
            "description": "중앙 조율, Context Pack 생성, 작업 분류 및 라우팅",
            "domain": ["전략", "브리핑", "라우팅", "작업 분해"],
            "model": "claude-sonnet-4-6",
            "status": "online" if bot_alive else "offline",
            "callable": True,
            "call_endpoint": "/chat",
        },
        {
            "id": "claude_code",
            "name": "Claude Code",
            "emoji": "⚡",
            "role": "1번 구현자",
            "description": "프론트엔드 / UI / HTML / CSS / 아키텍처 / 복잡한 구현",
            "domain": ["프론트엔드", "UI", "HTML", "CSS"],
            "model": "claude-sonnet-4-6",
            "status": "online",
            "callable": True,
            "call_endpoint": "/intake",
        },
        {
            "id": "codex",
            "name": "Codex",
            "emoji": "🔧",
            "role": "2번 구현자",
            "description": "백엔드 / 스크립트 / API / 자동화 / 테스트 / 버그 수정",
            "domain": ["백엔드", "스크립트", "API", "자동화"],
            "model": "claude-sonnet-4-6",
            "status": "standby",
            "callable": True,
            "call_endpoint": "/intake",
        },
        {
            "id": "wishket_agent",
            "name": "Wishket Agent",
            "emoji": "💼",
            "role": "수주 자동화",
            "description": "Wishket 프리랜서 프로젝트 탐색, 제안서 생성, 자동 매칭",
            "domain": ["Wishket", "프리랜서", "제안서"],
            "model": "claude-sonnet-4-6",
            "status": "active" if wishket_ok else "idle",
            "callable": True,
            "call_endpoint": "/intake",
        },
    ]

    # Domain agents from registry JSON
    domain_agents: list[dict] = []
    try:
        reg_data = json.loads(AGENTS_REGISTRY.read_text(encoding="utf-8"))
        for a in reg_data.get("agents", []):
            domain_agents.append({
                "id":            a.get("id", ""),
                "name":          a.get("name", ""),
                "emoji":         a.get("icon", "🤖"),
                "role":          a.get("domain", ""),
                "description":   a.get("description", ""),
                "domain":        a.get("keywords", [])[:4],
                "model":         a.get("model", "claude"),
                "status":        a.get("status", "idle"),
                "callable":      True,
                "call_endpoint": f"/os/agents/{a.get('id', '')}/call",
                "last_called":   a.get("last_called"),
            })
    except Exception:
        pass

    registry = system_agents + domain_agents

    online = sum(1 for a in registry if a["status"] in ("online", "active"))
    standby = sum(1 for a in registry if a["status"] == "standby")
    pending = sum(1 for a in registry if a["status"] == "pending")
    offline = sum(1 for a in registry if a["status"] == "offline")

    return jsonify({
        "agents": registry,
        "summary": {
            "total": len(registry),
            "online": online,
            "standby": standby,
            "pending": pending,
            "offline": offline,
        },
        "checked_at": _ts_now(),
    })


@agent_os_bp.get("/repo-priority")
def repo_priority():
    """레포지토리 수익성 우선순위 — 정의된 레포별 점수 반환.

    점수 기준 (100점):
      revenue_type (0~40): direct=40, potential=20, operational=5
      open_tasks   (0~20): 태스크 큐 내 해당 도메인 pending 수 비례
      last_activity(0~20): 최근 7일=20, 30일=10, 90일=5, 그 이상=0
      deploy_status(0~10): deployed=10, staging=5, local=0
      user_priority(0~10): BUCKY_CONTEXT 우선순위 반영 (수동)
    """
    import time as _time
    now = _time.time()
    SEVEN_DAYS = 7 * 86400
    THIRTY_DAYS = 30 * 86400
    NINETY_DAYS = 90 * 86400

    REPOS = [
        {
            "id": "wishket",
            "name": "Wishket 자동화",
            "description": "Wishket 공고 스캔·제안서 자동생성·수주 추적",
            "revenue_type": "direct",
            "deploy_status": "local",
            "user_priority": 10,
            "path": ROOT / "scripts" / "bucky_wishket_agent.py",
            "auto_ok": True,
            "domain": "freelance",
        },
        {
            "id": "sniper",
            "name": "스나이퍼 구매대행 플랫폼",
            "description": "iHerb/Amazon 소싱 → 마진율 → 통관 리스크 스코어",
            "revenue_type": "direct",
            "deploy_status": "deployed",
            "user_priority": 9,
            "path": ROOT / "docs" / "loashop.html",
            "auto_ok": False,
            "domain": "ecommerce",
        },
        {
            "id": "bucky-os",
            "name": "Bucky Agent OS",
            "description": "에이전트 운영체제 · 대시보드 · Discord 봇",
            "revenue_type": "operational",
            "deploy_status": "deployed",
            "user_priority": 8,
            "path": ROOT / "scripts" / "bucky_chat_server.py",
            "auto_ok": True,
            "domain": "infrastructure",
        },
        {
            "id": "daily-plus",
            "name": "Daily Plus 큐레이터",
            "description": "매일 진화 후보 수집·적용·리포트",
            "revenue_type": "operational",
            "deploy_status": "deployed",
            "user_priority": 7,
            "path": ROOT / "scripts" / "generate_daily_plus_dashboard.py",
            "auto_ok": True,
            "domain": "productivity",
        },
        {
            "id": "content-studio",
            "name": "ProSuTech 콘텐츠",
            "description": "유튜브·블로그·SNS 자동 원고 생성",
            "revenue_type": "potential",
            "deploy_status": "local",
            "user_priority": 6,
            "path": None,
            "auto_ok": False,
            "domain": "content",
        },
    ]

    REVENUE_SCORE = {"direct": 40, "potential": 20, "operational": 5}
    DEPLOY_SCORE = {"deployed": 10, "staging": 5, "local": 0}

    # pending tasks per domain from checklist
    domain_pending: dict[str, int] = {}
    try:
        data = json.loads(CHECKLIST_JSON.read_text(encoding="utf-8"))
        for t in data.get("tasks", []):
            if t.get("status") not in ("done", "completed", "skipped"):
                tags = t.get("tags", []) or []
                for tag in tags:
                    domain_pending[tag] = domain_pending.get(tag, 0) + 1
    except Exception:
        pass

    results = []
    for repo in REPOS:
        # last activity: mtime of path file
        activity_score = 0
        p = repo["path"]
        if p and Path(p).exists():
            try:
                age = now - Path(p).stat().st_mtime
                if age <= SEVEN_DAYS:
                    activity_score = 20
                elif age <= THIRTY_DAYS:
                    activity_score = 10
                elif age <= NINETY_DAYS:
                    activity_score = 5
            except Exception:
                pass

        # open tasks score (max 20, pro-rata from 5 tasks)
        pending_count = domain_pending.get(repo["domain"], 0)
        task_score = min(20, pending_count * 4)

        score = (
            REVENUE_SCORE.get(repo["revenue_type"], 0)
            + task_score
            + activity_score
            + DEPLOY_SCORE.get(repo["deploy_status"], 0)
            + repo["user_priority"]
        )

        results.append({
            "id": repo["id"],
            "name": repo["name"],
            "description": repo["description"],
            "score": score,
            "revenue_type": repo["revenue_type"],
            "deploy_status": repo["deploy_status"],
            "open_tasks": pending_count,
            "auto_ok": repo["auto_ok"],
            "domain": repo["domain"],
        })

    results.sort(key=lambda r: r["score"], reverse=True)
    return jsonify({
        "repos": results,
        "top": results[0] if results else None,
        "auto_eligible": [r for r in results if r["auto_ok"]],
        "checked_at": _ts_now(),
    })


@agent_os_bp.post("/repo-priority/queue")
def repo_priority_queue():
    """Phase 2-1: auto_ok=true 레포를 태스크 큐에 자동 등록.

    기존 태스크 중복 체크 후 신규만 추가.
    Returns: queued (추가된 수), skipped (중복), tasks (추가된 태스크 목록)
    """
    # Load repo-priority to get auto_ok repos
    import time as _time
    now = _time.time()
    SEVEN_DAYS = 7 * 86400
    THIRTY_DAYS = 30 * 86400
    NINETY_DAYS = 90 * 86400

    REPOS = [
        {"id": "wishket", "name": "Wishket 자동화", "auto_ok": True, "domain": "freelance",
         "revenue_type": "direct", "deploy_status": "local", "user_priority": 10,
         "path": ROOT / "scripts" / "bucky_wishket_agent.py",
         "auto_task": "Wishket 공고 스캔 및 제안서 자동화 파이프라인 개선"},
        {"id": "bucky-os", "name": "Bucky Agent OS", "auto_ok": True, "domain": "infrastructure",
         "revenue_type": "operational", "deploy_status": "deployed", "user_priority": 8,
         "path": ROOT / "scripts" / "bucky_chat_server.py",
         "auto_task": "BuckyOS 대시보드 성능 및 안정성 개선"},
        {"id": "daily-plus", "name": "Daily Plus", "auto_ok": True, "domain": "productivity",
         "revenue_type": "operational", "deploy_status": "deployed", "user_priority": 7,
         "path": ROOT / "scripts" / "generate_daily_plus_dashboard.py",
         "auto_task": "Daily Plus 큐레이터 효율 개선 및 자동화"},
    ]

    try:
        checklist = json.loads(CHECKLIST_JSON.read_text(encoding="utf-8"))
    except Exception:
        checklist = {"meta": {}, "tasks": []}

    existing_ids = {t.get("id", "") for t in checklist.get("tasks", [])}
    queued = []
    skipped = []

    for repo in REPOS:
        task_id = f"auto-{repo['id']}-{_time.strftime('%Y%m%d')}"
        if task_id in existing_ids:
            skipped.append(repo["id"])
            continue
        new_task = {
            "id": task_id,
            "title": repo["auto_task"],
            "priority": "P2",
            "status": "pending",
            "tags": [repo["domain"], "auto-generated"],
            "source": "repo-priority-auto",
            "repo": repo["id"],
            "created_at": _ts_now(),
        }
        checklist.setdefault("tasks", []).append(new_task)
        queued.append(new_task)

    if queued:
        CHECKLIST_JSON.write_text(json.dumps(checklist, ensure_ascii=False, indent=2), encoding="utf-8")

    return jsonify({"queued": len(queued), "skipped": len(skipped), "tasks": queued})


@agent_os_bp.post("/agents/call")
def agents_call():
    """Phase 2-3: 에이전트 호출 기록 — last_called + status 갱신.

    POST body: {"agent_id": "...", "task": "...", "caller": "user"}
    agents_registry.json의 last_called + call_count 업데이트.
    """
    data = request.get_json(silent=True) or {}
    agent_id = data.get("agent_id", "")
    task = data.get("task", "")
    if not agent_id:
        return jsonify({"error": "agent_id required"}), 400

    try:
        reg = json.loads(AGENTS_REGISTRY.read_text(encoding="utf-8"))
    except Exception:
        reg = {"agents": []}

    updated = False
    for a in reg.get("agents", []):
        if a.get("id") == agent_id:
            a["last_called"] = _ts_now()
            a["call_count"] = a.get("call_count", 0) + 1
            a["status"] = "active"
            a["last_task"] = task[:120] if task else ""
            updated = True
            break

    if not updated:
        reg.setdefault("agents", []).append({
            "id": agent_id, "name": agent_id, "status": "active",
            "last_called": _ts_now(), "call_count": 1, "last_task": task[:120],
        })

    AGENTS_REGISTRY.write_text(json.dumps(reg, ensure_ascii=False, indent=2), encoding="utf-8")
    return jsonify({"ok": True, "agent_id": agent_id, "recorded_at": _ts_now()})


@agent_os_bp.get("/spend/summary")
def spend_summary():
    """Phase 2-2: 총 AI 구독 비용 통합 뷰.

    Claude Code + Codex + ChatGPT Plus + 기타 구독 합산.
    수동 입력은 data/spend_remaining_override.json 에서 읽음.
    """
    REMAINING_OVERRIDE = ROOT / "data" / "spend_remaining_override.json"
    manual: dict = {}
    if REMAINING_OVERRIDE.exists():
        try:
            manual = json.loads(REMAINING_OVERRIDE.read_text(encoding="utf-8"))
        except Exception:
            pass

    # 기본 구독 비용 (하드코딩 기준값 — 수동 override 가능)
    subscriptions = [
        {"provider": "Claude Code (Anthropic)", "plan": "Max", "monthly_usd": 100,
         "currency_krw": 138000, "status": "active", "icon": "⚡"},
        {"provider": "Codex (OpenAI)", "plan": "Pro", "monthly_usd": 200,
         "currency_krw": 276000, "status": manual.get("codex_status", "active"), "icon": "🔧"},
        {"provider": "ChatGPT Plus (OpenAI)", "plan": "Plus", "monthly_usd": 20,
         "currency_krw": 27600, "status": manual.get("chatgpt_status", "active"), "icon": "💬"},
    ]

    # 수동 추가 구독 반영
    extra = manual.get("extra_subscriptions", [])
    subscriptions.extend(extra)

    total_usd = sum(s["monthly_usd"] for s in subscriptions if s.get("status") == "active")
    total_krw = sum(s.get("currency_krw", 0) for s in subscriptions if s.get("status") == "active")

    return jsonify({
        "subscriptions": subscriptions,
        "total_monthly_usd": total_usd,
        "total_monthly_krw": total_krw,
        "updated_at": manual.get("updated_at", _ts_now()),
        "note": manual.get("note", ""),
    })


@agent_os_bp.post("/repo-priority/snapshot")
def repo_priority_snapshot():
    """Phase 3-3: 수익성 점수 주간 스냅샷 저장.

    매주 월요일 09:00 KST 스케줄러 또는 수동 호출.
    data/repo_priority_snapshots.json 에 타임스탬프별 기록.
    """
    SNAPSHOTS = ROOT / "data" / "repo_priority_snapshots.json"

    # Inline score computation (repo-priority 로직 재사용)
    import time as _time
    now = _time.time()
    REPOS = [
        {"id": "wishket", "name": "Wishket 자동화", "revenue_type": "direct",
         "deploy_status": "local", "user_priority": 10, "domain": "freelance",
         "path": ROOT / "scripts" / "bucky_wishket_agent.py"},
        {"id": "sniper", "name": "스나이퍼 구매대행", "revenue_type": "direct",
         "deploy_status": "deployed", "user_priority": 9, "domain": "ecommerce",
         "path": ROOT / "docs" / "loashop.html"},
        {"id": "bucky-os", "name": "Bucky Agent OS", "revenue_type": "operational",
         "deploy_status": "deployed", "user_priority": 8, "domain": "infrastructure",
         "path": ROOT / "scripts" / "bucky_chat_server.py"},
        {"id": "daily-plus", "name": "Daily Plus", "revenue_type": "operational",
         "deploy_status": "deployed", "user_priority": 7, "domain": "productivity",
         "path": ROOT / "scripts" / "generate_daily_plus_dashboard.py"},
        {"id": "content-studio", "name": "ProSuTech 콘텐츠", "revenue_type": "potential",
         "deploy_status": "local", "user_priority": 6, "domain": "content", "path": None},
    ]
    REVENUE_SCORE = {"direct": 40, "potential": 20, "operational": 5}
    DEPLOY_SCORE = {"deployed": 10, "staging": 5, "local": 0}

    domain_pending: dict[str, int] = {}
    try:
        data = json.loads(CHECKLIST_JSON.read_text(encoding="utf-8"))
        for t in data.get("tasks", []):
            if t.get("status") not in ("done", "completed", "skipped"):
                for tag in (t.get("tags") or []):
                    domain_pending[tag] = domain_pending.get(tag, 0) + 1
    except Exception:
        pass

    snapshot_scores: dict[str, int] = {}
    for repo in REPOS:
        activity_score = 0
        p = repo["path"]
        if p and Path(p).exists():
            try:
                age = now - Path(p).stat().st_mtime
                if age <= 7 * 86400:
                    activity_score = 20
                elif age <= 30 * 86400:
                    activity_score = 10
                elif age <= 90 * 86400:
                    activity_score = 5
            except Exception:
                pass
        task_score = min(20, domain_pending.get(repo["domain"], 0) * 4)
        snapshot_scores[repo["id"]] = (
            REVENUE_SCORE.get(repo["revenue_type"], 0) + task_score
            + activity_score + DEPLOY_SCORE.get(repo["deploy_status"], 0)
            + repo["user_priority"]
        )

    # Load existing snapshots
    try:
        snapshots = json.loads(SNAPSHOTS.read_text(encoding="utf-8"))
    except Exception:
        snapshots = {"history": []}

    new_entry = {"timestamp": _ts_now(), "scores": snapshot_scores}
    snapshots["history"].append(new_entry)
    # Keep last 52 weeks
    snapshots["history"] = snapshots["history"][-52:]

    # Detect drops ≥ 20 from previous snapshot
    alerts = []
    if len(snapshots["history"]) >= 2:
        prev = snapshots["history"][-2]["scores"]
        for repo_id, score in snapshot_scores.items():
            prev_score = prev.get(repo_id, score)
            if prev_score - score >= 20:
                alerts.append({"repo": repo_id, "drop": prev_score - score,
                                "prev": prev_score, "now": score})

    SNAPSHOTS.write_text(json.dumps(snapshots, ensure_ascii=False, indent=2), encoding="utf-8")
    return jsonify({"saved": True, "snapshot": new_entry, "alerts": alerts})


@agent_os_bp.get("/model-stats")
def model_stats():
    """Phase 3-2: 모델별 호출 통계 및 비용 최적화 리포트.

    cli-tools.jsonl 에서 모델별 호출 수 집계.
    Haiku/Sonnet/Opus 절감액 추정.
    """
    stats: dict[str, dict] = {}
    try:
        lines = CLI_TOOLS_LOG.read_text(encoding="utf-8").splitlines()
        for line in lines[-2000:]:  # last 2000 entries only
            try:
                entry = json.loads(line)
                model = entry.get("model", "unknown")
                s = stats.setdefault(model, {"calls": 0, "success": 0, "fail": 0})
                s["calls"] += 1
                if entry.get("exit_code", 1) == 0 or entry.get("status") == "ok":
                    s["success"] += 1
                else:
                    s["fail"] += 1
            except Exception:
                pass
    except Exception:
        pass

    # Cost estimates (per-call rough estimate based on typical token use)
    COST_PER_CALL = {"haiku": 0.01, "sonnet": 0.05, "opus": 0.25, "codex-default": 0.04}
    savings = []
    total_estimated = 0.0
    optimized_estimated = 0.0

    for model, s in stats.items():
        base_cost = COST_PER_CALL.get(model, 0.05)
        actual = s["calls"] * base_cost
        # If all calls were Haiku: min cost
        haiku_cost = s["calls"] * COST_PER_CALL["haiku"]
        total_estimated += actual
        optimized_estimated += haiku_cost
        if model not in ("haiku",):
            savings.append({
                "model": model,
                "calls": s["calls"],
                "estimated_usd": round(actual, 2),
                "haiku_equivalent_usd": round(haiku_cost, 2),
                "potential_saving_usd": round(actual - haiku_cost, 2),
            })

    savings.sort(key=lambda x: x["potential_saving_usd"], reverse=True)

    return jsonify({
        "by_model": stats,
        "cost_estimate": {
            "total_usd": round(total_estimated, 2),
            "optimized_usd": round(optimized_estimated, 2),
            "saving_potential_usd": round(total_estimated - optimized_estimated, 2),
        },
        "top_savings": savings[:3],
        "recommendation": "상태 확인·분류·짧은 요약은 Haiku로, 구현·파일 편집은 Sonnet으로 라우팅하면 최대 절감 가능",
        "checked_at": _ts_now(),
    })


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


