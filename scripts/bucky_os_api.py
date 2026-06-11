#!/usr/bin/env python3
"""Bucky Agent OS API — Flask Blueprint serving /os/* endpoints.

Register in bucky_chat_server.py:
    from bucky_os_api import os_bp
    app.register_blueprint(os_bp)
"""

from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path

from flask import Blueprint, jsonify, request

ROOT = Path(__file__).resolve().parent.parent
VAULT = ROOT / "ObsidianVault"
CONTEXT_PACKS_DIR = VAULT / "06_Context_Packs"
GRAPHIFY_OUT = VAULT / "graphify-out"
GRAPH_JSON = GRAPHIFY_OUT / "graph.json"
GRAPH_REPORT = GRAPHIFY_OUT / "GRAPH_REPORT.md"
AGENTBUS_DIR = VAULT / "10_AgentBus"
MEMORY_DB = VAULT / "10_AgentBus" / "tasks" / "bucky_memory.db"
SKILLS_DIR = ROOT / ".claude" / "skills"

os_bp = Blueprint("os", __name__, url_prefix="/os")

_graph_cache: dict = {"data": None, "mtime": 0.0}


def _load_graph() -> dict:
    global _graph_cache
    try:
        mtime = GRAPH_JSON.stat().st_mtime
        if mtime != _graph_cache["mtime"] or _graph_cache["data"] is None:
            _graph_cache["data"] = json.loads(GRAPH_JSON.read_text(encoding="utf-8"))
            _graph_cache["mtime"] = mtime
    except Exception:
        return {"nodes": [], "links": []}
    return _graph_cache["data"]


def _parse_graph_report() -> dict:
    stats: dict = {"nodes": 0, "edges": 0, "clusters": 0, "isolated": 0, "built_at": ""}
    try:
        for line in GRAPH_REPORT.read_text(encoding="utf-8").splitlines():
            if line.startswith("- Nodes:"):
                stats["nodes"] = int(line.split(":")[1].strip())
            elif line.startswith("- Edges:"):
                stats["edges"] = int(line.split(":")[1].strip())
            elif line.startswith("- Clusters:"):
                stats["clusters"] = int(line.split(":")[1].strip())
            elif line.startswith("- Isolated:"):
                stats["isolated"] = int(line.split(":")[1].strip())
            elif "Generated:" in line:
                stats["built_at"] = line.split("|")[0].replace("> Generated:", "").strip()
    except Exception:
        pass
    return stats


def _fmt_ts(ts) -> str:
    try:
        return time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(float(ts)))
    except Exception:
        return str(ts)


@os_bp.get("/graph")
def get_graph():
    data = _load_graph()
    report = _parse_graph_report()

    nodes = [
        {
            "id": n.get("id", ""),
            "label": n.get("label", ""),
            "file_type": n.get("file_type", "code"),
            "source_file": n.get("source_file", ""),
            "community": n.get("community", 0),
        }
        for n in data.get("nodes", [])
    ]

    edges = [
        {
            "source": e.get("source", ""),
            "target": e.get("target", ""),
            "confidence": e.get("confidence", "EXTRACTED"),
        }
        for e in data.get("links", [])
    ]

    # Fact vs inferred ratio from link confidence (computed on FULL graph)
    total = len(edges)
    extracted = sum(1 for e in edges if e.get("confidence") == "EXTRACTED")
    fact_pct = round(extracted / total * 100) if total else 0

    # Downsample: full graph is ~11.6MB / 6k+ nodes — too heavy to ship to the
    # browser every refresh. Keep top-N nodes by degree; ?limit=0 returns all.
    try:
        limit = int(request.args.get("limit", 300))
    except (TypeError, ValueError):
        limit = 300
    if limit > 0 and len(nodes) > limit:
        degree: dict = {}
        for e in edges:
            degree[e["source"]] = degree.get(e["source"], 0) + 1
            degree[e["target"]] = degree.get(e["target"], 0) + 1
        nodes = sorted(nodes, key=lambda n: degree.get(n["id"], 0), reverse=True)[:limit]
        kept = {n["id"] for n in nodes}
        edges = [e for e in edges if e["source"] in kept and e["target"] in kept]

    resp = jsonify({
        "nodes": nodes,
        "edges": edges,
        "stats": {**report, "fact_pct": fact_pct, "inferred_pct": 100 - fact_pct},
    })
    # Browsers were memory-caching the old 7MB response and replaying it on
    # every refresh — live dashboard data must never be cached.
    resp.headers["Cache-Control"] = "no-store"
    return resp


@os_bp.get("/stats")
def get_stats():
    # Context Packs (top-level .md only)
    cp_files = sorted(f.name for f in CONTEXT_PACKS_DIR.glob("*.md")) if CONTEXT_PACKS_DIR.exists() else []

    # Skills
    skill_files: list[str] = []
    for candidate in [SKILLS_DIR, SKILLS_DIR / "suggested"]:
        if candidate.exists():
            skill_files.extend(f.name for f in candidate.glob("*.md"))
    skill_files = sorted(set(skill_files))

    # AgentBus counts
    def _count(d: Path) -> int:
        return len(list(d.glob("*.*"))) if d.exists() else 0

    inbox_count = _count(AGENTBUS_DIR / "inbox")
    outbox_count = _count(AGENTBUS_DIR / "outbox")

    tasks_pending = 0
    try:
        tf = AGENTBUS_DIR / "tasks" / "session_tasks.json"
        tasks_data = json.loads(tf.read_text(encoding="utf-8"))
        tasks = tasks_data if isinstance(tasks_data, list) else tasks_data.get("tasks", [])
        tasks_pending = sum(1 for t in tasks if t.get("status") not in ("done", "completed", "skipped"))
    except Exception:
        pass

    # Memory DB
    fact_count = session_count = 0
    try:
        conn = sqlite3.connect(str(MEMORY_DB), check_same_thread=False)
        conn.execute("PRAGMA journal_mode=WAL")
        try:
            fact_count = conn.execute("SELECT COUNT(*) FROM learned_facts").fetchone()[0]
        except Exception:
            pass
        try:
            session_count = conn.execute(
                "SELECT COUNT(DISTINCT session_id) FROM conv_history"
            ).fetchone()[0]
        except Exception:
            pass
        conn.close()
    except Exception:
        pass

    return jsonify({
        "context_packs": {"count": len(cp_files), "files": cp_files},
        "skills": {"count": len(skill_files), "files": skill_files},
        "agentbus": {
            "inbox_count": inbox_count,
            "outbox_count": outbox_count,
            "tasks_pending": tasks_pending,
        },
        "memory": {"fact_count": fact_count, "session_count": session_count},
        "graph": _parse_graph_report(),
    })


@os_bp.get("/activity")
def get_activity():
    events: list[dict] = []

    # Awareness latest
    try:
        af = AGENTBUS_DIR / "awareness" / "LATEST.md"
        if af.exists():
            events.append({
                "ts": _fmt_ts(af.stat().st_mtime),
                "type": "awareness",
                "title": "Bucky Awareness 업데이트",
                "detail": af.read_text(encoding="utf-8")[:200],
            })
    except Exception:
        pass

    # Recent reports
    try:
        rdir = AGENTBUS_DIR / "reports"
        if rdir.exists():
            for rf in sorted(rdir.glob("*.md"), key=lambda f: f.stat().st_mtime, reverse=True)[:5]:
                events.append({
                    "ts": _fmt_ts(rf.stat().st_mtime),
                    "type": "report",
                    "title": rf.stem,
                    "detail": rf.read_text(encoding="utf-8")[:120],
                })
    except Exception:
        pass

    # Recent chat from memory DB
    try:
        conn = sqlite3.connect(str(MEMORY_DB), check_same_thread=False)
        conn.execute("PRAGMA journal_mode=WAL")
        try:
            rows = conn.execute(
                "SELECT content, timestamp FROM conv_history WHERE role='user' ORDER BY timestamp DESC LIMIT 5"
            ).fetchall()
            for content, ts in rows:
                events.append({
                    "ts": _fmt_ts(ts),
                    "type": "chat",
                    "title": f"채팅: {str(content)[:50]}",
                    "detail": str(content)[:120],
                })
        except Exception:
            pass
        conn.close()
    except Exception:
        pass

    events.sort(key=lambda e: e.get("ts", ""), reverse=True)
    return jsonify({"events": events[:20]})


@os_bp.get("/session-cost")
def get_session_cost():
    session_count = 0
    try:
        conn = sqlite3.connect(str(MEMORY_DB), check_same_thread=False)
        conn.execute("PRAGMA journal_mode=WAL")
        try:
            session_count = conn.execute(
                "SELECT COUNT(DISTINCT session_id) FROM conv_history"
            ).fetchone()[0]
        except Exception:
            pass
        conn.close()
    except Exception:
        pass

    # Heuristic: graphify map saves ~$0.15 per session vs raw file scanning
    estimated_saved = round(session_count * 0.15, 2)
    return jsonify({
        "total_sessions": session_count,
        "estimated_saved_usd": estimated_saved,
        "savings_per_session": 0.15,
    })
