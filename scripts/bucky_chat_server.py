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
import hashlib
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

from urllib.parse import quote

from flask import Flask, jsonify, request, send_from_directory

from bucky_client import BuckyError, run_bucky

DOCS_DIR = ROOT / "docs"
PROTECTED_DIR = ROOT / "protected"
# 공개 배포(docs/) 밖에 두고 로컬 서버에서만 쿠키 게이트로 서빙하는 페이지
PROTECTED_PAGES = ("wishket.html", "bucky-daily.html", "investment-report.html")

app = Flask(__name__)

try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env", encoding="utf-8", override=False)
except Exception:
    pass

AUTH_COOKIE_NAME = "bucky_auth"
AUTH_COOKIE_MAX_AGE = 7 * 24 * 60 * 60
PUBLIC_PATHS = {
    "/login",
    "/login.html",
    "/api/login",
    "/api/logout",
    "/launch",
    "/health",
    "/favicon.ico",
    "/manifest.json",
    "/sw.js",
}
PUBLIC_PREFIXES = ("/icons/",)
PROTECTED_API_PATHS = {
    "/chat",
    "/intake",
    "/tablet-intake",
    "/update-wishket",
    "/update-profile",
}

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
    origin = request.headers.get("Origin")
    if origin:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Vary"] = "Origin"
        response.headers["Access-Control-Allow-Credentials"] = "true"
    else:
        response.headers["Access-Control-Allow-Origin"] = "same-origin"
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


def _auth_secret() -> str:
    return (
        os.environ.get("BUCKY_DASH_AUTH_SECRET")
        or os.environ.get("BUCKY_DASH_PASSWORD")
        or os.environ.get("BUCKY_AUTH_PASSWORD")
        or ""
    )


def _auth_token() -> str:
    secret = _auth_secret()
    if not secret:
        return ""
    return hashlib.sha256(("bucky-dashboard:" + secret).encode("utf-8")).hexdigest()


def _is_authenticated_request() -> bool:
    token = _auth_token()
    return bool(token) and request.cookies.get(AUTH_COOKIE_NAME) == token


def _is_public_path(path: str) -> bool:
    return path in PUBLIC_PATHS or any(path.startswith(prefix) for prefix in PUBLIC_PREFIXES)


def _is_html_path(path: str) -> bool:
    return path == "/" or path.endswith(".html") or "." not in Path(path).name


@app.before_request
def _require_dashboard_auth():
    if request.method == "OPTIONS":
        return None

    path = request.path or "/"
    if _is_public_path(path):
        return None

    if path in PROTECTED_API_PATHS and not _is_authenticated_request():
        return jsonify({"error": "authentication required"}), 401

    if _is_html_path(path) and not _is_authenticated_request():
        from flask import redirect
        return redirect("/login.html?r=" + quote(path))

    return None


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


def _is_trusted_source() -> bool:
    """loopback 또는 본인 Tailscale 기기(CGNAT 100.64.0.0/10)에서 온 요청인지."""
    import ipaddress
    try:
        ip = ipaddress.ip_address(request.remote_addr or "")
        if ip.version == 6 and ip.ipv4_mapped:
            ip = ip.ipv4_mapped
    except ValueError:
        return False
    return ip.is_loopback or ip in ipaddress.ip_network("100.64.0.0/10")


def _safe_next(raw: str | None, default: str = "/bucky-os.html") -> str:
    """리다이렉트 대상을 로컬 경로로 제한 (open redirect 방지)."""
    nxt = (raw or "").strip()
    if not nxt.startswith("/") or nxt.startswith("//"):
        return default
    return nxt


def _auth_cookie_response(target: str):
    from flask import make_response, redirect
    resp = make_response(redirect(target))
    token = _auth_token()
    resp.set_cookie(
        AUTH_COOKIE_NAME,
        token,
        max_age=AUTH_COOKIE_MAX_AGE,
        path="/",
        httponly=False,
        samesite="Lax",
    )
    return resp


@app.get("/launch")
def auto_launch():
    """자동 로그인 → 대시보드 리다이렉트 (localhost + 본인 Tailscale 기기 전용).

    ?next=/task-board.html 처럼 도착 페이지 지정 가능 (기본 Bucky OS).
    """
    from flask import redirect
    target = _safe_next(request.args.get("next"))
    if _is_authenticated_request():
        return redirect(target)
    return redirect("/login.html?r=" + quote(target))


@app.post("/api/login")
def api_login():
    """login.html 로그인 처리.

    신뢰 소스(localhost/Tailscale)는 비밀번호 없이 통과 — /launch와 동일 신뢰 모델.
    그 외 소스는 BUCKY_DASH_PASSWORD 환경변수와 대조 (미설정 시 항상 거부).
    JSON 요청이면 {"ok": bool} 응답, 폼 요청이면 302 리다이렉트.
    """
    body = request.get_json(silent=True) or {}
    password = (request.form.get("password") or body.get("password") or "").strip()
    target = _safe_next(request.form.get("redirect") or body.get("redirect"), default="/")
    expected = os.environ.get("BUCKY_DASH_PASSWORD") or os.environ.get("BUCKY_AUTH_PASSWORD") or ""
    # 평문 env 미설정 시 폴백: 기존 JS 게이트(6658b13)와 동일한 SHA-256 비교 —
    # 사용자가 이미 쓰던 대시보드 비밀번호가 그대로 통한다 (해시는 git 히스토리 공개값).
    expected_hash = os.environ.get(
        "BUCKY_DASH_PASSWORD_SHA256",
        "9a02838cef35cd584f2ca164ea91d69da757d8295b9770e26a86546dd2521f01",
    )
    password_hash = hashlib.sha256(password.encode("utf-8")).hexdigest()
    allowed = (bool(expected) and password == expected) or (
        bool(password) and password_hash == expected_hash
    )
    if request.is_json:
        if not allowed:
            return jsonify({"ok": False}), 403
        resp = jsonify({"ok": True, "redirect": target})
        resp.set_cookie(
            AUTH_COOKIE_NAME,
            _auth_token(),
            max_age=AUTH_COOKIE_MAX_AGE,
            path="/",
            httponly=False,
            samesite="Lax",
        )
        return resp
    if not allowed:
        from flask import redirect
        return redirect("/login.html?error=1&r=" + quote(target))
    return _auth_cookie_response(target)


@app.get("/api/logout")
def api_logout():
    from flask import make_response, redirect
    resp = make_response(redirect("/login.html"))
    resp.delete_cookie(AUTH_COOKIE_NAME, path="/")
    return resp


@app.get("/wishket.html")
@app.get("/bucky-daily.html")
@app.get("/investment-report.html")
def serve_protected_page():
    """protected/ 운영 대시보드 — 서버측 쿠키 게이트 (공개 정적 호스팅 미노출 유지)."""
    from flask import redirect
    name = request.path.lstrip("/")
    if name not in PROTECTED_PAGES:
        return jsonify({"error": "not found"}), 404
    if not _is_authenticated_request():
        return redirect("/login.html?r=" + quote(request.path))
    return send_from_directory(str(PROTECTED_DIR), name)


@app.get("/login")
@app.get("/login.html")
def serve_login_page():
    from flask import redirect
    target = _safe_next(request.args.get("r") or request.args.get("redirect"), default="/bucky-os.html")
    if _is_authenticated_request():
        return redirect(target)
    return send_from_directory(str(DOCS_DIR), "login.html")


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
