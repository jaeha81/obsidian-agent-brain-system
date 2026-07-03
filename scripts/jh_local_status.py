#!/usr/bin/env python3
"""Read-only local PC status report for the jh-local Discord channel."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Callable


ROOT = Path(__file__).resolve().parent.parent
PID_FILE = ROOT / "logs" / "discord_bot.pid"
PIPELINE_TASK_NAME = "BuckyDailyPlusPipeline"
CommandRunner = Callable[[list[str]], tuple[int, str]]


def run_command(args: list[str], timeout: int = 10) -> tuple[int, str]:
    try:
        result = subprocess.run(
            args,
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
        return result.returncode, (result.stdout + result.stderr).strip()
    except Exception as exc:
        return 1, str(exc)


def cpu_load_percent(command_runner: CommandRunner = run_command) -> str:
    code, output = command_runner([
        "powershell", "-NoProfile", "-Command",
        "(Get-CimInstance Win32_Processor | Measure-Object -Property LoadPercentage -Average).Average",
    ])
    return f"{output.strip()}%" if code == 0 and output.strip() else "unknown"


def disk_usage(path: Path) -> dict:
    try:
        usage = shutil.disk_usage(path)
    except OSError:
        return {"path": str(path), "error": "unavailable"}
    total_gb = usage.total / (1024 ** 3)
    free_gb = usage.free / (1024 ** 3)
    return {
        "path": str(path),
        "total_gb": round(total_gb, 1),
        "free_gb": round(free_gb, 1),
        "percent_used": round((usage.total - usage.free) / usage.total * 100, 1),
    }


def bot_process_alive(pid_file: Path = PID_FILE, command_runner: CommandRunner = run_command) -> bool:
    try:
        pid = int(pid_file.read_text().strip())
    except (OSError, ValueError):
        return False
    code, output = command_runner(["tasklist", "/FI", f"PID eq {pid}", "/NH", "/FO", "CSV"])
    return code == 0 and f'"{pid}"' in output


def _parse_dotnet_date(value: str) -> str:
    """schtasks JSON은 /Date(ms)/ 형식(WCF)을 쓴다 — 로케일 무관 epoch ms 파싱."""
    match = re.search(r"\d+", value or "")
    if not match:
        return "unknown"
    return datetime.fromtimestamp(int(match.group()) / 1000).strftime("%Y-%m-%d %H:%M")


def pipeline_status(task_name: str = PIPELINE_TASK_NAME, command_runner: CommandRunner = run_command) -> dict:
    code, output = command_runner([
        "powershell", "-NoProfile", "-Command",
        f"Get-ScheduledTaskInfo -TaskName '{task_name}' "
        "| Select-Object LastRunTime,LastTaskResult,NextRunTime "
        "| ConvertTo-Json -Compress",
    ])
    if code != 0 or not output.strip():
        return {"task": task_name, "status": "not_found"}
    try:
        info = json.loads(output)
    except json.JSONDecodeError:
        return {"task": task_name, "status": "parse_error"}
    return {
        "task": task_name,
        "last_run": _parse_dotnet_date(info.get("LastRunTime", "")),
        "last_result": info.get("LastTaskResult"),
        "next_run": _parse_dotnet_date(info.get("NextRunTime", "")),
    }


def git_ahead_behind(command_runner: CommandRunner = run_command) -> dict:
    """origin 대비 ahead/behind — 로컬에 이미 있는 원격 추적 정보만 사용, fetch 없음(read-only)."""
    branch_code, branch = command_runner(["git", "rev-parse", "--abbrev-ref", "HEAD"])
    branch = branch.strip() if branch_code == 0 and branch.strip() else "unknown"
    code, counts = command_runner(
        ["git", "rev-list", "--left-right", "--count", f"origin/{branch}...{branch}"]
    )
    if code != 0 or not counts.strip():
        return {"branch": branch, "ahead": "?", "behind": "?"}
    parts = counts.split()
    behind, ahead = (parts + ["?", "?"])[:2]
    return {"branch": branch, "ahead": ahead, "behind": behind}


def build_report(*, command_runner: CommandRunner = run_command) -> dict:
    drives = {Path(ROOT.anchor)}
    g_drive = Path("G:/")
    if g_drive.exists():
        drives.add(g_drive)
    return {
        "cpu_load": cpu_load_percent(command_runner),
        "disks": [disk_usage(d) for d in sorted(drives, key=str)],
        "discord_bot_alive": bot_process_alive(command_runner=command_runner),
        "daily_plus_pipeline": pipeline_status(command_runner=command_runner),
        "git": git_ahead_behind(command_runner),
    }


def format_text(report: dict) -> str:
    lines = ["[jh-local PC 상태]", f"CPU 사용률: {report['cpu_load']}"]
    for d in report["disks"]:
        if "error" in d:
            lines.append(f"디스크 {d['path']}: 조회 불가")
        else:
            lines.append(
                f"디스크 {d['path']}: {d['free_gb']}GB 여유 / {d['total_gb']}GB "
                f"(사용률 {d['percent_used']}%)"
            )
    bot_state = "실행 중" if report["discord_bot_alive"] else "중지됨"
    lines.append(f"Discord 봇 프로세스: {bot_state}")
    p = report["daily_plus_pipeline"]
    if p.get("status") in ("not_found", "parse_error"):
        lines.append(f"Daily Plus 파이프라인: 조회 실패 ({p['status']})")
    else:
        lines.append(
            f"Daily Plus 파이프라인: 마지막 실행 {p.get('last_run')} "
            f"(결과 코드 {p.get('last_result')}) / 다음 실행 {p.get('next_run')}"
        )
    g = report["git"]
    lines.append(f"Git ({g['branch']}): origin 대비 ahead {g['ahead']} / behind {g['behind']}")
    return "\n".join(lines)


def main() -> int:
    print(format_text(build_report()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
