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
import os
import sys
import time
import uuid
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
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
