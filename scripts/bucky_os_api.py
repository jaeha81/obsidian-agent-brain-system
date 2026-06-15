#!/usr/bin/env python3
"""Bucky Agent OS API — Flask Blueprint serving /os/* endpoints.

Register in bucky_chat_server.py:
    from bucky_os_api import os_bp
    app.register_blueprint(os_bp)
"""

from __future__ import annotations

import ctypes
import io
import json
import sqlite3
import threading
import time
from pathlib import Path

from flask import Blueprint, Response, jsonify, request, stream_with_context

ROOT = Path(__file__).resolve().parent.parent
VAULT = ROOT / "ObsidianVault"
CONTEXT_PACKS_DIR = VAULT / "06_Context_Packs"
GRAPHIFY_OUT = VAULT / "graphify-out"
GRAPH_JSON = GRAPHIFY_OUT / "graph.json"
GRAPH_REPORT = GRAPHIFY_OUT / "GRAPH_REPORT.md"
AGENTBUS_DIR = VAULT / "10_AgentBus"
MEMORY_DB = VAULT / "10_AgentBus" / "tasks" / "bucky_memory.db"
SKILLS_DIR = ROOT / ".claude" / "skills"
AGENTS_REGISTRY = ROOT / "data" / "agents_registry.json"

os_bp = Blueprint("os", __name__, url_prefix="/os")

_graph_cache: dict = {"data": None, "mtime": 0.0}


def _set_windows_clipboard_text(text: str) -> None:
    """Set Unicode text on the Windows clipboard without extra dependencies."""
    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32

    user32.OpenClipboard.argtypes = [ctypes.c_void_p]
    user32.OpenClipboard.restype = ctypes.c_int
    user32.EmptyClipboard.restype = ctypes.c_int
    user32.SetClipboardData.argtypes = [ctypes.c_uint, ctypes.c_void_p]
    user32.SetClipboardData.restype = ctypes.c_void_p
    user32.CloseClipboard.restype = ctypes.c_int
    kernel32.GlobalAlloc.argtypes = [ctypes.c_uint, ctypes.c_size_t]
    kernel32.GlobalAlloc.restype = ctypes.c_void_p
    kernel32.GlobalLock.argtypes = [ctypes.c_void_p]
    kernel32.GlobalLock.restype = ctypes.c_void_p
    kernel32.GlobalUnlock.argtypes = [ctypes.c_void_p]
    kernel32.GlobalUnlock.restype = ctypes.c_int
    kernel32.GlobalFree.argtypes = [ctypes.c_void_p]
    kernel32.GlobalFree.restype = ctypes.c_void_p

    data = (text + "\0").encode("utf-16-le")
    h_global = kernel32.GlobalAlloc(0x0002, len(data))
    if not h_global:
        raise RuntimeError("clipboard allocation failed")

    locked = kernel32.GlobalLock(h_global)
    if not locked:
        kernel32.GlobalFree(h_global)
        raise RuntimeError("clipboard lock failed")

    try:
        ctypes.memmove(locked, data, len(data))
    finally:
        kernel32.GlobalUnlock(h_global)

    opened = False
    for _ in range(10):
        if user32.OpenClipboard(None):
            opened = True
            break
        time.sleep(0.02)

    if not opened:
        kernel32.GlobalFree(h_global)
        raise RuntimeError("clipboard unavailable")

    try:
        if not user32.EmptyClipboard():
            raise RuntimeError("clipboard clear failed")
        if not user32.SetClipboardData(13, h_global):
            raise RuntimeError("clipboard set failed")
        h_global = None
    finally:
        user32.CloseClipboard()
        if h_global:
            kernel32.GlobalFree(h_global)


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


# ─── Screen Control ──────────────────────────────────────────────
_screen_lock = threading.Lock()


def _capture_jpeg(quality: int = 60, scale: float = 0.5) -> bytes:
    import mss
    from PIL import Image

    with _screen_lock:
        with mss.MSS() as sct:
            monitor = sct.monitors[1]
            shot = sct.grab(monitor)
            img = Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")
    if scale != 1.0:
        w = max(1, int(img.width * scale))
        h = max(1, int(img.height * scale))
        img = img.resize((w, h), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=quality, optimize=True)
    return buf.getvalue()


@os_bp.get("/screen/info")
def screen_info():
    import mss

    with mss.MSS() as sct:
        m = sct.monitors[1]
    return jsonify({"width": m["width"], "height": m["height"], "left": m["left"], "top": m["top"]})


@os_bp.get("/screen/snapshot")
def screen_snapshot():
    try:
        quality = max(10, min(95, int(request.args.get("quality", 60))))
        scale = max(0.1, min(1.0, float(request.args.get("scale", 0.5))))
        jpeg = _capture_jpeg(quality, scale)
        resp = Response(jpeg, mimetype="image/jpeg")
        resp.headers["Cache-Control"] = "no-store"
        return resp
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@os_bp.get("/screen/stream")
def screen_stream():
    try:
        quality = max(10, min(85, int(request.args.get("quality", 50))))
        scale = max(0.1, min(1.0, float(request.args.get("scale", 0.5))))
        fps = max(1, min(30, float(request.args.get("fps", 10))))
        interval = 1.0 / fps

        def _gen():
            while True:
                try:
                    jpeg = _capture_jpeg(quality, scale)
                    yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + jpeg + b"\r\n"
                    time.sleep(interval)
                except GeneratorExit:
                    break
                except Exception:
                    break

        return Response(
            stream_with_context(_gen()),
            mimetype="multipart/x-mixed-replace; boundary=frame",
            headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"},
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@os_bp.get("/agents")
def get_agents():
    try:
        data = json.loads(AGENTS_REGISTRY.read_text(encoding="utf-8"))
    except Exception:
        data = {"agents": []}
    agents = data.get("agents", [])
    active = sum(1 for a in agents if a.get("status") == "active")
    return jsonify({"agents": agents, "total": len(agents), "active": active})


@os_bp.get("/agents/<agent_id>")
def get_agent(agent_id: str):
    try:
        data = json.loads(AGENTS_REGISTRY.read_text(encoding="utf-8"))
    except Exception:
        return jsonify({"error": "registry not found"}), 404
    for a in data.get("agents", []):
        if a.get("id") == agent_id:
            return jsonify(a)
    return jsonify({"error": "agent not found"}), 404


@os_bp.post("/agents/<agent_id>/call")
def call_agent(agent_id: str):
    body = request.get_json(force=True) or {}
    task_text = str(body.get("task", "")).strip()
    if not task_text:
        return jsonify({"error": "task is required"}), 400

    try:
        data = json.loads(AGENTS_REGISTRY.read_text(encoding="utf-8"))
    except Exception:
        return jsonify({"error": "registry not found"}), 404

    agent = next((a for a in data.get("agents", []) if a.get("id") == agent_id), None)
    if not agent:
        return jsonify({"error": "agent not found"}), 404

    # Update last_called timestamp
    for a in data["agents"]:
        if a.get("id") == agent_id:
            a["last_called"] = time.strftime("%Y-%m-%dT%H:%M:%S")
            a["status"] = "active"
            break
    try:
        AGENTS_REGISTRY.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass

    # Dispatch via AgentBus inbox
    msg_id = f"{time.strftime('%Y%m%d_%H%M%S')}_{agent_id}"
    inbox_msg = {
        "id": msg_id,
        "agent": agent_id,
        "agent_name": agent.get("name", agent_id),
        "model": agent.get("model", "claude"),
        "domain": agent.get("domain", ""),
        "task": task_text,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "source": "agent-room",
        "status": "pending",
    }
    try:
        inbox_dir = AGENTBUS_DIR / "inbox"
        inbox_dir.mkdir(parents=True, exist_ok=True)
        inbox_file = inbox_dir / f"{msg_id}_agent_room.json"
        inbox_file.write_text(json.dumps(inbox_msg, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        return jsonify({"error": f"dispatch failed: {e}"}), 500

    return jsonify({"ok": True, "id": msg_id, "agent": agent_id, "status": "dispatched"})


@os_bp.post("/screen/input")
def screen_input():
    import pyautogui

    pyautogui.FAILSAFE = False

    data = request.get_json(force=True) or {}
    ev = data.get("type", "")
    try:
        if ev == "move":
            pyautogui.moveTo(int(data["x"]), int(data["y"]), duration=0)
        elif ev == "click":
            btn = data.get("button", "left")
            x, y = int(data["x"]), int(data["y"])
            if data.get("double"):
                pyautogui.doubleClick(x, y, button=btn)
            else:
                pyautogui.click(x, y, button=btn)
        elif ev == "mousedown":
            pyautogui.mouseDown(int(data["x"]), int(data["y"]), button=data.get("button", "left"))
        elif ev == "mouseup":
            pyautogui.mouseUp(int(data["x"]), int(data["y"]), button=data.get("button", "left"))
        elif ev == "scroll":
            pyautogui.moveTo(int(data["x"]), int(data["y"]), duration=0)
            dy = int(data.get("dy", 0))
            dx = int(data.get("dx", 0))
            if dy:
                pyautogui.scroll(dy)
            if dx:
                pyautogui.hscroll(dx)
        elif ev == "key":
            key = str(data.get("key", "")).strip()
            if key:
                if "+" in key:
                    keys = [part.strip() for part in key.split("+") if part.strip()]
                    pyautogui.hotkey(*keys)
                else:
                    pyautogui.press(key)
        elif ev == "type":
            text = str(data.get("text", ""))
            if text:
                try:
                    _set_windows_clipboard_text(text)
                    pyautogui.hotkey("ctrl", "v")
                except Exception:
                    pyautogui.typewrite(text, interval=0.03)
        elif ev == "hotkey":
            keys = data.get("keys", [])
            if keys:
                pyautogui.hotkey(*[str(k).strip() for k in keys if str(k).strip()])
        else:
            return jsonify({"error": f"unknown type: {ev}"}), 400

        return jsonify({"ok": True, "type": ev})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
