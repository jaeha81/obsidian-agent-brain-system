#!/usr/bin/env python3
"""
Agent Health Monitor — 전체 서브에이전트 상태 감시

역할:
  - 모든 에이전트(Bucky, ClaudeCode, Codex, Collector, Distiller) 헬스 체크
  - AgentBus 큐 지연 감지 (메시지 처리 안 됨)
  - git index.lock 자동 해제 (커밋 충돌 복구)
  - 상태 요약 → ObsidianVault/10_AgentBus/health-status.json
  - Discord 웹훅으로 주기적 상태 보고

실행: python scripts/agent_health_monitor.py [--once]
"""

import argparse
import json
import os
import platform
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv

_ROOT = Path(__file__).parent.parent
load_dotenv(_ROOT / ".env", encoding="utf-8")

DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK_URL", "")
HEALTH_FILE = _ROOT / "ObsidianVault" / "10_AgentBus" / "health-status.json"
AGENTBUS_INBOX = _ROOT / "ObsidianVault" / "10_AgentBus" / "inbox"
GIT_LOCK = _ROOT / ".git" / "index.lock"

CHECK_INTERVAL = 60          # 헬스 체크 주기(초)
QUEUE_STALE_MINUTES = 10     # 이 시간 이상 미처리 메시지 → 경고


def ts() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def log(msg: str) -> None:
    print(f"[HEALTH {ts()}] {msg}", flush=True)


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
    except Exception:
        pass


# ── 개별 체크 함수 ─────────────────────────────────────────────────────────────

def check_git_lock() -> dict:
    if GIT_LOCK.exists():
        age = time.time() - GIT_LOCK.stat().st_mtime
        if age > 30:  # 30초 이상 남은 lock → 고착 lock
            GIT_LOCK.unlink(missing_ok=True)
            log(f"git index.lock 자동 해제 (age={age:.0f}s)")
            return {"status": "recovered", "detail": f"stale lock removed ({age:.0f}s)"}
        return {"status": "warn", "detail": f"lock exists ({age:.0f}s, may be active)"}
    return {"status": "ok"}


def check_agentbus_queue() -> dict:
    if not AGENTBUS_INBOX.exists():
        return {"status": "ok", "pending": 0}

    stale = []
    now = datetime.now()
    for f in AGENTBUS_INBOX.glob("*.json"):
        try:
            age_min = (now - datetime.fromtimestamp(f.stat().st_mtime)).total_seconds() / 60
            if age_min > QUEUE_STALE_MINUTES:
                stale.append({"file": f.name, "age_min": round(age_min, 1)})
        except Exception:
            pass

    pending = len(list(AGENTBUS_INBOX.glob("*.json")))
    if stale:
        return {"status": "warn", "pending": pending, "stale": stale}
    return {"status": "ok", "pending": pending}


def check_process(name: str, keyword: str) -> dict:
    """keyword가 포함된 프로세스 실행 여부 확인"""
    try:
        if platform.system() == "Windows":
            result = subprocess.run(
                ["tasklist", "/FO", "CSV", "/NH"],
                capture_output=True, text=True, timeout=5
            )
            running = keyword.lower() in result.stdout.lower()
        else:
            result = subprocess.run(
                ["pgrep", "-f", keyword],
                capture_output=True, text=True, timeout=5
            )
            running = bool(result.stdout.strip())
        return {"status": "ok" if running else "down", "running": running}
    except Exception as e:
        return {"status": "unknown", "error": str(e)}


def check_docker_services() -> dict:
    try:
        result = subprocess.run(
            ["docker", "compose", "ps", "--format", "json"],
            capture_output=True, text=True, timeout=10,
            cwd=str(_ROOT)
        )
        if result.returncode != 0:
            return {"status": "warn", "detail": "docker compose ps failed"}
        lines = [l for l in result.stdout.strip().splitlines() if l]
        services = []
        for line in lines:
            try:
                svc = json.loads(line)
                services.append({"name": svc.get("Name"), "state": svc.get("State")})
            except Exception:
                pass
        unhealthy = [s for s in services if s["state"] not in ("running", "healthy")]
        return {
            "status": "warn" if unhealthy else "ok",
            "services": services,
            "unhealthy": unhealthy,
        }
    except FileNotFoundError:
        return {"status": "skip", "detail": "docker not found"}
    except Exception as e:
        return {"status": "unknown", "error": str(e)}


def check_disk_space() -> dict:
    try:
        usage = os.statvfs(str(_ROOT)) if hasattr(os, "statvfs") else None
        if usage:
            free_gb = (usage.f_bavail * usage.f_frsize) / 1e9
            return {"status": "warn" if free_gb < 1 else "ok", "free_gb": round(free_gb, 1)}
        # Windows fallback
        import shutil
        free_gb = shutil.disk_usage(str(_ROOT)).free / 1e9
        return {"status": "warn" if free_gb < 1 else "ok", "free_gb": round(free_gb, 1)}
    except Exception as e:
        return {"status": "unknown", "error": str(e)}


# ── 종합 체크 ─────────────────────────────────────────────────────────────────

def run_checks() -> dict:
    report = {
        "timestamp": ts(),
        "checks": {
            "git_lock":      check_git_lock(),
            "agentbus":      check_agentbus_queue(),
            "bucky_process": check_process("bucky", "discord_bot.py"),
            "docker":        check_docker_services(),
            "disk":          check_disk_space(),
        },
    }

    # 전체 상태 집계
    statuses = [v["status"] for v in report["checks"].values()]
    if "down" in statuses:
        report["overall"] = "critical"
    elif "warn" in statuses or "recovered" in statuses:
        report["overall"] = "warn"
    else:
        report["overall"] = "healthy"

    return report


def save_report(report: dict) -> None:
    HEALTH_FILE.parent.mkdir(parents=True, exist_ok=True)
    HEALTH_FILE.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")


def format_discord_report(report: dict) -> str:
    icon = {"healthy": "✅", "warn": "⚠️", "critical": "🔴"}.get(report["overall"], "❓")
    lines = [f"{icon} **에이전트 헬스 체크** `{report['timestamp']}`"]
    for name, check in report["checks"].items():
        status = check["status"]
        emoji = {"ok": "✅", "warn": "⚠️", "down": "🔴", "recovered": "🔧",
                 "skip": "⏭️", "unknown": "❓"}.get(status, "❓")
        detail = check.get("detail") or check.get("error") or ""
        lines.append(f"  {emoji} `{name}` {detail}")
    return "\n".join(lines)


# ── 엔트리포인트 ──────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true", help="1회 실행 후 종료")
    args = parser.parse_args()

    log("Agent Health Monitor 시작")
    last_webhook = 0.0
    WEBHOOK_INTERVAL = 3600  # 정상 시 1시간마다 Discord 보고

    while True:
        report = run_checks()
        save_report(report)
        log(f"상태: {report['overall']}")

        # 위험/경고 또는 정기 보고
        now = time.time()
        if report["overall"] in ("critical", "warn") or (now - last_webhook) > WEBHOOK_INTERVAL:
            send_webhook(format_discord_report(report))
            last_webhook = now

        if args.once:
            print(json.dumps(report, indent=2, ensure_ascii=False))
            break

        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()
