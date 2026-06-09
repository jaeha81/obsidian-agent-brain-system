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

from flask import Flask, jsonify, request, send_from_directory

from bucky_client import BuckyError, run_bucky

DOCS_DIR = ROOT / "docs"

app = Flask(__name__)

try:
    from bucky_os_api import os_bp
    app.register_blueprint(os_bp)
except Exception as _e:
    print(f"[bucky-chat-server] OS API blueprint skipped: {_e}")

try:
    from bucky_agent_os_api import agent_os_bp
    app.register_blueprint(agent_os_bp)
except Exception as _e:
    print(f"[bucky-chat-server] Agent OS API blueprint skipped: {_e}")


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


@app.route("/tablet-intake", methods=["OPTIONS"])
def _tablet_intake_preflight():
    return "", 204


@app.post("/tablet-intake")
def tablet_intake():
    """태블릿 음성 인테이크 수신 엔드포인트.

    tablet_voice_intake.py 가 전송하는 tablet-batch-upload-manifest 형식을 수신.
    트랜스크립트를 ObsidianVault/04_SiteLog/voice_log_{DATE}.md 에 누적 저장.
    """
    VAULT = ROOT / "ObsidianVault"
    SITE_LOG_DIR = VAULT / "04_SiteLog"

    data = request.get_json(silent=True)
    if not data or not isinstance(data, dict):
        return jsonify({"error": "JSON object payload is required"}), 400

    batch_id = str(data.get("batch_id") or "unknown")
    device = str(data.get("source_device") or "tablet")
    chunks: list[dict] = data.get("chunks") or []
    upload_time = str(data.get("upload_time") or "")
    vault_path = str(data.get("vault_path") or "04_SiteLog")
    tags: list[str] = data.get("tags") or []

    if not chunks:
        return jsonify({"error": "chunks array is empty"}), 400

    # ── 날짜 파싱 ────────────────────────────────────────────────────────────
    try:
        from datetime import datetime as _dt, timezone as _tz
        date_str = _dt.now(_tz.utc).strftime("%Y-%m-%d")
    except Exception:
        import time as _t
        date_str = _t.strftime("%Y-%m-%d")

    # ── Vault 경로 결정 ───────────────────────────────────────────────────────
    # vault_path 이 상대경로면 ObsidianVault 기준, 아니면 고정
    log_dir = VAULT / vault_path.lstrip("/\\")
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"voice_log_{date_str}.md"

    # ── 트랜스크립트 추출 ──────────────────────────────────────────────────
    lines: list[str] = []
    for chunk in chunks:
        ts = str(chunk.get("ts") or "").replace("T", " ")[:19]
        transcript = str(chunk.get("transcript") or "").strip()
        intent = str(chunk.get("intent") or "")
        entities = chunk.get("entities") or []
        if not transcript:
            continue
        entry = f"- **{ts}** [{intent}] {transcript}"
        if entities:
            ent_str = ", ".join(
                str(e.get("value") or e) if isinstance(e, dict) else str(e)
                for e in entities[:5]
            )
            entry += f" `[{ent_str}]`"
        lines.append(entry)

    if not lines:
        return jsonify({"error": "no transcripts in chunks"}), 400

    # ── Markdown 파일 append ──────────────────────────────────────────────
    tag_str = " ".join(f"#{t}" for t in tags) if tags else "#voice #tablet"
    header_needed = not log_file.exists()

    with open(log_file, "a", encoding="utf-8") as f:
        if header_needed:
            f.write(f"---\n")
            f.write(f"type: voice-log\n")
            f.write(f"date: {date_str}\n")
            f.write(f"device: {device}\n")
            f.write(f"tags: [{', '.join(tags)}]\n")
            f.write(f"---\n\n")
            f.write(f"# 음성 로그 — {date_str}\n\n")

        f.write(f"\n## 배치: {batch_id} ({device})\n\n")
        f.write("\n".join(lines))
        f.write("\n")

    log_file_rel = str(log_file.relative_to(ROOT)) if log_file.is_relative_to(ROOT) else str(log_file)

    return jsonify({
        "status": "accepted",
        "batch_id": batch_id,
        "chunks_saved": len(lines),
        "log_file": log_file_rel,
        "checked_at": upload_time or date_str,
    }), 202


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


@app.get("/")
@app.get("/index.html")
def serve_index():
    return send_from_directory(str(DOCS_DIR), "index.html")


@app.get("/bucky-os.html")
def serve_bucky_os():
    return send_from_directory(str(DOCS_DIR), "bucky-os.html")


@app.get("/launch")
def auto_launch():
    """localhost 전용 자동 로그인 → Bucky OS 리다이렉트 (바탕화면 바로가기용)."""
    if request.remote_addr not in ("127.0.0.1", "::1"):
        return jsonify({"error": "localhost only"}), 403
    from flask import make_response, redirect
    resp = make_response(redirect("/bucky-os.html"))
    resp.set_cookie("bucky_auth", "local", path="/", httponly=False)
    return resp


@app.get("/<path:filename>")
def serve_docs(filename):
    return send_from_directory(str(DOCS_DIR), filename)


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
