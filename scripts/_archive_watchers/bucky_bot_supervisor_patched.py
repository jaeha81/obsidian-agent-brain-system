#!/usr/bin/env python3
"""
bucky_bot_supervisor_patched.py
 — Bucky 봇 슈퍼바이저 (디스크 가드 + 토큰(4004) 인증실패 알림 보강판)

원본 bucky_bot_supervisor.py 와 동일하게 동작하되 다음 2가지를 추가:
  1) 디스크 가드: 여유 공간이 BUCKY_MIN_FREE_GB(기본 1GB) 미만이면 봇을 띄우지
     않고 웹훅 경고 후 대기 → '[Errno 28] No space left' 크래시 루프 방지
  2) 토큰 인증 실패(WebSocket 4004 / LoginFailure) 감지 시 전용 웹훅 알림 후
     긴 간격으로 재시도 → .env 토큰 교체 시 자동 복구 (디스코드 레이트리밋 회피)

적용(PC에서):
  1) 기존 scripts/bucky_bot_supervisor.py 를 bucky_bot_supervisor.py.bak 으로 백업
  2) 이 파일을 bucky_bot_supervisor.py 로 이름 변경(교체)
  3) 기존처럼 start_discord_bot.bat 실행
(또는 start_discord_bot.bat / discord_bot_watchdog.ps1 안의 파일명을
 bucky_bot_supervisor_patched.py 로 바꿔서 실행해도 됩니다.)

환경변수(선택, .env):
  BUCKY_SUPERVISOR_INTERVAL=10     # 신호/생존 점검 주기(초)
  BUCKY_SUPERVISOR_RESTART_DELAY=5 # 일반 크래시 재시작 대기(초)
  BUCKY_MIN_FREE_GB=1.0            # 이 용량 미만이면 봇 미기동
  BUCKY_DISK_WAIT=60              # 디스크 부족 시 재점검 간격(초)
  BUCKY_TOKEN_RETRY=60           # 토큰 인증 실패 시 재시도 간격(초)
"""
from __future__ import annotations

import csv
import json
import os
import shutil
import socket
import subprocess
import sys
import time
import urllib.request
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BOT_SCRIPT = ROOT / "scripts" / "discord_bot.py"
SIGNAL_DIR = ROOT / "ObsidianVault" / "10_AgentBus" / "signals"
SIGNAL_FILE = SIGNAL_DIR / "bot_restart.signal"
PID_FILE = SIGNAL_DIR / "bucky_bot.pid"
SUPERVISOR_PID_FILE = SIGNAL_DIR / "bucky_bot_supervisor.pid"
LOG_FILE = ROOT / "discord_bot.log"
ERR_FILE = ROOT / "discord_bot.err"

_restart_count = 0


def load_env_file() -> None:
    env_path = ROOT / ".env"
    if not env_path.exists():
        return
    try:
        from dotenv import load_dotenv
        load_dotenv(env_path, encoding="utf-8-sig", override=True)
        return
    except ImportError:
        pass
    for raw_line in env_path.read_text(encoding="utf-8-sig", errors="replace").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        os.environ[name.strip()] = value.strip().strip('"').strip("'")


load_env_file()
POLL_SECONDS = int(os.getenv("BUCKY_SUPERVISOR_INTERVAL", "10"))
RESTART_DELAY_SECONDS = int(os.getenv("BUCKY_SUPERVISOR_RESTART_DELAY", "5"))
MIN_FREE_GB = float(os.getenv("BUCKY_MIN_FREE_GB", "1.0"))
DISK_WAIT_SECONDS = int(os.getenv("BUCKY_DISK_WAIT", "60"))
TOKEN_RETRY_SECONDS = int(os.getenv("BUCKY_TOKEN_RETRY", "60"))
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", "")


def now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def log(message: str) -> None:
    print(f"[Supervisor {now()}] {message}", flush=True)


def send_webhook(text: str) -> None:
    if not DISCORD_WEBHOOK_URL:
        return
    try:
        data = json.dumps({"content": text}).encode("utf-8")
        req = urllib.request.Request(
            DISCORD_WEBHOOK_URL,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        urllib.request.urlopen(req, timeout=8)
    except Exception as e:
        log(f"웹훅 전송 실패: {e}")


# ── 디스크 가드 ──────────────────────────────────────────────────────────────
def free_gb(path: Path) -> float:
    try:
        return shutil.disk_usage(str(path)).free / (1024 ** 3)
    except Exception as e:
        log(f"디스크 점검 실패: {e}")
        return 999.0


def ensure_disk() -> None:
    """여유 공간이 MIN_FREE_GB 이상이 될 때까지 대기 (부족 시 웹훅 1회 경고)."""
    alerted = False
    while True:
        fg = free_gb(ROOT)
        if fg >= MIN_FREE_GB:
            return
        if not alerted:
            send_webhook(
                f"🟥 **디스크 부족** {fg:.2f}GB < {MIN_FREE_GB}GB — 봇 미기동.\n"
                f"PC: `{socket.gethostname()}` | 공간 확보되면 자동 재개."
            )
            alerted = True
        log(f"디스크 부족 {fg:.2f}GB < {MIN_FREE_GB}GB — {DISK_WAIT_SECONDS}s 대기")
        time.sleep(DISK_WAIT_SECONDS)


def err_tail_has_auth_failure() -> bool:
    """discord_bot.err 끝부분에서 토큰 인증 실패(4004/LoginFailure) 흔적 확인."""
    try:
        with ERR_FILE.open("rb") as f:
            f.seek(0, os.SEEK_END)
            size = f.tell()
            f.seek(max(0, size - 4000))
            chunk = f.read().decode("utf-8", errors="replace").lower()
    except Exception:
        return False
    return ("4004" in chunk) or ("loginfailure" in chunk) or ("improper token" in chunk)


# ── PID/프로세스 유틸 ────────────────────────────────────────────────────────
def is_pid_running(pid: int) -> bool:
    if pid <= 0:
        return False
    if os.name == "nt":
        try:
            result = subprocess.run(
                ["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"],
                capture_output=True, text=True, encoding="utf-8",
                errors="replace", timeout=5,
            )
        except Exception:
            return False
        for row in csv.reader(result.stdout.splitlines()):
            if len(row) > 1 and row[1].strip() == str(pid):
                return True
        return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def process_command_line(pid: int) -> str:
    if pid <= 0 or os.name != "nt":
        return ""
    try:
        result = subprocess.run(
            ["powershell.exe", "-NoProfile", "-Command",
             f'(Get-CimInstance Win32_Process -Filter "ProcessId={pid}").CommandLine'],
            capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=8,
        )
        return result.stdout.strip()
    except Exception as exc:
        log(f"process_command_line({pid}) 실패: {exc}")
        return ""


def existing_child_is_running() -> bool:
    try:
        pid = int(PID_FILE.read_text(encoding="utf-8").strip())
    except Exception:
        return False
    if not is_pid_running(pid):
        return False
    return "discord_bot.py" in process_command_line(pid).replace("\\", "/")


def read_supervisor_pid():
    try:
        pid = int(SUPERVISOR_PID_FILE.read_text(encoding="utf-8").strip())
    except Exception:
        return None
    return pid if pid > 0 else None


def existing_supervisor_is_running() -> bool:
    pid = read_supervisor_pid()
    if not pid or pid == os.getpid():
        return False
    if is_pid_running(pid):
        cmd = process_command_line(pid).replace("\\", "/").lower()
        if "supervisor" in cmd and "discord_bot.py" not in cmd:
            return True
    try:
        SUPERVISOR_PID_FILE.unlink(missing_ok=True)
    except OSError:
        pass
    return False


def write_supervisor_pid() -> None:
    try:
        SIGNAL_DIR.mkdir(parents=True, exist_ok=True)
        SUPERVISOR_PID_FILE.write_text(str(os.getpid()), encoding="ascii")
    except OSError as exc:
        log(f"슈퍼바이저 PID 기록 실패: {exc}")


def remove_supervisor_pid() -> None:
    pid = read_supervisor_pid()
    if pid and pid != os.getpid():
        return
    try:
        SUPERVISOR_PID_FILE.unlink(missing_ok=True)
    except OSError:
        pass


def find_existing_bot_pids():
    self_pid = os.getpid()
    pids = []
    if os.name == "nt":
        try:
            result = subprocess.run(
                ["powershell.exe", "-NoProfile", "-Command",
                 "Get-CimInstance Win32_Process | "
                 "Where-Object { $_.CommandLine -like '*discord_bot.py*' } | "
                 "ForEach-Object { $_.ProcessId }"],
                capture_output=True, text=True, encoding="utf-8",
                errors="replace", timeout=10,
            )
            for line in result.stdout.splitlines():
                line = line.strip()
                if line.isdigit():
                    pid = int(line)
                    if pid and pid != self_pid:
                        pids.append(pid)
        except Exception as exc:
            log(f"find_existing_bot_pids 오류: {exc}")
    else:
        try:
            result = subprocess.run(["pgrep", "-f", "discord_bot.py"],
                                    capture_output=True, text=True, timeout=5)
            for line in result.stdout.splitlines():
                try:
                    pid = int(line.strip())
                    if pid != self_pid:
                        pids.append(pid)
                except ValueError:
                    pass
        except Exception as exc:
            log(f"find_existing_bot_pids 오류: {exc}")
    return pids


def kill_pid(pid: int) -> None:
    try:
        if os.name == "nt":
            subprocess.run(["taskkill", "/F", "/PID", str(pid)],
                           capture_output=True, timeout=5)
        else:
            import signal as _signal
            os.kill(pid, _signal.SIGTERM)
    except Exception as exc:
        log(f"kill_pid({pid}) 실패: {exc}")


def clear_restart_signal() -> None:
    try:
        SIGNAL_FILE.unlink(missing_ok=True)
    except OSError as exc:
        log(f"신호파일 제거 실패: {exc}")


def write_pid(pid: int) -> None:
    try:
        SIGNAL_DIR.mkdir(parents=True, exist_ok=True)
        PID_FILE.write_text(str(pid), encoding="ascii")
    except OSError as exc:
        log(f"봇 PID 기록 실패: {exc}")


def remove_pid() -> None:
    try:
        PID_FILE.unlink(missing_ok=True)
    except OSError:
        pass


def start_bot() -> subprocess.Popen:
    ensure_disk()  # ★ 디스크 가드: 공간 확보될 때까지 대기 후 기동
    SIGNAL_DIR.mkdir(parents=True, exist_ok=True)
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    stdout = LOG_FILE.open("a", encoding="utf-8", errors="replace")
    stderr = ERR_FILE.open("a", encoding="utf-8", errors="replace")
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    if os.name == "nt":
        path_value = env.get("PATH") or env.get("Path") or os.defpath
        for key in list(env):
            if key.lower() == "path":
                env.pop(key, None)
        env["PATH"] = path_value
    proc = subprocess.Popen(
        [sys.executable, str(BOT_SCRIPT)],
        cwd=str(ROOT), stdout=stdout, stderr=stderr,
        stdin=subprocess.DEVNULL, text=True, encoding="utf-8",
        errors="replace", env=env,
    )
    proc._bucky_stdout = stdout  # type: ignore[attr-defined]
    proc._bucky_stderr = stderr  # type: ignore[attr-defined]
    write_pid(proc.pid)
    log(f"discord_bot.py 시작 pid={proc.pid} (여유 {free_gb(ROOT):.1f}GB)")
    return proc


def close_bot_log_handles(proc) -> None:
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


def stop_bot(proc) -> None:
    if proc is None or proc.poll() is not None:
        close_bot_log_handles(proc)
        remove_pid()
        return
    log(f"discord_bot.py 종료 pid={proc.pid}")
    proc.terminate()
    try:
        proc.wait(timeout=15)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=10)
    close_bot_log_handles(proc)
    remove_pid()


def run() -> int:
    global _restart_count
    if existing_supervisor_is_running():
        log(f"이미 슈퍼바이저 실행 중 pid={read_supervisor_pid()} — 중복 실행 안 함")
        return 0
    write_supervisor_pid()

    send_webhook(f"🟢 **Bucky 슈퍼바이저 시작(보강판)** | PC: `{socket.gethostname()}`")
    log(f"슈퍼바이저 시작 on {socket.gethostname()} | 신호: {SIGNAL_FILE}")
    log(f"디스크 임계치: {MIN_FREE_GB}GB | 현재 여유: {free_gb(ROOT):.1f}GB")

    if existing_child_is_running():
        pid_str = PID_FILE.read_text(encoding="utf-8").strip()
        log(f"기존 봇 pid={pid_str} 종료 후 재기동")
        kill_pid(int(pid_str))
        time.sleep(2)
        remove_pid()

    orphans = find_existing_bot_pids()
    if orphans:
        log(f"고아 discord_bot.py 종료: {orphans}")
        for pid in orphans:
            kill_pid(pid)
        time.sleep(2)

    clear_restart_signal()
    proc = start_bot()
    token_alerted = False

    try:
        while True:
            time.sleep(POLL_SECONDS)

            # 원격/수동 재시작 신호
            if SIGNAL_FILE.exists():
                log("재시작 신호 감지")
                clear_restart_signal()
                stop_bot(proc)
                time.sleep(2)
                proc = start_bot()
                token_alerted = False
                continue

            # 봇이 죽었으면 사유 분류 후 재시작
            if proc.poll() is not None:
                exit_code = proc.returncode
                _restart_count += 1
                close_bot_log_handles(proc)
                remove_pid()

                auth_fail = err_tail_has_auth_failure()
                if auth_fail:
                    if not token_alerted:
                        send_webhook(
                            "🔑 **봇 토큰 인증 실패(4004)** — `.env`의 `DISCORD_BOT_TOKEN`을 "
                            "새로 재발급한 토큰으로 교체하세요. 교체되면 자동 복구됩니다.\n"
                            f"PC: `{socket.gethostname()}`"
                        )
                        token_alerted = True
                    delay = TOKEN_RETRY_SECONDS
                    log(f"봇 종료(exit={exit_code}) — 토큰 인증 실패 추정, {delay}s 후 재시도")
                else:
                    token_alerted = False
                    delay = RESTART_DELAY_SECONDS
                    send_webhook(
                        f"⚠️ **Bucky 봇 다운** (exit={exit_code}) | 재시작 #{_restart_count}\n"
                        f"PC: `{socket.gethostname()}` | {delay}s 후 자동 재시작..."
                    )
                    log(f"봇 종료(exit={exit_code}) — {delay}s 후 재시작 #{_restart_count}")

                time.sleep(delay)
                proc = start_bot()
                if not auth_fail:
                    send_webhook(f"✅ **Bucky 봇 재시작 완료** (PID {proc.pid}) | #{_restart_count}")
    except KeyboardInterrupt:
        log("슈퍼바이저 수동 종료")
        stop_bot(proc)
        send_webhook(f"🔴 **Bucky 슈퍼바이저 수동 종료** | PC: `{socket.gethostname()}`")
        remove_supervisor_pid()
        return 0


if __name__ == "__main__":
    raise SystemExit(run())
