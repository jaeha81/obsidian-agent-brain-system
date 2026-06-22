#!/usr/bin/env python3
"""
Bucky Watchdog — 자가복구 감시 데몬

역할:
  - Bucky(discord_bot.py) 프로세스를 지속 감시
  - 다운 감지 시 자동 재시작 + Discord 웹훅 알림
  - 재시작 전 오류 로그 수집 → ObsidianVault/10_AgentBus/error-logs/ 저장
  - 연속 실패 3회 → Claude Code / Codex에 긴급 복구 요청 전송

실행: python scripts/bucky_watchdog.py
Docker: docker-compose up watchdog
"""

import json
import os
import platform
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

_ROOT = Path(__file__).parent.parent
load_dotenv(_ROOT / ".env", encoding="utf-8-sig")

DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK_URL", "")
BUCKY_SCRIPT = str(_ROOT / "scripts" / "discord_bot.py")
CHAT_SERVER_SCRIPT = str(_ROOT / "scripts" / "bucky_chat_server.py")
ERROR_LOG_DIR = _ROOT / "ObsidianVault" / "10_AgentBus" / "error-logs"
STATE_FILE = _ROOT / ".agent" / "watchdog_state.json"

MAX_RETRIES = 3          # 연속 실패 이 횟수 초과 시 긴급 알림
RETRY_DELAY = 15         # 재시작 대기(초)
HEALTH_INTERVAL = 30     # 헬스체크 주기(초)


# ── 유틸 ──────────────────────────────────────────────────────────────────────

def ts() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def log(msg: str) -> None:
    print(f"[WATCHDOG {ts()}] {msg}", flush=True)


def send_webhook(text: str) -> None:
    if not DISCORD_WEBHOOK:
        return
    try:
        import urllib.request
        data = json.dumps({"content": text}).encode()
        req = urllib.request.Request(
            DISCORD_WEBHOOK,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        urllib.request.urlopen(req, timeout=5)
    except Exception as e:
        log(f"웹훅 전송 실패: {e}")


def save_error_log(stdout: str, stderr: str, exit_code: int) -> Path:
    ERROR_LOG_DIR.mkdir(parents=True, exist_ok=True)
    fname = ERROR_LOG_DIR / f"bucky-crash-{datetime.now().strftime('%Y%m%d-%H%M%S')}.md"
    content = f"""---
type: error-log
agent: bucky
exit_code: {exit_code}
timestamp: {ts()}
---

## Bucky 충돌 로그

### stdout
```
{stdout[-3000:] if stdout else '(없음)'}
```

### stderr
```
{stderr[-3000:] if stderr else '(없음)'}
```
"""
    fname.write_text(content, encoding="utf-8")
    log(f"오류 로그 저장: {fname.name}")
    return fname


def load_state() -> dict:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"consecutive_failures": 0, "total_restarts": 0, "last_restart": None}


def save_state(state: dict) -> None:
    STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")


def request_emergency_recovery(failure_count: int, log_path: Path) -> None:
    """긴급 복구 요청 — AgentBus inbox에 메시지 투입"""
    inbox = _ROOT / "ObsidianVault" / "10_AgentBus" / "inbox"
    inbox.mkdir(parents=True, exist_ok=True)
    msg = {
        "id": f"emergency-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "from": "watchdog",
        "to": "claudecode",
        "type": "emergency_recovery",
        "priority": "P0",
        "timestamp": ts(),
        "payload": {
            "agent": "bucky",
            "consecutive_failures": failure_count,
            "error_log": str(log_path),
            "action": "diagnose_and_restart",
        },
    }
    msg_file = inbox / f"{msg['id']}.json"
    msg_file.write_text(json.dumps(msg, indent=2, ensure_ascii=False), encoding="utf-8")
    log(f"긴급 복구 요청 전송: {msg_file.name}")

    send_webhook(
        f"🚨 **Bucky 긴급 복구 요청**\n"
        f"연속 실패: {failure_count}회\n"
        f"오류 로그: `{log_path.name}`\n"
        f"ClaudeCode에 복구 지시 전송됨."
    )


# ── 프로세스 관리 ─────────────────────────────────────────────────────────────

def start_bucky() -> subprocess.Popen:
    python = sys.executable
    env = {**os.environ}
    proc = subprocess.Popen(
        [python, BUCKY_SCRIPT],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
    )
    log(f"Bucky 시작 (PID {proc.pid})")
    return proc


def start_chat_server() -> subprocess.Popen:
    python = sys.executable
    env = {**os.environ}
    log_path = _ROOT / "logs" / "chat_server_watchdog.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_fh = open(log_path, "a", encoding="utf-8")
    proc = subprocess.Popen(
        [python, "-X", "utf8", CHAT_SERVER_SCRIPT, "--port", "8765"],
        stdout=log_fh,
        stderr=log_fh,
        env=env,
    )
    log(f"BuckyChatServer 시작 (PID {proc.pid})")
    return proc


def collect_output(proc: subprocess.Popen, timeout: float = 2.0) -> tuple[str, str]:
    try:
        out, err = proc.communicate(timeout=timeout)
        return out or "", err or ""
    except subprocess.TimeoutExpired:
        return "", ""


# ── 메인 루프 ─────────────────────────────────────────────────────────────────

def run() -> None:
    log("Watchdog 시작")
    state = load_state()
    proc: subprocess.Popen | None = None
    chat_proc: subprocess.Popen | None = None

    while True:
        # ── bucky_chat_server 감시 ──────────────────────────────────────────
        if chat_proc is None or chat_proc.poll() is not None:
            if chat_proc is not None and chat_proc.poll() is not None:
                log(f"BuckyChatServer 종료 (exit={chat_proc.poll()}) — 재시작")
                send_webhook("⚠️ **BuckyChatServer 다운** — 자동 재시작")
            time.sleep(2)
            chat_proc = start_chat_server()

        # ── Discord 봇 감시 ─────────────────────────────────────────────────
        if proc is None or proc.poll() is not None:
            exit_code = proc.poll() if proc is not None else None

            if exit_code is not None:
                # 비정상 종료
                out, err = collect_output(proc)
                log(f"Bucky 종료 (exit={exit_code})")
                log_path = save_error_log(out, err, exit_code)

                state["consecutive_failures"] += 1
                state["total_restarts"] += 1
                state["last_restart"] = ts()
                save_state(state)

                send_webhook(
                    f"⚠️ **Bucky 다운** (exit={exit_code})\n"
                    f"연속 실패: {state['consecutive_failures']}회 · "
                    f"총 재시작: {state['total_restarts']}회\n"
                    f"{RETRY_DELAY}초 후 자동 재시작..."
                )

                if state["consecutive_failures"] >= MAX_RETRIES:
                    request_emergency_recovery(state["consecutive_failures"], log_path)
                    log(f"연속 {MAX_RETRIES}회 실패 — 긴급 복구 요청 후 60초 대기")
                    time.sleep(60)
                else:
                    time.sleep(RETRY_DELAY)

            # 재시작
            proc = start_bucky()
            send_webhook(f"✅ **Bucky 재시작** (PID {proc.pid})")

        else:
            # 정상 실행 중 → 연속 실패 카운트 리셋
            if state["consecutive_failures"] > 0:
                state["consecutive_failures"] = 0
                save_state(state)

        time.sleep(HEALTH_INTERVAL)


if __name__ == "__main__":
    run()
