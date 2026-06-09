#!/usr/bin/env python3
"""Local Bucky chat server for the Daily Plus dashboard.

Listens on http://localhost:8765 and provides a synchronous /chat endpoint
so the browser can POST a message and receive Bucky's response inline.

Usage:
    python scripts/bucky_chat_server.py
    python scripts/bucky_chat_server.py --port 8765

Endpoints:
    POST /chat   {"message": "...", "session_id": "optional"}
                 → {"reply": "...", "session_id": "..."}
    DELETE /chat {"session_id": "..."} → {"ok": true}
    GET  /health → {"status": "ok"}
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
import uuid
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INTAKE_QUEUE_DIR = ROOT / "data" / "intake_queue"
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from flask import Flask, jsonify, request

from bucky_client import BuckyError, run_bucky

app = Flask(__name__)


@app.after_request
def _cors(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, DELETE, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return response


@app.route("/chat", methods=["OPTIONS"])
@app.route("/health", methods=["OPTIONS"])
@app.route("/intake", methods=["OPTIONS"])
def _preflight():
    return "", 204

MAX_HISTORY = 20
_sessions: dict[str, list[dict]] = defaultdict(list)


def _build_prompt(history: list[dict], user_message: str) -> str:
    history_text = "\n".join(
        f"{'User' if m['role'] == 'user' else 'Bucky'}: {m['content']}"
        for m in history
    )
    if history_text:
        history_text += f"\nUser: {user_message}"
    else:
        history_text = f"User: {user_message}"

    return (
        "## BUCKY DAILY-PLUS CHAT MODE\n\n"
        "You are Bucky. The user is interacting from the Daily Plus dashboard.\n"
        "Answer in Korean when the user writes Korean. Be direct and practical.\n"
        "For analysis requests: summarize findings → key insights → next actions.\n"
        "For follow-up questions: be concise and continue the context naturally.\n\n"
        "---\n\n"
        f"{history_text}\nBucky:"
    )


@app.get("/health")
def health():
    return jsonify({"status": "ok", "time": time.time()})


@app.post("/chat")
def chat():
    data = request.get_json(silent=True) or {}
    message = (data.get("message") or "").strip()
    if not message:
        return jsonify({"error": "message is required"}), 400

    session_id = (data.get("session_id") or "").strip() or str(uuid.uuid4())
    history = _sessions[session_id]

    prompt = _build_prompt(history, message)

    try:
        reply = run_bucky(prompt, task_type="chat")
    except BuckyError as exc:
        return jsonify({"error": str(exc)}), 500

    history.append({"role": "user", "content": message})
    history.append({"role": "assistant", "content": reply})
    if len(history) > MAX_HISTORY * 2:
        _sessions[session_id] = history[-(MAX_HISTORY * 2):]

    return jsonify({"reply": reply, "session_id": session_id})


@app.post("/")
def intake():
    """Compatibility route for postToBucky() calls (command tray, etc.)
    Extracts the body text and routes it to the chat handler."""
    data = request.get_json(silent=True) or {}
    message = (data.get("body") or data.get("message") or "").strip()
    if not message:
        return jsonify({"error": "message is required"}), 400

    session_id = (data.get("session_id") or "").strip() or str(uuid.uuid4())
    history = _sessions[session_id]
    prompt = _build_prompt(history, message)

    try:
        reply = run_bucky(prompt, task_type="chat")
    except BuckyError as exc:
        return jsonify({"error": str(exc)}), 500

    history.append({"role": "user", "content": message})
    history.append({"role": "assistant", "content": reply})
    if len(history) > MAX_HISTORY * 2:
        _sessions[session_id] = history[-(MAX_HISTORY * 2):]

    return jsonify({"reply": reply, "session_id": session_id})


@app.post("/intake")
def intake_dashboard():
    """Dashboard intake — atomic queue write, 202 Accepted immediately.

    Never calls run_bucky() or requests anything from port 8766.
    The discord_bot async consumer picks up queue files.
    """
    data = request.get_json(silent=True) or {}
    if not isinstance(data, dict):
        return jsonify({"error": "JSON object payload is required"}), 400

    dashboard_type = str(data.get("dashboard_type") or "").strip()
    if not dashboard_type:
        return jsonify({"error": "dashboard_type is required"}), 400

    request_id = str(data.get("request_id") or uuid.uuid4()).strip()
    payload = {**data, "request_id": request_id, "enqueued_at": time.time()}

    INTAKE_QUEUE_DIR.mkdir(parents=True, exist_ok=True)
    safe_type = re.sub(r"[^a-z0-9_-]", "_", dashboard_type.lower())
    ts_ms = int(time.time() * 1000)
    filename = f"{ts_ms}_{safe_type}_{request_id[:8]}.json"
    tmp_path = INTAKE_QUEUE_DIR / (filename + ".tmp")
    final_path = INTAKE_QUEUE_DIR / filename
    try:
        tmp_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        tmp_path.rename(final_path)
    except Exception as exc:
        return jsonify({"error": f"queue write failed: {exc}"}), 500

    return jsonify({"status": "accepted", "request_id": request_id, "queue_file": filename}), 202


@app.post("/update-wishket")
def update_wishket():
    """Trigger wishket scraper → dashboard generator → git push.

    Returns immediately with 202 if async=true (default), or waits for result.
    """
    data = request.get_json(silent=True) or {}
    force = bool(data.get("force", False))
    async_mode = bool(data.get("async", True))

    py = sys.executable
    scraper = str(SCRIPTS / "wishket_scraper.py")
    generator = str(SCRIPTS / "generate_wishket_dashboard.py")

    def _run():
        env = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"}
        scraper_args = [py, "-X", "utf8", scraper]
        if force:
            scraper_args.append("--clear-cache")
        r1 = subprocess.run(scraper_args, capture_output=True, text=True, env=env, cwd=str(ROOT))
        if r1.returncode != 0:
            return {"ok": False, "step": "scraper", "stderr": r1.stderr[-500:]}

        r2 = subprocess.run([py, "-X", "utf8", generator], capture_output=True, text=True, env=env, cwd=str(ROOT))
        if r2.returncode != 0:
            return {"ok": False, "step": "generator", "stderr": r2.stderr[-500:]}

        r3 = subprocess.run(
            ["git", "add", "docs/wishket.html"],
            capture_output=True, text=True, cwd=str(ROOT)
        )
        diff = subprocess.run(["git", "diff", "--cached", "--stat"], capture_output=True, text=True, cwd=str(ROOT))
        if not diff.stdout.strip():
            return {"ok": True, "changed": False, "msg": "공고 변경 없음"}

        subprocess.run(
            ["git", "commit", "-m", "chore: wishket 대시보드 수동 업데이트"],
            capture_output=True, text=True, cwd=str(ROOT)
        )
        r4 = subprocess.run(["git", "push"], capture_output=True, text=True, cwd=str(ROOT))
        if r4.returncode != 0:
            return {"ok": False, "step": "push", "stderr": r4.stderr[-500:]}
        return {"ok": True, "changed": True, "msg": "업데이트 완료, GitHub Pages 배포 중 (1~2분)"}

    if async_mode:
        import threading
        threading.Thread(target=_run, daemon=True).start()
        return jsonify({"status": "running", "msg": "업데이트 시작됨. 1~2분 후 새로고침하세요."}), 202

    result = _run()
    code = 200 if result.get("ok") else 500
    return jsonify(result), code


@app.post("/update-profile")
def update_profile():
    """위시켓 프로필 자동 업데이트 (헤드라인 + 자기소개)."""
    py = sys.executable
    scraper = str(SCRIPTS / "wishket_scraper.py")

    def _run():
        env = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"}
        r = subprocess.run(
            [py, "-X", "utf8", scraper, "--update-profile"],
            capture_output=True, text=True, env=env, cwd=str(ROOT)
        )
        if r.returncode != 0:
            return {"ok": False, "stderr": r.stderr[-500:]}
        return {"ok": True, "msg": "프로필 업데이트 완료"}

    import threading
    threading.Thread(target=_run, daemon=True).start()
    return jsonify({"status": "running", "msg": "프로필 업데이트 시작됨. 30초 후 위시켓에서 확인하세요."}), 202


@app.delete("/chat")
def clear_chat():
    data = request.get_json(silent=True) or {}
    session_id = (data.get("session_id") or "").strip()
    if session_id and session_id in _sessions:
        del _sessions[session_id]
    return jsonify({"ok": True})


def main() -> None:
    parser = argparse.ArgumentParser(description="Bucky local chat server for Daily Plus")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--host", default="127.0.0.1")
    args = parser.parse_args()

    print(f"[bucky-chat-server] Starting on http://{args.host}:{args.port}")
    print(f"[bucky-chat-server] Chat endpoint: POST http://{args.host}:{args.port}/chat")
    app.run(host=args.host, port=args.port, debug=False)


if __name__ == "__main__":
    main()
