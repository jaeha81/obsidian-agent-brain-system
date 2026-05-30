#!/usr/bin/env python3
"""Supervise the Discord Bucky bot without relying on window titles.

This wrapper is intended for the home PC runtime. It starts
``scripts/discord_bot.py``, writes the child PID to AgentBus signals, watches
for ``bot_restart.signal``, and restarts the child process when requested or
after an unexpected exit.
"""

from __future__ import annotations

import csv
import json
import os
import socket
import subprocess
import sys
import time
import urllib.request
from datetime import datetime
from pathlib import Path

try:
    from dotenv import load_dotenv
    _env_path = Path(__file__).resolve().parent.parent / ".env"
    if _env_path.exists():
        load_dotenv(_env_path, encoding="utf-8")
except ImportError:
    pass

ROOT = Path(__file__).resolve().parent.parent
BOT_SCRIPT = ROOT / "scripts" / "discord_bot.py"
SIGNAL_DIR = ROOT / "ObsidianVault" / "10_AgentBus" / "signals"
SIGNAL_FILE = SIGNAL_DIR / "bot_restart.signal"
PID_FILE = SIGNAL_DIR / "bucky_bot.pid"
LOG_FILE = ROOT / "discord_bot.log"
ERR_FILE = ROOT / "discord_bot.err"
POLL_SECONDS = int(os.getenv("BUCKY_SUPERVISOR_INTERVAL", "10"))
RESTART_DELAY_SECONDS = int(os.getenv("BUCKY_SUPERVISOR_RESTART_DELAY", "5"))
DISCORD_WEBHOOK_URL: str = os.getenv("DISCORD_WEBHOOK_URL", "")

# 재시작 통계
_restart_count = 0


def send_webhook(text: str) -> None:
    if not DISCORD_WEBHOOK_URL:
        return
    try:
        import requests as _requests
        _requests.post(
            DISCORD_WEBHOOK_URL,
            json={"content": text},
            timeout=8,
            allow_redirects=True,
        )
    except Exception as e:
        log(f"웹훅 전송 실패: {e}")


def show_windows_toast(title: str, message: str) -> None:
    """PowerShell BurntToast or fallback balloon via msg.exe."""
    if os.name != "nt":
        return
    try:
        ps_script = (
            f"Add-Type -AssemblyName System.Windows.Forms; "
            f"$n = New-Object System.Windows.Forms.NotifyIcon; "
            f"$n.Icon = [System.Drawing.SystemIcons]::Warning; "
            f"$n.Visible = $true; "
            f"$n.ShowBalloonTip(8000, '{title}', '{message}', "
            f"[System.Windows.Forms.ToolTipIcon]::Warning); "
            f"Start-Sleep 2; $n.Dispose()"
        )
        subprocess.Popen(
            ["powershell", "-NonInteractive", "-WindowStyle", "Hidden", "-Command", ps_script],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception as e:
        log(f"토스트 알림 실패: {e}")


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
    # Keep redirected log handles alive for the child process on Windows.
    proc._bucky_stdout = stdout  # type: ignore[attr-defined]
    proc._bucky_stderr = stderr  # type: ignore[attr-defined]
    write_pid(proc.pid)
    log(f"Started discord_bot.py pid={proc.pid}")
    return proc


def close_bot_log_handles(proc: subprocess.Popen | None) -> None:
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
        try:
            delattr(proc, attr)
        except AttributeError:
            pass


def stop_bot(proc: subprocess.Popen | None) -> None:
    if proc is None or proc.poll() is not None:
        close_bot_log_handles(proc)
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
    close_bot_log_handles(proc)
    remove_pid()


def run() -> int:
    send_webhook(f"🟢 **Bucky 슈퍼바이저 시작** | PC: `{socket.gethostname()}`")
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
                _restart_count += 1
                ts_str = now()
                log(f"discord_bot.py exited with code {exit_code}; restarting (#{_restart_count})")
                close_bot_log_handles(proc)
                remove_pid()

                # PC 알림 + Discord 웹훅
                alert_msg = (
                    f"⚠️ **Bucky 봇 다운** (exit={exit_code})\n"
                    f"PC: `{socket.gethostname()}` | 재시작 #{_restart_count}\n"
                    f"시각: {ts_str}\n"
                    f"{RESTART_DELAY_SECONDS}초 후 자동 재시작..."
                )
                send_webhook(alert_msg)
                show_windows_toast(
                    "Bucky 봇 다운",
                    f"exit={exit_code} | 재시작 #{_restart_count} | {RESTART_DELAY_SECONDS}초 후 자동복구"
                )

                time.sleep(RESTART_DELAY_SECONDS)
                proc = start_bot()

                # 재시작 완료 알림
                send_webhook(f"✅ **Bucky 봇 재시작 완료** (PID {proc.pid}) | 재시작 #{_restart_count}")
    except KeyboardInterrupt:
        log("Supervisor interrupted")
        stop_bot(proc)
        send_webhook(f"🔴 **Bucky 슈퍼바이저 수동 종료** | PC: `{socket.gethostname()}`")
        return 0


if __name__ == "__main__":
    raise SystemExit(run())
