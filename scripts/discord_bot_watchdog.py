#!/usr/bin/env python3
"""Keep the Discord Bucky bot running and restart it after unexpected exits."""

from __future__ import annotations

import datetime as _dt
import subprocess
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
BOT_SCRIPT = ROOT / "scripts" / "discord_bot.py"
LOG_DIR = ROOT / ".logs"
RESTART_DELAY_SECONDS = 10
CHECK_INTERVAL_SECONDS = 30


def log(message: str) -> None:
    ts = _dt.datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {message}", flush=True)


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
