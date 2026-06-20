#!/usr/bin/env python3
"""Bucky Agent OS API — Flask Blueprint serving /os/* endpoints.

Register in bucky_chat_server.py:
    from bucky_os_api import os_bp
    app.register_blueprint(os_bp)
"""

from __future__ import annotations

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
# graphify-out was moved to 09_Archive during vault consolidation (2026-06-20d)
_GRAPHIFY_CANDIDATES = [
    VAULT / "09_Archive" / "graphify-out",
    VAULT / "graphify-out",
    VAULT / "03_Projects" / "graphify-out",
]
GRAPHIFY_OUT = next((p for p in _GRAPHIFY_CANDIDATES if (p / "graph.json").exists()), _GRAPHIFY_CANDIDATES[0])
GRAPH_JSON = GRAPHIFY_OUT / "graph.json"
GRAPH_REPORT = GRAPHIFY_OUT / "GRAPH_REPORT.md"
AGENTBUS_DIR = VAULT / "10_AgentBus"
MEMORY_DB = VAULT / "10_AgentBus" / "tasks" / "bucky_memory.db"
SKILLS_DIR = ROOT / ".claude" / "skills"
AGENTS_REGISTRY = ROOT / "data" / "agents_registry.json"

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
                "SELECT content, ts FROM conv_history WHERE role='user' ORDER BY ts DESC LIMIT 5"
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
            key = str(data.get("key", ""))
            if key:
                pyautogui.press(key)
        elif ev == "type":
            text = str(data.get("text", ""))
            if text:
                pyautogui.typewrite(text, interval=0.03)
        elif ev == "hotkey":
            keys = data.get("keys", [])
            if keys:
                pyautogui.hotkey(*keys)
        else:
            return jsonify({"error": f"unknown type: {ev}"}), 400

        return jsonify({"ok": True, "type": ev})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── Card 4: 레포 수익성 점수화 ──────────────────────────────────────────
_REPO_SCORE_CACHE: dict = {"data": None, "mtime": 0.0}
_REPO_SCORE_JSON = DATA_DIR / "repo_priority_scores.json" if (DATA_DIR := ROOT / "data") else None


@os_bp.get("/repo-priority")
def get_repo_priority():
    """최근 repo_priority_scorer.py 결과를 반환.
    ?refresh=1 이면 백그라운드 재실행 트리거.
    ?owner=xxx 로 특정 오너 필터.
    """
    import subprocess, sys, threading

    score_path = ROOT / "data" / "repo_priority_scores.json"

    def _run_scorer():
        try:
            subprocess.run(
                [sys.executable, "-X", "utf8", str(ROOT / "scripts" / "repo_priority_scorer.py")],
                capture_output=True,
                timeout=120,
            )
        except Exception:
            pass

    if request.args.get("refresh") == "1":
        threading.Thread(target=_run_scorer, daemon=True).start()
        return jsonify({"ok": True, "status": "refresh_triggered"})

    try:
        mtime = score_path.stat().st_mtime
        if _REPO_SCORE_CACHE["data"] is None or mtime != _REPO_SCORE_CACHE["mtime"]:
            _REPO_SCORE_CACHE["data"] = json.loads(score_path.read_text(encoding="utf-8"))
            _REPO_SCORE_CACHE["mtime"] = mtime
        data = _REPO_SCORE_CACHE["data"]
    except Exception:
        return jsonify({"generated_at": None, "results": [], "note": "score file not found — call ?refresh=1"})

    results = data.get("results", [])
    owner_filter = request.args.get("owner", "")
    if owner_filter:
        results = [r for r in results if r.get("name", "").startswith(owner_filter + "/")]

    shortlist = [r for r in results if r.get("shortlist")]
    tiers = {"High": 0, "Medium": 0, "Low": 0}
    for r in results:
        t = r.get("tier", "Low")
        tiers[t] = tiers.get(t, 0) + 1

    resp = jsonify({
        "generated_at": data.get("generated_at"),
        "summary": {**tiers, "shortlist_count": len(shortlist), "total": len(results)},
        "shortlist": shortlist,
        "results": results[:50],
    })
    resp.headers["Cache-Control"] = "no-store"
    return resp


# ── G1: 쿼리→Wiki 피드백 루프 ──────────────────────────────────────────
@os_bp.route("/query-to-wiki", methods=["POST"])
def query_to_wiki():
    """쿼리 결과를 01_RAW 노트로 저장 → wiki_gate 파이프라인 진입.

    Body JSON:
      query   (str, required)  — 검색 쿼리 또는 질문
      answer  (str, required)  — 답변 본문
      cluster (str, optional)  — graph_cluster (기본: misc)
      source  (str, optional)  — 출처 레이블 (기본: query-feedback)
      links   (list, optional) — 추가 wikilink 목록
    """
    import subprocess, sys

    data = request.get_json(force=True) or {}
    query = data.get("query", "").strip()
    answer = data.get("answer", "").strip()
    if not query or not answer:
        return jsonify({"error": "query and answer are required"}), 400

    cluster = data.get("cluster", "misc")
    source = data.get("source", "query-feedback")
    links = data.get("links", [])

    script = Path(__file__).parent / "query_to_wiki.py"
    cmd = [
        sys.executable, "-X", "utf8", str(script),
        "--query", query,
        "--answer", answer,
        "--cluster", cluster,
        "--source", source,
    ]
    if links:
        cmd += ["--links"] + links

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        if result.returncode != 0:
            return jsonify({"error": result.stderr}), 500
        saved_path = result.stdout.strip().replace("[query_to_wiki] 저장: ", "")
        return jsonify({"ok": True, "path": saved_path})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ------- Wiki Gate endpoints -------

DAILY_DIR = VAULT / "07_Daily"


def _latest_report(pattern):
    """Return path of newest file matching glob pattern in DAILY_DIR."""
    files = sorted(DAILY_DIR.glob(pattern), key=lambda p: p.name, reverse=True)
    return files[0] if files else None


@os_bp.route("/wiki-gate/status")
def wiki_gate_status():
    """Parse latest wiki-lint + wiki-gate + wiki-link-suggest reports."""
    import re

    out = {
        "lint": {"total_checked": 0, "last_run": None, "issues_total": 0, "rules": {}},
        "gate": {"total_scanned": 0, "promotions": 0, "last_run": None, "failed_total": 0, "filters": {}},
        "l007": {"under_linked": 0, "applied": 0, "last_run": None},
    }

    lint_file = _latest_report("*-wiki-lint.md")
    if lint_file:
        text = lint_file.read_text(encoding="utf-8", errors="ignore")
        out["lint"]["last_run"] = lint_file.name[:10]
        m = re.search(r"(\d+)개 파일 검사", text)
        if m:
            out["lint"]["total_checked"] = int(m.group(1))
        m = re.search(r"총 (\d+)건", text)
        if m:
            out["lint"]["issues_total"] = int(m.group(1))
        for rule in ["L001", "L002", "L003", "L004", "L005", "L006"]:
            out["lint"]["rules"][rule] = {"issues": text.count(f"[{rule}]")}

    gate_file = _latest_report("*-wiki-gate-report.md")
    if gate_file:
        text = gate_file.read_text(encoding="utf-8", errors="ignore")
        out["gate"]["last_run"] = gate_file.name[:10]
        m = re.search(r"총 (\d+)개 검사", text)
        if m:
            out["gate"]["total_scanned"] = int(m.group(1))
        m = re.search(r"(\d+)개 승격", text)
        if m:
            out["gate"]["promotions"] = int(m.group(1))
        for fk, fname in {"F1": "Schema", "F2": "Duplicate", "F3": "Relevance", "F4": "Link", "F5": "Age"}.items():
            out["gate"]["filters"][fk] = {"name": fname, "failed": text.count(f"❌ {fk}-")}
        out["gate"]["failed_total"] = sum(v["failed"] for v in out["gate"]["filters"].values())

    l007_file = _latest_report("*-wiki-link-suggest.md")
    if l007_file:
        text = l007_file.read_text(encoding="utf-8", errors="ignore")
        out["l007"]["last_run"] = l007_file.name[:10]
        m = re.search(r"(\d+)[개\s].*?링크 부족", text)
        if m:
            out["l007"]["under_linked"] = int(m.group(1))
        m = re.search(r"(\d+)개.*?적용", text)
        if m:
            out["l007"]["applied"] = int(m.group(1))

    return jsonify(out)


@os_bp.route("/charlie-status")
def charlie_status():
    """Charlie 감사관 현황 — docs/data/charlie_status.json 기반."""
    candidates = [
        ROOT / "docs" / "data" / "charlie_status.json",
        ROOT / "data" / "charlie_status.json",
    ]
    for path in candidates:
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                return jsonify(data)
            except Exception:
                pass
    return jsonify({"status": "no_data", "message": "charlie_audit.py를 실행하여 상태를 생성하세요."})


@os_bp.route("/wiki-gate/run", methods=["POST"])
def wiki_gate_run():
    """Trigger wiki pipeline scripts asynchronously (mode: lint / gate / link)."""
    import sys
    mode = request.args.get("mode", "lint")
    script_map = {
        "lint": Path(__file__).parent / "wiki_lint.py",
        "gate": Path(__file__).parent / "wiki_gate.py",
        "link": Path(__file__).parent / "wiki_link_suggest.py",
    }
    script = script_map.get(mode)
    if not script or not script.exists():
        return jsonify({"error": f"unknown mode: {mode}"}), 400
    try:
        proc = subprocess.Popen(
            [sys.executable, "-X", "utf8", str(script)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return jsonify({"ok": True, "pid": proc.pid, "mode": mode})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
