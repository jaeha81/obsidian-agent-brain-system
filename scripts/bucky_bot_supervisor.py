#!/usr/bin/env python3
"""Supervise the Discord Bucky bot without relying on window titles.

This wrapper is intended for the home PC runtime. It starts
``scripts/discord_bot.py``, writes the child PID to AgentBus signals, watches
for ``bot_restart.signal``, and restarts the child process when requested or
after an unexpected exit.
"""

from __future__ import annotations

import csv
import os
import socket
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
BOT_SCRIPT = ROOT / "scripts" / "discord_bot.py"
SIGNAL_DIR = ROOT / "ObsidianVault" / "10_AgentBus" / "signals"
SIGNAL_FILE = SIGNAL_DIR / "bot_restart.signal"
PID_FILE = SIGNAL_DIR / "bucky_bot.pid"
LOG_FILE = ROOT / "discord_bot.log"
ERR_FILE = ROOT / "discord_bot.err"
POLL_SECONDS = int(os.getenv("BUCKY_SUPERVISOR_INTERVAL", "10"))
RESTART_DELAY_SECONDS = int(os.getenv("BUCKY_SUPERVISOR_RESTART_DELAY", "5"))


def now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def log(message: str) -> None:
    print(f"[Supervisor {now()}] {message}", flush=True)


def is_pid_running(pid: int) -> bool:
    if pid <= 0:
        return False
    if os.name == "nt":
        result = subprocess.run(
            ["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=5,
        )
        for row in csv.reader(result.stdout.splitlines()):
            if len(row) > 1 and row[1].strip() == str(pid):
                return True
        return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def existing_child_is_running() -> bool:
    try:
        pid = int(PID_FILE.read_text(encoding="utf-8").strip())
    except Exception:
        return False
    return is_pid_running(pid)


def find_existing_bot_pids() -> list[int]:
    """프로세스 명령줄로 실행 중인 discord_bot.py 프로세스 PID 목록 반환 (자신 제외)."""
    self_pid = os.getpid()
    pids: list[int] = []

    if os.name == "nt":
        try:
            result = subprocess.run(
                [
                    "wmic", "process", "where",
                    "CommandLine like '%discord_bot%'",
                    "get", "ProcessId", "/format:value",
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=10,
            )
            for line in result.stdout.splitlines():
                line = line.strip()
                if line.startswith("ProcessId="):
                    val = line.split("=", 1)[1].strip()
                    if val.isdigit():
                        pid = int(val)
                        if pid and pid != self_pid:
                            pids.append(pid)
        except Exception as exc:
            log(f"find_existing_bot_pids wmic 오류: {exc}")
    else:
        try:
            result = subprocess.run(
                ["pgrep", "-f", "discord_bot.py"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            for line in result.stdout.splitlines():
                try:
                    pid = int(line.strip())
                    if pid != self_pid:
                        pids.append(pid)
                except ValueError:
                    pass
        except Exception as exc:
            log(f"find_existing_bot_pids pgrep 오류: {exc}")

    return pids


def kill_pid(pid: int) -> None:
    """지정 PID 강제 종료."""
    try:
        if os.name == "nt":
            subprocess.run(
                ["taskkill", "/F", "/PID", str(pid)],
                capture_output=True,
                timeout=5,
            )
        else:
            import signal as _signal
            os.kill(pid, _signal.SIGTERM)
    except Exception as exc:
        log(f"kill_pid({pid}) 실패: {exc}")


def clear_restart_signal() -> None:
    try:
        SIGNAL_FILE.unlink(missing_ok=True)
    except OSError as exc:
        log(f"Could not remove restart signal: {exc}")


def write_pid(pid: int) -> None:
    SIGNAL_DIR.mkdir(parents=True, exist_ok=True)
    PID_FILE.write_text(str(pid), encoding="ascii")


def remove_pid() -> None:
    try:
        PID_FILE.unlink(missing_ok=True)
    except OSError:
        pass


def start_bot() -> subprocess.Popen:
    SIGNAL_DIR.mkdir(parents=True, exist_ok=True)
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    stdout = LOG_FILE.open("a", encoding="utf-8", errors="replace")
    stderr = ERR_FILE.open("a", encoding="utf-8", errors="replace")
    try:
        proc = subprocess.Popen(
            [sys.executable, str(BOT_SCRIPT)],
            cwd=str(ROOT),
            stdout=stdout,
            stderr=stderr,
            stdin=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    finally:
        stdout.close()
        stderr.close()
    write_pid(proc.pid)
    log(f"Started discord_bot.py pid={proc.pid}")
    return proc


def stop_bot(proc: subprocess.Popen | None) -> None:
    if proc is None or proc.poll() is not None:
        remove_pid()
        return
    log(f"Stopping discord_bot.py pid={proc.pid}")
    proc.terminate()
    try:
        proc.wait(timeout=15)
    except subprocess.TimeoutExpired:
        log(f"Force killing discord_bot.py pid={proc.pid}")
        proc.kill()
        proc.wait(timeout=10)
    remove_pid()


def run() -> int:
    log(f"Home PC supervisor starting on {socket.gethostname()}")
    log(f"Restart signal: {SIGNAL_FILE}")
    log(f"Logs: {LOG_FILE.name} / {ERR_FILE.name}")

    # ── 기존 discord_bot.py 프로세스 탐지 (PID 파일 + 이름 기반) ─────────────────
    # PID 파일로 확인
    if existing_child_is_running():
        pid_str = PID_FILE.read_text(encoding="utf-8").strip()
        log(f"Existing bot pid={pid_str} is already running (PID file); not starting duplicate.")
        return 0

    # 이름 기반 검색: PID 파일 없이 직접 실행된 경우도 감지
    orphan_pids = find_existing_bot_pids()
    if orphan_pids:
        log(f"Orphaned discord_bot.py processes detected: {orphan_pids} - terminating before start")
        for pid in orphan_pids:
            kill_pid(pid)
        time.sleep(2)
        # 종료 확인
        still_running = [p for p in orphan_pids if is_pid_running(p)]
        if still_running:
            log(f"WARNING: {still_running} could not be terminated; proceeding anyway")

    clear_restart_signal()
    proc: subprocess.Popen | None = start_bot()

    try:
        while True:
            time.sleep(POLL_SECONDS)

            if SIGNAL_FILE.exists():
                log("Restart signal detected")
                clear_restart_signal()
                stop_bot(proc)
                time.sleep(2)
                proc = start_bot()
                continue

            if proc.poll() is not None:
                exit_code = proc.returncode
                log(f"discord_bot.py exited with code {exit_code}; restarting")
                remove_pid()
                time.sleep(RESTART_DELAY_SECONDS)
                proc = start_bot()
    except KeyboardInterrupt:
        log("Supervisor interrupted")
        stop_bot(proc)
        return 0


if __name__ == "__main__":
    raise SystemExit(run())
