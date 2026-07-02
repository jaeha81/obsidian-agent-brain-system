"""
charlie_audit.py
─────────────────
Deterministic, read-only system audit for the Obsidian Agent Brain System (Bucky OS).

Charlie is an independent audit layer (see ObsidianVault/03_Projects/agents/charlie.md).
This script never modifies code, instructions, runtime state, or git — it only reads and
writes its own JSON output.

Output: data/charlie/charlie_status.json, docs/data/charlie_status.json
Usage:  python scripts/charlie_audit.py [--since YYYY-MM-DD] [--json]
"""

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VAULT = ROOT / "ObsidianVault"
SYSTEM = VAULT / "00_System"
DEFAULT_SINCE = "2026-06-05"

GIT_CANDIDATES = ["git", r"C:\Program Files\Git\cmd\git.exe", r"C:\Program Files\Git\bin\git.exe"]


# ──────────────────────────────────────────
# git helpers (read-only: log/status only)
# ──────────────────────────────────────────
def _find_git():
    for candidate in GIT_CANDIDATES:
        try:
            subprocess.run([candidate, "--version"], capture_output=True, check=True, timeout=5)
            return candidate
        except Exception:
            continue
    return None


_GIT = _find_git()


def run_git(args):
    if not _GIT:
        return 1, ""
    try:
        result = subprocess.run(
            [_GIT, "-C", str(ROOT)] + args,
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30,
        )
        return result.returncode, (result.stdout + result.stderr)
    except Exception as exc:
        return 1, str(exc)


# ──────────────────────────────────────────
# area classification (mirrors docs/charlie-system-audit.html areaLabel())
# ──────────────────────────────────────────
AREA_RULES = [
    (r"^scripts/(discord_bot|bucky_briefing|bucky_client|bucky_dispatcher|bucky_multi_dispatcher"
     r"|sync_system_enhance|channel_task_tracker|task_tracker|daily_plus_morning_report"
     r"|backfill_daily_plus|chatgpt_daily_collector|daily_report_generator"
     r"|generate_daily_plus_dashboard)", "bucky-discord-daily-plus"),
    (r"^scripts/(preflight_check|bucky_os_gate|bucky_recovery_handler|charlie_audit)", "support-tooling"),
    (r"charlie", "charlie"),
    (r"^ObsidianVault/", "knowledge-vault"),
    (r"google-revenue|jh-google-revenue", "google-revenue-dashboard"),
    (r"kmong", "kmong"),
    (r"^docs/|^api/|^vercel\.json$", "dashboard"),
    (r"login|logout|protected|auth", "authentication"),
    (r"daily-plus|daily_plus", "daily-plus"),
    (r"^\.claude/", "discord-runtime"),
    (r"^scripts/", "workflow-expansion"),
    (r"CLAUDE\.md|AGENTS\.md|OPERATING_INTENT|USER_OPERATING_INTENT", "instruction-authority"),
]


def classify_area(path):
    for pattern, area in AREA_RULES:
        if re.search(pattern, path, re.IGNORECASE):
            return area
    return "other"


# ──────────────────────────────────────────
# checks
# ──────────────────────────────────────────
AUTHORITY_FILES = [
    "AGENTS.md",
    "CLAUDE.md",
    "OPERATING_INTENT.md",
    "ObsidianVault/00_System/USER_OPERATING_INTENT.md",
    "ObsidianVault/03_Projects/agents/charlie.md",
]

REGISTRIES = {
    "error_registry": "ObsidianVault/00_System/CHARLIE_ERROR_REGISTRY.md",
    "change_log": "ObsidianVault/00_System/CHARLIE_CHANGE_LOG.md",
    "instruction_registry": "ObsidianVault/00_System/PROJECT_INSTRUCTION_REGISTRY.md",
}

STALE_DAYS_WARN = 30


def _mtime_str(path):
    return datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M")


def check_authority_files():
    out = []
    for rel in AUTHORITY_FILES:
        p = ROOT / rel
        exists = p.exists()
        out.append({"path": rel, "exists": exists, "updated": _mtime_str(p) if exists else ""})
    return out


def check_registries():
    out = {}
    for key, rel in REGISTRIES.items():
        p = ROOT / rel
        exists = p.exists()
        out[key] = {"path": rel, "exists": exists, "mtime": _mtime_str(p) if exists else ""}
    return out


def check_git_status():
    rc, out = run_git(["status", "--short"])
    if rc != 0:
        return {"changed_count": 0, "by_area": {}}, []
    lines = [line for line in out.splitlines() if line.strip()]
    by_area = {}
    for line in lines:
        path = line[3:].strip().strip('"')
        area = classify_area(path)
        by_area[area] = by_area.get(area, 0) + 1
    return {"changed_count": len(lines), "by_area": by_area}, lines


def git_log_summary(since):
    rc, out = run_git(["log", f"--since={since}", "--pretty=format:%x01%h|%ad|%s", "--date=short", "--name-only"])
    if rc != 0:
        return []
    commits = []
    current = None
    for line in out.split("\x01"):
        if not line.strip():
            continue
        header, _, files = line.partition("\n")
        parts = header.split("|", 2)
        if len(parts) != 3:
            continue
        commit_hash, commit_date, subject = parts
        areas = set()
        for f in files.splitlines():
            f = f.strip()
            if f:
                areas.add(classify_area(f))
        commits.append({
            "commit": commit_hash,
            "date": commit_date,
            "subject": subject,
            "areas": sorted(areas) if areas else ["other"],
        })
    return commits


def by_area_counts(commits):
    counts = {}
    for c in commits:
        for a in c["areas"]:
            counts[a] = counts.get(a, 0) + 1
    return counts


def check_bot_pid():
    pid_file = ROOT / "logs" / "discord_bot.pid"
    if not pid_file.exists():
        return {"valid": False, "raw_preview": "missing"}
    raw = pid_file.read_text(encoding="utf-8", errors="replace").strip()
    try:
        pid = int(raw)
    except ValueError:
        return {"valid": False, "raw_preview": raw[:40]}
    alive = _pid_alive(pid)
    return {"valid": alive, "pid": pid, "raw_preview": raw[:40] if not alive else None}


def _pid_alive(pid):
    if sys.platform != "win32":
        try:
            import os as _os
            _os.kill(pid, 0)
            return True
        except Exception:
            return False
    try:
        result = subprocess.run(
            ["tasklist", "/fi", f"PID eq {pid}", "/fo", "csv"],
            capture_output=True, text=True, timeout=10,
        )
        return str(pid) in result.stdout
    except Exception:
        return False


def check_python_processes():
    if sys.platform != "win32":
        return {"python_pids": [], "error": "process listing only implemented for win32"}
    try:
        result = subprocess.run(
            ["tasklist", "/fi", "imagename eq python.exe", "/fo", "csv"],
            capture_output=True, text=True, timeout=10,
        )
        pids = re.findall(r'"python\.exe","(\d+)"', result.stdout)
        return {"python_pids": pids}
    except Exception as exc:
        return {"python_pids": [], "error": str(exc)}


def check_daily_plus_bridge():
    outbox_dir = VAULT / "10_AgentBus" / "outbox" / "Bucky"
    if not outbox_dir.exists():
        return {"latest_outbox": "", "latest_sent": ""}
    files = sorted(outbox_dir.glob("*daily_plus_dashboard_bucky.md"), key=lambda p: p.stat().st_mtime, reverse=True)
    latest = files[0] if files else None
    return {
        "latest_outbox": latest.name if latest else "",
        "latest_sent": _mtime_str(latest) if latest else "",
    }


def check_daily_plus_dashboard():
    page = ROOT / "docs" / "daily-plus" / "index.html"
    if not page.exists():
        page = ROOT / "docs" / "daily-plus.html"
    if not page.exists():
        return {"latest_date": "", "mtime": ""}
    return {"latest_date": datetime.fromtimestamp(page.stat().st_mtime).strftime("%Y-%m-%d"), "mtime": _mtime_str(page)}


def check_env_file():
    env = ROOT / ".env"
    return {"ok": env.exists(), "error": None if env.exists() else ".env missing — bot cannot start"}


# ──────────────────────────────────────────
# findings (deterministic rules only)
# ──────────────────────────────────────────
def build_findings(authority_files, registries, git_status, bot_pid, env_check):
    findings = []

    for f in authority_files:
        if not f["exists"]:
            findings.append({
                "severity": "P2",
                "area": "instruction-authority",
                "title": f"Missing authority file: {f['path']}",
                "detail": "Charlie expects this file to exist as an instruction-authority source.",
                "evidence": f"authority_files:{f['path']}",
            })

    for key, r in registries.items():
        if not r["exists"]:
            findings.append({
                "severity": "P2",
                "area": "charlie",
                "title": f"Missing registry: {key}",
                "detail": f"Expected at {r['path']}.",
                "evidence": f"registries:{key}",
            })

    if git_status["changed_count"] > 80:
        findings.append({
            "severity": "P2",
            "area": "worktree",
            "title": "Large dirty worktree",
            "detail": f"{git_status['changed_count']} changed/untracked paths. See git_status.by_area.",
            "evidence": "git_status.by_area",
        })

    if not bot_pid.get("valid"):
        findings.append({
            "severity": "P3",
            "area": "discord-runtime",
            "title": "Discord bot PID file missing or stale",
            "detail": "logs/discord_bot.pid does not point at a live process — the bot may not "
                       "be running, or it was started without writing the PID file.",
            "evidence": "runtime_status.bot_pid_file",
        })

    if not env_check.get("ok"):
        findings.append({
            "severity": "P1",
            "area": "discord-runtime",
            "title": ".env missing",
            "detail": "No .env file — the Discord bot and other runtime scripts cannot start.",
            "evidence": "runtime_status.bucky_health",
        })

    return findings


def severity_summary(findings):
    counts = {"p1": 0, "p2": 0, "p3": 0}
    for f in findings:
        key = f["severity"].lower()
        if key in counts:
            counts[key] += 1
    counts["findings"] = len(findings)
    return counts


def overall_state(summary):
    if summary["p1"] > 0:
        return "FAIL"
    if summary["p2"] > 0:
        return "WARNING"
    return "PASS"


# ──────────────────────────────────────────
# main
# ──────────────────────────────────────────
def run(since):
    authority_files = check_authority_files()
    registries = check_registries()
    git_status, _dirty_lines = check_git_status()
    commits = git_log_summary(since)
    change_timeline = {"commits": commits[:50], "by_area": by_area_counts(commits)}

    bot_pid = check_bot_pid()
    runtime_status = {
        "bucky_health": {"ok": False, "error": "no local health endpoint configured"},
        "bot_pid_file": bot_pid,
        "supervisor_pid_file": {"valid": False, "raw_preview": "not configured"},
        "process_ids": check_python_processes(),
        "discord_log": {"mtime": "", "markers": {"Bot ready": False}},
        "daily_plus_bridge": check_daily_plus_bridge(),
        "daily_plus_dashboard": check_daily_plus_dashboard(),
    }

    env_check = check_env_file()
    runtime_status["bucky_health"] = env_check if not env_check["ok"] else {"ok": True, "error": None}

    findings = build_findings(authority_files, registries, git_status, bot_pid, env_check)
    summary = severity_summary(findings)
    state = overall_state(summary)

    operational_checks = [
        {
            "id": "charlie-dashboard-access",
            "label": "대시보드 접속 비밀번호",
            "status": "USER_APPROVAL",
            "evidence": "정적 HTML 내부 비밀번호 게이트 적용",
            "next": "공개 배포 후 모바일에서 비밀번호 입력 확인",
        },
        {
            "id": "charlie-no-autofix",
            "label": "Charlie는 자동 수정하지 않음",
            "status": "PASS",
            "evidence": "scripts/charlie_audit.py는 git add/commit/push를 호출하지 않음",
            "next": "발견사항은 사용자 승인 후 별도로 수정",
        },
    ]

    return {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "agent": "Charlie",
        "state": state,
        "principle": "Charlie는 독립 시스템 감사 계층입니다. 운영 이상을 보고하지만 "
                      "사용자 승인 없이 자동 수정하지 않습니다.",
        "summary": summary,
        "user_intent": {
            "top_level_goal": "2026-06-05 이후 드리프트를 복구하고 Obsidian Brain System을 "
                               "안정화한 뒤, GPU 작업은 로컬에 남기고 Oracle Cloud로 24/7 이전합니다.",
            "core_purpose": "효율적인 AI 사용, 강한 세션 기억, 효율적인 컨텍스트 관리, "
                             "사용자 피드백 기반 진화.",
            "critical_failure_mode": "Bucky, Codex, Claude Code가 함께 덜 유용해지는 공유 성능 저하.",
            "knowledge_loop": "Daily Plus와 GPT 대화가 Obsidian 지식 라이브러리를 강화하고, "
                               "LLM Wiki, Graphify, Context Packs가 필요한 지식만 찾아 연결합니다.",
            "session_continuity": "컨텍스트가 비대해지면 변경점, 보존 파일, 다음 세션 읽기 순서, "
                                    "반복 금지 항목을 남깁니다.",
            "bucky_role": "작업 운영 조율자",
            "charlie_role": "독립 시스템 감사자",
        },
        "findings": findings,
        "authority_files": authority_files,
        "change_timeline": change_timeline,
        "git_status": git_status,
        "runtime_status": runtime_status,
        "operational_checks": operational_checks,
        "registries": registries,
    }


def write_outputs(status):
    local_path = ROOT / "data" / "charlie" / "charlie_status.json"
    dashboard_path = ROOT / "docs" / "data" / "charlie_status.json"
    payload = json.dumps(status, ensure_ascii=False, indent=2)
    for path in (local_path, dashboard_path):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(payload + "\n", encoding="utf-8")
    return local_path, dashboard_path


def main():
    parser = argparse.ArgumentParser(description="Charlie: independent, read-only system audit.")
    parser.add_argument("--since", default=DEFAULT_SINCE, help="git log --since date (default: %(default)s)")
    parser.add_argument("--json", action="store_true", help="print the full JSON to stdout")
    args = parser.parse_args()

    status = run(args.since)
    local_path, dashboard_path = write_outputs(status)

    if args.json:
        print(json.dumps(status, ensure_ascii=False, indent=2))
    else:
        print(f"charlie_audit: state={status['state']} "
              f"p1={status['summary']['p1']} p2={status['summary']['p2']} p3={status['summary']['p3']} "
              f"dirty={status['git_status']['changed_count']}")
        for f in status["findings"]:
            print(f"  [{f['severity']}] {f['area']}: {f['title']}")
        print(f"wrote: {local_path}")
        print(f"wrote: {dashboard_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
