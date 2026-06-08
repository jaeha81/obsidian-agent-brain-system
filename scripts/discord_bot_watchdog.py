#!/usr/bin/env python3
"""Keep the Discord Bucky bot running and restart it after unexpected exits."""

from __future__ import annotations

import datetime as _dt
import os
import subprocess
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
BOT_SCRIPT = ROOT / "scripts" / "discord_bot.py"
LOG_DIR = ROOT / ".logs"
PID_FILE = ROOT / "logs" / "discord_bot.pid"
RESTART_DELAY_SECONDS = 10
CHECK_INTERVAL_SECONDS = 30


def log(message: str) -> None:
    ts = _dt.datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {message}", flush=True)


def _pid_alive(pid: int) -> bool:
    # os.kill(pid, 0) raises WinError 87 on Windows Python 3.14+ — use tasklist instead
    if sys.platform == "win32":
        try:
            result = subprocess.run(
                ["tasklist", "/FI", f"PID eq {pid}", "/NH", "/FO", "CSV"],
                capture_output=True, text=True, encoding="utf-8", errors="replace",
            )
            return f'"{pid}"' in result.stdout or f",{pid}," in result.stdout
        except Exception:
            return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def start_bot() -> subprocess.Popen:
    LOG_DIR.mkdir(exist_ok=True)
    ts = _dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    out_log = LOG_DIR / f"discord_bot_out_{ts}.log"
    err_log = LOG_DIR / f"discord_bot_err_{ts}.log"
    stdout = out_log.open("w", encoding="utf-8", errors="replace")
    stderr = err_log.open("w", encoding="utf-8", errors="replace")
    proc = subprocess.Popen(
        [sys.executable, "-X", "utf8", str(BOT_SCRIPT)],
        cwd=str(ROOT),
        stdout=stdout,
        stderr=stderr,
        stdin=subprocess.DEVNULL,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    proc._bucky_stdout = stdout  # type: ignore[attr-defined]
    proc._bucky_stderr = stderr  # type: ignore[attr-defined]
    log(f"Bot started pid={proc.pid} log={out_log.name}")
    return proc


def close_log_handles(proc: subprocess.Popen | None) -> None:
    if proc is None:
        return
    for attr in ("_bucky_stdout", "_bucky_stderr"):
        handle = getattr(proc, attr, None)
        if handle is None:
            continue
        try:
            handle.close()
        except OSError:
            pass


def cleanup_old_logs(days: int = 7) -> None:
    cutoff = time.time() - days * 86400
    for path in LOG_DIR.glob("discord_bot_*.log"):
        try:
            if path.stat().st_mtime < cutoff:
                path.unlink(missing_ok=True)
        except OSError as exc:
            log(f"Could not remove old log {path.name}: {exc}")


def main() -> int:
    if not BOT_SCRIPT.exists():
        log(f"Bot script missing: {BOT_SCRIPT}")
        return 1

    log(f"Watchdog starting check={CHECK_INTERVAL_SECONDS}s restart_delay={RESTART_DELAY_SECONDS}s")
    cleanup_old_logs()

    # 기존 봇이 실행 중이면 새로 시작하지 않고 PID를 감시
    existing_pid: int | None = None
    try:
        existing_pid = int(PID_FILE.read_text().strip())
        if not _pid_alive(existing_pid):
            existing_pid = None
    except (OSError, ValueError, FileNotFoundError):
        existing_pid = None

    if existing_pid is not None:
        log(f"Existing bot detected pid={existing_pid}, monitoring without restart")
        try:
            while _pid_alive(existing_pid):
                time.sleep(CHECK_INTERVAL_SECONDS)
            log(f"Adopted bot pid={existing_pid} exited; restarting in {RESTART_DELAY_SECONDS}s")
            time.sleep(RESTART_DELAY_SECONDS)
            cleanup_old_logs()
        except KeyboardInterrupt:
            log("Watchdog interrupted")
            return 0

    bot = start_bot()
    try:
        while True:
            time.sleep(CHECK_INTERVAL_SECONDS)
            ret = bot.poll()
            if ret is None:
                continue
            log(f"Bot exited exit={ret}; restarting in {RESTART_DELAY_SECONDS}s")
            close_log_handles(bot)
            time.sleep(RESTART_DELAY_SECONDS)
            cleanup_old_logs()
            bot = start_bot()
    except KeyboardInterrupt:
        log("Watchdog interrupted")
        close_log_handles(bot)
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
