#!/usr/bin/env python3
"""Charlie low-token audit for the Obsidian Brain System.

This script performs deterministic local checks only. It does not call an LLM,
does not modify source/runtime state, and does not commit or push.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any


try:
    import sys

    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
VAULT = ROOT / "ObsidianVault"
SYSTEM = VAULT / "00_System"
DOCS_DATA = ROOT / "docs" / "data"
DATA_DIR = ROOT / "data" / "charlie"
SINCE_DATE = "2026-06-05"

AUTHORITY_FILES = [
    ROOT / "AGENTS.md",
    ROOT / "CLAUDE.md",
    ROOT / "OPERATING_INTENT.md",
    SYSTEM / "USER_OPERATING_INTENT.md",
    SYSTEM / "BUCKY_CONTEXT.md",
    SYSTEM / "session-state.md",
    VAULT / "03_Projects" / "agents" / "charlie.md",
    VAULT / "03_Projects" / "agents" / "codex-instructions.md",
    VAULT / "03_Projects" / "agents" / "bucky.md",
]

RISK_KEYWORDS = {
    "shared-agent-degradation": [
        "멍청",
        "상위",
        "intent",
        "사용자 요구",
        "복원",
        "Charlie",
    ],
    "instruction-authority": [
        "AGENTS.md",
        "CLAUDE.md",
        "routing",
        "context",
        "Context",
        "지침",
        "라우팅",
        "three-tier",
    ],
    "dashboard": ["dashboard", "대시보드", "bucky-os", "bucky-agent-os", "PWA"],
    "discord-runtime": ["discord", "Discord", "봇", "gateway", "voice"],
    "daily-plus": ["daily-plus", "Daily Plus", "오늘", "pulse"],
    "authentication": ["auth", "login", "cookie", "password", "인증", "로그인"],
    "memory-context": ["memory", "Memory", "compaction", "skill", "SKILL"],
    "knowledge-loop": ["Daily Plus", "daily-plus", "Graphify", "LLM Wiki", "knowledge", "지식"],
    "core-purpose": ["efficient", "memory", "context", "feedback", "진화", "기억", "컨텍스트"],
    "session-continuity": ["session", "handoff", "context", "세션", "컨텍스트"],
    "workflow-expansion": ["wishket", "kmong", "collab", "workflow", "proposal"],
}


@dataclass
class Finding:
    severity: str
    area: str
    title: str
    detail: str
    evidence: str

    def to_dict(self) -> dict[str, str]:
        return {
            "severity": self.severity,
            "area": self.area,
            "title": self.title,
            "detail": self.detail,
            "evidence": self.evidence,
        }


def _run_git(args: list[str]) -> str:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=ROOT,
            text=True,
            encoding="utf-8",
            errors="replace",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
    except OSError as exc:
        return f"ERROR: {exc}"
    if result.returncode != 0:
        return f"ERROR: {result.stderr.strip()}"
    return result.stdout


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8-sig", errors="replace")
    except OSError:
        return ""


def _frontmatter_value(text: str, key: str) -> str:
    match = re.search(rf"^{re.escape(key)}:\s*(.+)$", text, flags=re.MULTILINE)
    return match.group(1).strip() if match else ""


def check_instruction_packet() -> list[Finding]:
    findings: list[Finding] = []
    required = [
        ("AGENTS.md", ROOT / "AGENTS.md"),
        ("CLAUDE.md", ROOT / "CLAUDE.md"),
        ("OPERATING_INTENT.md", ROOT / "OPERATING_INTENT.md"),
    ]
    for label, path in required:
        if not path.exists():
            findings.append(
                Finding(
                    "P2",
                    "project-instruction-packets",
                    f"Missing {label}",
                    "Project root cannot fully operate without a local instruction packet.",
                    str(path.relative_to(ROOT)),
                )
            )
    return findings


def check_authority_files() -> tuple[list[dict[str, Any]], list[Finding]]:
    files: list[dict[str, Any]] = []
    findings: list[Finding] = []
    now = time.time()
    for path in AUTHORITY_FILES:
        exists = path.exists()
        rel = str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path)
        mtime = path.stat().st_mtime if exists else 0
        text = _read_text(path) if exists and path.suffix.lower() == ".md" else ""
        updated = _frontmatter_value(text, "updated")
        files.append(
            {
                "path": rel,
                "exists": exists,
                "updated": updated,
                "mtime": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(mtime)) if exists else "",
                "age_days": round((now - mtime) / 86400, 1) if exists else None,
            }
        )
        if not exists:
            findings.append(
                Finding("P2", "authority", "Missing authority file", f"{rel} is absent.", rel)
            )
    return files, findings


def check_stale_markers() -> list[Finding]:
    findings: list[Finding] = []
    bucky_context = SYSTEM / "BUCKY_CONTEXT.md"
    session_state = SYSTEM / "session-state.md"
    context_text = _read_text(bucky_context)
    session_text = _read_text(session_state)

    if "PID 51220" in context_text:
        findings.append(
            Finding(
                "P2",
                "bucky-context",
                "Stale PID in Bucky context",
                "BUCKY_CONTEXT.md still references PID 51220.",
                "ObsidianVault/00_System/BUCKY_CONTEXT.md",
            )
        )
    if "2026-06-02 완료" in context_text:
        findings.append(
            Finding(
                "P2",
                "bucky-context",
                "Frozen 2026-06-02 snapshot remains",
                "BUCKY_CONTEXT.md still contains old completion snapshot language.",
                "ObsidianVault/00_System/BUCKY_CONTEXT.md",
            )
        )
    if "Gate 5 Discord Voice E2E | ⚠️ 사용자 직접 테스트 필요" in session_text:
        if "Gate 5 Discord Voice E2E | ✅ 완료" in context_text:
            findings.append(
                Finding(
                    "P2",
                    "agentbus",
                    "Gate 5 state mismatch",
                    "session-state.md requires user direct testing, but context marks Gate 5 complete.",
                    "session-state.md vs BUCKY_CONTEXT.md",
                )
            )
    if "현재 권위 소스는 `ObsidianVault/00_System/session-state.md`" not in context_text:
        findings.append(
            Finding(
                "P3",
                "bucky-context",
                "Bucky context lacks session-state pointer",
                "Section 9-1 should point to session-state.md and live runtime verification.",
                "ObsidianVault/00_System/BUCKY_CONTEXT.md",
            )
        )
    return findings


def check_shared_degradation_guard() -> list[Finding]:
    findings: list[Finding] = []
    intent_text = _read_text(SYSTEM / "USER_OPERATING_INTENT.md")
    charlie_text = _read_text(VAULT / "03_Projects" / "agents" / "charlie.md")
    if "Shared Degradation Rule" not in intent_text:
        findings.append(
            Finding(
                "P1",
                "shared-agent-degradation",
                "Missing shared degradation rule",
                "The system lacks an explicit guard for Bucky/Codex/Claude losing intent together.",
                "ObsidianVault/00_System/USER_OPERATING_INTENT.md",
            )
        )
    if "shared degradation" not in charlie_text.lower():
        findings.append(
            Finding(
                "P1",
                "shared-agent-degradation",
                "Charlie lacks shared degradation mission",
                "Charlie must explicitly watch for Bucky, Codex, and Claude Code degrading together.",
                "ObsidianVault/03_Projects/agents/charlie.md",
            )
        )
    return findings


def check_knowledge_loop_guard() -> list[Finding]:
    findings: list[Finding] = []
    intent_text = _read_text(SYSTEM / "USER_OPERATING_INTENT.md")
    required = ["Daily Plus", "LLM Wiki", "Graphify", "Context Packs", "targeted"]
    missing = [term for term in required if term not in intent_text]
    if missing:
        findings.append(
            Finding(
                "P2",
                "knowledge-loop",
                "Knowledge growth loop is not fully pinned",
                "USER_OPERATING_INTENT.md should preserve Daily Plus, LLM Wiki, Graphify, Context Packs, and targeted retrieval.",
                ", ".join(missing),
            )
        )
    return findings


def check_core_purpose_guard() -> list[Finding]:
    findings: list[Finding] = []
    intent_text = _read_text(SYSTEM / "USER_OPERATING_INTENT.md")
    required = [
        "Efficient AI use",
        "Stronger memory",
        "Efficient context management",
        "User feedback driven evolution",
    ]
    missing = [term for term in required if term not in intent_text]
    if missing:
        findings.append(
            Finding(
                "P1",
                "core-purpose",
                "Obsidian Brain System purpose is not pinned",
                "The system must preserve efficient AI use, memory, context efficiency, and user-feedback evolution.",
                ", ".join(missing),
            )
        )
    return findings


def check_session_continuity_guard() -> list[Finding]:
    findings: list[Finding] = []
    intent_text = _read_text(SYSTEM / "USER_OPERATING_INTENT.md")
    required = ["Session Continuity Rule", "handoff", "next session", "durable state"]
    missing = [term for term in required if term not in intent_text]
    if missing:
        findings.append(
            Finding(
                "P2",
                "session-continuity",
                "Session continuity rule is not fully pinned",
                "USER_OPERATING_INTENT.md should preserve session-end reasons, handoff, next-session reading order, and durable state.",
                ", ".join(missing),
            )
        )
    return findings


def check_turn_closure_guard() -> list[Finding]:
    findings: list[Finding] = []
    coordination_text = _read_text(SYSTEM / "CHARLIE_AGENT_COORDINATION.md")
    charlie_text = _read_text(VAULT / "03_Projects" / "agents" / "charlie.md")
    template_text = _read_text(SYSTEM / "CHARLIE_SESSION_HANDOFF_TEMPLATE.md")
    required = [
        ("Turn Closure Rule", coordination_text, "ObsidianVault/00_System/CHARLIE_AGENT_COORDINATION.md"),
        ("next work directive", coordination_text, "ObsidianVault/00_System/CHARLIE_AGENT_COORDINATION.md"),
        ("active request queue", charlie_text.lower(), "ObsidianVault/03_Projects/agents/charlie.md"),
        ("Active Request Queue", template_text, "ObsidianVault/00_System/CHARLIE_SESSION_HANDOFF_TEMPLATE.md"),
    ]
    missing = [f"{term} in {path}" for term, text, path in required if term not in text]
    if missing:
        findings.append(
            Finding(
                "P2",
                "turn-continuity",
                "Turn closure guard is not fully pinned",
                "Charlie/Codex must preserve requested follow-up work inside the same session before reporting completion.",
                "; ".join(missing),
            )
        )
    return findings


def check_expert_roster_guard() -> list[Finding]:
    findings: list[Finding] = []
    roster = SYSTEM / "CHARLIE_EXPERT_AGENT_ROSTER.md"
    coordination_text = _read_text(SYSTEM / "CHARLIE_AGENT_COORDINATION.md")
    roster_text = _read_text(roster)
    required_roles = [
        "Intent Auditor",
        "Worktree Classifier",
        "Knowledge Loop Auditor",
        "Runtime Evidence Auditor",
        "Permission Diagnostician",
        "Handoff Curator",
    ]
    missing_roles = [role for role in required_roles if role not in roster_text]
    if not roster.exists() or missing_roles or "CHARLIE_EXPERT_AGENT_ROSTER.md" not in coordination_text:
        findings.append(
            Finding(
                "P2",
                "specialist-routing",
                "Charlie specialist roster is not fully pinned",
                "Charlie needs a bounded expert-agent split for broad audit work so the main agent does not lose the active request queue.",
                ", ".join(missing_roles) if missing_roles else "roster reference missing",
            )
        )
    return findings


def check_hermes_level_guard() -> list[Finding]:
    findings: list[Finding] = []
    roadmap = SYSTEM / "CHARLIE_HERMES_LEVEL_ROADMAP.md"
    roadmap_text = _read_text(roadmap)
    required_terms = [
        "Hermes-Level Capabilities",
        "Pantheon graph",
        "Memory stack",
        "AI spend",
        "Mission control",
        "Dreaming function",
        "Agent health",
        "JH_CHARLIE_CHANNEL_ID",
    ]
    missing = [term for term in required_terms if term not in roadmap_text]
    if not roadmap.exists() or missing:
        findings.append(
            Finding(
                "P2",
                "hermes-level-charlie",
                "Charlie Hermes-level roadmap is not fully pinned",
                "Charlie needs a durable capability map comparable to the Hermes/Bucky benchmark without exceeding its audit role.",
                ", ".join(missing) if missing else str(roadmap.relative_to(ROOT)),
            )
        )
    return findings


def check_discord_charlie_channel_guard() -> list[Finding]:
    findings: list[Finding] = []
    discord_bot = _read_text(ROOT / "scripts" / "discord_bot.py")
    env_example = _read_text(ROOT / ".env.example")
    required = [
        ("JH_CHARLIE_CHANNEL_ID", discord_bot, "scripts/discord_bot.py"),
        ("jh-charlie", discord_bot, "scripts/discord_bot.py"),
        ("_uses_charlie_context", discord_bot, "scripts/discord_bot.py"),
        ("JH_CHARLIE_CHANNEL_ID", env_example, ".env.example"),
    ]
    missing = [f"{term} in {path}" for term, text, path in required if term not in text]
    if missing:
        findings.append(
            Finding(
                "P2",
                "discord-charlie-channel",
                "Discord Charlie channel is not fully configured",
                "Charlie needs a dedicated Discord channel for audit state, home PC continuity, and user confirmations.",
                "; ".join(missing),
            )
        )
    return findings


SECRET_ASSIGNMENT_RE = re.compile(
    r"""(?ix)
    ^\s*
    (?P<name>[A-Z0-9_]*(?:PASSWORD|SECRET|TOKEN|API_KEY|PRIVATE_KEY)[A-Z0-9_]*)
    \s*=\s*
    (?P<quote>['"])(?P<value>[^'"]{8,})(?P=quote)
    """
)

SECRET_ALLOWLIST_VALUES = {
    "changeme",
    "example",
    "placeholder",
    "your-secret-here",
    "your-password-here",
}


def check_hardcoded_secrets() -> list[Finding]:
    findings: list[Finding] = []
    scan_roots = [ROOT / "scripts"]
    scan_files: list[Path] = []
    for scan_root in scan_roots:
        if not scan_root.exists():
            continue
        scan_files.extend(
            path
            for path in scan_root.rglob("*.py")
            if ".git" not in path.parts and "__pycache__" not in path.parts
        )

    for path in sorted(scan_files):
        rel = str(path.relative_to(ROOT))
        for line_number, line in enumerate(_read_text(path).splitlines(), start=1):
            match = SECRET_ASSIGNMENT_RE.search(line)
            if not match:
                continue
            value = match.group("value").strip()
            if value.lower() in SECRET_ALLOWLIST_VALUES:
                continue
            findings.append(
                Finding(
                    "P1",
                    "secrets",
                    "Hardcoded secret-like value",
                    f"{match.group('name')} is assigned a literal value in source code.",
                    f"{rel}:{line_number}",
                )
            )
    return findings


def classify_commit(subject: str) -> list[str]:
    areas = []
    for area, keywords in RISK_KEYWORDS.items():
        if any(keyword.lower() in subject.lower() for keyword in keywords):
            areas.append(area)
    return areas or ["other"]


def collect_change_timeline() -> dict[str, Any]:
    output = _run_git(["log", f"--since={SINCE_DATE}", "--date=short", "--pretty=format:%ad\t%h\t%s"])
    commits: list[dict[str, Any]] = []
    by_area: dict[str, int] = {}
    by_date: dict[str, int] = {}
    if output.startswith("ERROR:"):
        return {"error": output, "commits": [], "by_area": {}, "by_date": {}}
    for line in output.splitlines():
        parts = line.split("\t", 2)
        if len(parts) != 3:
            continue
        date, commit, subject = parts
        areas = classify_commit(subject)
        for area in areas:
            by_area[area] = by_area.get(area, 0) + 1
        by_date[date] = by_date.get(date, 0) + 1
        commits.append({"date": date, "commit": commit, "subject": subject, "areas": areas})
    return {"commits": commits[:80], "by_area": by_area, "by_date": by_date, "total": len(commits)}


def collect_git_status() -> dict[str, Any]:
    output = _run_git(["status", "--short"])
    if output.startswith("ERROR:"):
        return {"error": output, "changed_count": 0, "sample": [], "by_area": {}, "by_area_files": {}}
    lines = [line for line in output.splitlines() if line.strip()]
    by_area: dict[str, int] = {}
    by_area_files: dict[str, list[str]] = {}
    for line in lines:
        path_text = line[3:].strip()
        area = classify_worktree_path(path_text)
        by_area[area] = by_area.get(area, 0) + 1
        by_area_files.setdefault(area, []).append(line)
    return {
        "changed_count": len(lines),
        "sample": lines[:40],
        "by_area": by_area,
        "by_area_files": by_area_files,
    }


def _file_state(path: Path) -> dict[str, Any]:
    exists = path.exists()
    state: dict[str, Any] = {
        "path": str(path.relative_to(ROOT)) if path.is_absolute() else str(path),
        "exists": exists,
    }
    if exists:
        stat = path.stat()
        state["mtime"] = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(stat.st_mtime))
        state["age_seconds"] = round(time.time() - stat.st_mtime, 1)
        state["size"] = stat.st_size
    return state


def _read_pid_file(path: Path) -> dict[str, Any]:
    state = _file_state(path)
    if not path.exists():
        state.update({"valid": False, "pid": None, "raw_preview": ""})
        return state
    raw = path.read_bytes()
    text = raw.decode("ascii", errors="ignore").strip().strip("\x00")
    if text.isdigit() and int(text) > 0:
        state.update({"valid": True, "pid": int(text), "raw_preview": text})
    else:
        preview = raw[:16].hex(" ")
        state.update({"valid": False, "pid": None, "raw_preview": preview})
    return state


def _process_ids_by_name() -> dict[str, Any]:
    if os.name != "nt":
        return {"available": False, "error": "process name check is implemented for Windows only", "python_pids": []}
    try:
        result = subprocess.run(
            [
                "powershell.exe",
                "-NoProfile",
                "-Command",
                "Get-Process -Name python -ErrorAction SilentlyContinue | "
                "Select-Object -ExpandProperty Id",
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=5,
        )
    except Exception as exc:
        return {"available": False, "error": str(exc), "python_pids": []}
    pids = [int(line.strip()) for line in result.stdout.splitlines() if line.strip().isdigit()]
    return {
        "available": result.returncode == 0,
        "error": result.stderr.strip(),
        "python_pids": pids,
    }


def _annotate_pid_process_matches(runtime_status: dict[str, Any]) -> dict[str, Any]:
    process_ids = runtime_status.get("process_ids", {})
    available = bool(process_ids.get("available"))
    running_pids = {int(pid) for pid in process_ids.get("python_pids", []) if isinstance(pid, int)}
    for key in ("bot_pid_file", "supervisor_pid_file"):
        pid_file = runtime_status.get(key, {})
        pid = pid_file.get("pid")
        if not pid_file.get("valid") or not pid:
            pid_file["process_match"] = False
        elif available:
            pid_file["process_match"] = int(pid) in running_pids
        else:
            pid_file["process_match"] = None
    return runtime_status


def _local_health(url: str = "http://127.0.0.1:8765/health") -> dict[str, Any]:
    try:
        with urllib.request.urlopen(url, timeout=1.5) as response:
            body = response.read(4000).decode("utf-8", errors="replace")
            return {"url": url, "ok": 200 <= response.status < 300, "status": response.status, "body": body}
    except (OSError, urllib.error.URLError) as exc:
        return {"url": url, "ok": False, "status": None, "error": str(exc)}


def _tail_markers(path: Path, markers: list[str]) -> dict[str, Any]:
    state = _file_state(path)
    if not path.exists():
        state["markers"] = {marker: False for marker in markers}
        return state
    text = path.read_text(encoding="utf-8", errors="replace")[-30000:]
    state["markers"] = {marker: marker in text for marker in markers}
    return state


def _daily_plus_bridge_state() -> dict[str, Any]:
    path = VAULT / "10_AgentBus" / "signals" / "daily_plus_discord_bridge.json"
    state = _file_state(path)
    sent_files: list[str] = []
    if path.exists():
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            sent_files = [str(item) for item in payload.get("sent_files", [])]
        except Exception as exc:
            state["error"] = str(exc)
    latest_sent = sorted(sent_files)[-1] if sent_files else ""
    outbox = VAULT / "10_AgentBus" / "outbox" / "Bucky"
    outbox_files = sorted(path.name for path in outbox.glob("*_090000_daily_plus_dashboard_bucky.md")) if outbox.exists() else []
    latest_outbox = outbox_files[-1] if outbox_files else ""
    state.update(
        {
            "sent_count": len(sent_files),
            "latest_sent": latest_sent,
            "latest_outbox": latest_outbox,
            "latest_outbox_sent": bool(latest_outbox and latest_outbox in sent_files),
        }
    )
    return state


def _daily_plus_dashboard_state() -> dict[str, Any]:
    path = ROOT / "docs" / "daily-plus.html"
    state = _file_state(path)
    if path.exists():
        text = path.read_text(encoding="utf-8", errors="replace")
        dates = re.findall(r"20\d{2}-\d{2}-\d{2}", text)
        state["latest_date"] = sorted(set(dates))[-1] if dates else ""
    return state


def collect_runtime_status() -> dict[str, Any]:
    runtime_status = {
        "bucky_health": _local_health(),
        "bot_pid_file": _read_pid_file(VAULT / "10_AgentBus" / "signals" / "bucky_bot.pid"),
        "supervisor_pid_file": _read_pid_file(VAULT / "10_AgentBus" / "signals" / "bucky_bot_supervisor.pid"),
        "process_ids": _process_ids_by_name(),
        "discord_log": _tail_markers(ROOT / "discord_bot.log", ["Bot ready", "Watching channels"]),
        "discord_err": _tail_markers(
            ROOT / "discord_bot.err",
            ["Bot ready", "IntakeConsumer", "DailyPlusBridge", "Traceback", "ERROR"],
        ),
        "daily_plus_bridge": _daily_plus_bridge_state(),
        "daily_plus_dashboard": _daily_plus_dashboard_state(),
    }
    return _annotate_pid_process_matches(runtime_status)


def check_runtime_findings(runtime_status: dict[str, Any]) -> list[Finding]:
    findings: list[Finding] = []
    health = runtime_status.get("bucky_health", {})
    pid_file = runtime_status.get("bot_pid_file", {})
    process_ids = runtime_status.get("process_ids", {})
    err_log = runtime_status.get("discord_err", {})
    bridge = runtime_status.get("daily_plus_bridge", {})
    dashboard = runtime_status.get("daily_plus_dashboard", {})

    if not health.get("ok"):
        findings.append(
            Finding(
                "P2",
                "discord-runtime",
                "Bucky local health endpoint is unavailable",
                "Charlie could not verify the local Bucky dashboard/API health endpoint.",
                str(health.get("error") or health.get("status") or health.get("url")),
            )
        )
    if pid_file.get("exists") and not pid_file.get("valid"):
        findings.append(
            Finding(
                "P2",
                "discord-runtime",
                "Bucky bot PID file is invalid",
                "The PID signal file exists but does not contain a usable process id.",
                f"{pid_file.get('path')}: {pid_file.get('raw_preview')}",
            )
        )
    if pid_file.get("valid") and pid_file.get("process_match") is False:
        findings.append(
            Finding(
                "P2",
                "discord-runtime",
                "Bucky bot PID does not match a running Python process",
                "The PID signal file points at a process id that is not currently visible in the Python process list.",
                f"pid={pid_file.get('pid')}; python_pids={process_ids.get('python_pids', [])}",
            )
        )
    if err_log.get("exists") and err_log.get("age_seconds", 0) > 3600 * 12:
        findings.append(
            Finding(
                "P2",
                "discord-runtime",
                "Discord bot runtime evidence is stale",
                "Recent runtime proof should come from current process, gateway, or channel evidence, not old logs.",
                f"{err_log.get('path')} mtime={err_log.get('mtime')}",
            )
        )
    if bridge.get("latest_outbox") and not bridge.get("latest_outbox_sent"):
        findings.append(
            Finding(
                "P2",
                "daily-plus",
                "Daily Plus bridge has unsent outbox files",
                "The latest Daily Plus Bucky outbox report has not been recorded in the Discord bridge state.",
                str(bridge.get("latest_outbox")),
            )
        )
    if not dashboard.get("latest_date"):
        findings.append(
            Finding(
                "P2",
                "daily-plus",
                "Daily Plus dashboard date was not detected",
                "Charlie could not extract a current date marker from docs/daily-plus.html.",
                str(dashboard.get("path")),
            )
        )
    return findings


def build_operational_checks(runtime_status: dict[str, Any]) -> list[dict[str, str]]:
    bot_pid = runtime_status.get("bot_pid_file", {})
    pid_valid = bool(bot_pid.get("valid"))
    pid_process_match = bot_pid.get("process_match") is True
    discord_markers = runtime_status.get("discord_err", {}).get("markers", {})
    bot_runtime_markers_ok = (
        bool(discord_markers.get("Bot ready"))
        and bool(discord_markers.get("IntakeConsumer"))
        and bool(discord_markers.get("DailyPlusBridge"))
        and not bool(discord_markers.get("Traceback"))
        and not bool(discord_markers.get("ERROR"))
    )
    discord_runtime_ok = pid_valid and pid_process_match and bot_runtime_markers_ok
    if discord_runtime_ok:
        live_runtime_evidence = "PID matches process; Bot ready; IntakeConsumer; DailyPlusBridge"
    elif bot_pid.get("process_match") is False:
        live_runtime_evidence = "PID file does not match a running Python process"
    else:
        live_runtime_evidence = "Discord bot runtime proof is incomplete"
    bridge = runtime_status.get("daily_plus_bridge", {})
    dashboard_html = _read_text(ROOT / "docs" / "charlie-system-audit.html")
    discord_bot = _read_text(ROOT / "scripts" / "discord_bot.py")
    charlie_audit = _read_text(ROOT / "scripts" / "charlie_audit.py")

    return [
        {
            "id": "discord_bucky_live",
            "label": "Discord Bucky agent live runtime",
            "status": "PASS" if discord_runtime_ok else "WARNING",
            "evidence": live_runtime_evidence,
            "next": "Send Discord ping only when user wants channel-level proof.",
        },
        {
            "id": "discord_channel_routes",
            "label": "Discord channel routing",
            "status": "USER_APPROVAL",
            "evidence": "JH channel IDs and intake route map are present in scripts/discord_bot.py",
            "next": "Send test messages/payloads per channel.",
        },
        {
            "id": "charlie_pc_status",
            "label": "Charlie conversation can check home PC status",
            "status": "WARNING" if "JH_CHARLIE_CHANNEL_ID" in discord_bot else "FAIL",
            "evidence": "Charlie channel context route exists" if "JH_CHARLIE_CHANNEL_ID" in discord_bot else "Charlie channel route missing",
            "next": "Verify in #jh-charlie with a live PC status request.",
        },
        {
            "id": "daily_plus_automation",
            "label": "Daily Plus automation and Discord bridge",
            "status": "PASS" if bridge.get("latest_outbox_sent") else "WARNING",
            "evidence": f"latest_outbox={bridge.get('latest_outbox')}; latest_sent={bridge.get('latest_sent')}",
            "next": "Observe the next scheduled run or approve a manual dry-run.",
        },
        {
            "id": "development_instruction_guard",
            "label": "Bucky development instruction guard",
            "status": "WARNING",
            "evidence": "development intake routes exist, but Charlie anomaly report loop still needs live proof",
            "next": "Send a harmless development test request and verify Charlie reports failures only.",
        },
        {
            "id": "charlie_dashboard_realtime",
            "label": "Charlie dashboard live refresh",
            "status": "PASS" if "setInterval(load" in dashboard_html else "FAIL",
            "evidence": "dashboard polls charlie_status.json" if "setInterval(load" in dashboard_html else "dashboard does not poll status JSON",
            "next": "Open local preview and watch generated_at update.",
        },
        {
            "id": "charlie_dashboard_detail",
            "label": "Charlie dashboard detailed user status",
            "status": "PASS" if "operationalChecks" in dashboard_html and "runtimeStatus" in dashboard_html else "FAIL",
            "evidence": "dashboard renders operational and runtime sections",
            "next": "Preview the dashboard visually.",
        },
        {
            "id": "pc_anomaly_reporting",
            "label": "PC anomaly detection and reporting",
            "status": "PASS" if "check_runtime_findings" in charlie_audit else "FAIL",
            "evidence": "Charlie audit converts runtime anomalies into findings",
            "next": "Wire high-priority findings to Discord report only if user wants active notifications.",
        },
        {
            "id": "charlie_exception_only",
            "label": "Charlie reports exceptions only",
            "status": "PASS",
            "evidence": "Charlie principle remains report-only and no auto-fix",
            "next": "No action.",
        },
    ]


def classify_worktree_path(path_text: str) -> str:
    normalized = path_text.replace("\\", "/").strip('"')
    if re.search(
        r"(^OPERATING_INTENT\.md$|ObsidianVault/00_System/(CHARLIE_|USER_OPERATING_INTENT|PROJECT_INSTRUCTION_REGISTRY)|"
        r"ObsidianVault/03_Projects/agents/charlie\.md|docs/charlie-system-audit\.html|"
        r"docs/superpowers/plans/2026-06-15-charlie-system-audit\.md|scripts/(charlie_audit|create_charlie_discord_channel)\.py)",
        normalized,
    ):
        return "charlie"
    if re.search(r"(Google-AdSense-OS|jh-google-revenue|jh_google_revenue|google_blog_adsense|test_jh_google_revenue)", normalized):
        return "google-revenue-dashboard"
    if re.search(r"(kmong|Kmong|test_kmong)", normalized):
        return "kmong"
    if re.search(
        r"(^\.gitignore$|ObsidianVault/\.obsidian/graph\.json|ObsidianVault/00_Dashboard/|"
        r"ObsidianVault/00_System/folder-registry\.md|ObsidianVault/03_Knowledge/|"
        r"ObsidianVault/09_Archive/)",
        normalized,
    ):
        return "knowledge-vault"
    if re.search(
        r"(scripts/(codex_session_handoff|daily_report_generator|gdrive_agent_room_migrator|gemini_client|"
        r"github_repo_cataloger|goal_tracker|graphify_hygiene_check|knowledge_bridge_builder|"
        r"legacy_residue_scanner|pc_identity|raw_import_watcher|send_bot_restart|stripe_payment_server|"
        r"vault_auto_tagger|yaml_validator|codex_preview_hook|prompt_logger)\.py)",
        normalized,
    ):
        return "support-tooling"
    if re.search(r"(^G1-preflight-dirty\.patch$|^Api .+\.txt$)", normalized):
        return "local-review-artifact"
    if re.search(
        r"(daily-plus|daily_plus|Bucky|BUCKY|bucky|discord|Discord|intake_channel|start_discord|"
        r"chatgpt_daily|claude_session_collector|collection_scheduler|run_daily_plus|screen-control|"
        r"task-board|checklist|app-session|wishket|user_checklist|agent_dispatcher|agent_health_monitor|"
        r"codex_request|codex_review_runner|harness_router|preflight_check|task_queue|task_tracker|"
        r"validation_council|start_discord_bot|tests/test_daily_plus_channel_bridge|"
        r"tests/test_dashboard_intake_payloads|tests/test_intake_channel_allowed|\.env\.example|AGENTS\.md|"
        r"package\.json|docs/index\.html)",
        normalized,
    ):
        return "bucky-discord-daily-plus"
    if re.search(r"(^\.gpt_collector_profile/|^\.playwright-mcp/|data/intake_queue/failed/|\.png$)", normalized):
        return "local-runtime-artifact"
    return "other"


def load_registry_summary() -> dict[str, Any]:
    paths = {
        "error_registry": SYSTEM / "CHARLIE_ERROR_REGISTRY.md",
        "change_log": SYSTEM / "CHARLIE_CHANGE_LOG.md",
        "instruction_registry": SYSTEM / "PROJECT_INSTRUCTION_REGISTRY.md",
    }
    return {
        name: {
            "path": str(path.relative_to(ROOT)),
            "exists": path.exists(),
            "mtime": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(path.stat().st_mtime))
            if path.exists()
            else "",
        }
        for name, path in paths.items()
    }


def build_status() -> dict[str, Any]:
    findings: list[Finding] = []
    authority_files, authority_findings = check_authority_files()
    findings.extend(authority_findings)
    findings.extend(check_instruction_packet())
    findings.extend(check_stale_markers())
    findings.extend(check_shared_degradation_guard())
    findings.extend(check_knowledge_loop_guard())
    findings.extend(check_core_purpose_guard())
    findings.extend(check_session_continuity_guard())
    findings.extend(check_turn_closure_guard())
    findings.extend(check_expert_roster_guard())
    findings.extend(check_hermes_level_guard())
    findings.extend(check_discord_charlie_channel_guard())
    findings.extend(check_hardcoded_secrets())
    runtime_status = collect_runtime_status()
    findings.extend(check_runtime_findings(runtime_status))
    operational_checks = build_operational_checks(runtime_status)

    change_timeline = collect_change_timeline()
    git_status = collect_git_status()
    if git_status.get("changed_count", 0) > 50:
        area_summary = ", ".join(
            f"{area}={count}" for area, count in sorted(git_status.get("by_area", {}).items())
        )
        findings.append(
            Finding(
                "P2",
                "worktree",
                "Large dirty worktree",
                f"Many changed/untracked files are present. Charlie should treat restore planning carefully. Areas: {area_summary}",
                "git status --short",
            )
        )

    p1 = sum(1 for f in findings if f.severity == "P1")
    p2 = sum(1 for f in findings if f.severity == "P2")
    p3 = sum(1 for f in findings if f.severity == "P3")
    state = "FAIL" if p1 else "WARNING" if p2 or p3 else "PASS"

    return {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "agent": "Charlie",
        "state": state,
        "principle": "Low-token deterministic audit. Charlie reports drift and does not auto-fix.",
        "summary": {"p1": p1, "p2": p2, "p3": p3, "findings": len(findings)},
        "user_intent": {
            "top_level_goal": (
                "Restore and stabilize the Obsidian Brain System after the post-2026-06-05 drift "
                "period, then maintain it for growth, expansion, upgrades, evolution, and improvement."
            ),
            "core_purpose": (
                "Efficient AI use, stronger memory, efficient context management, and user feedback "
                "driven evolution through Daily Plus, GPT conversations, Obsidian, LLM Wiki, Graphify, and Context Packs."
            ),
            "critical_failure_mode": (
                "Bucky, Codex, and Claude Code all become less capable together because local instructions, "
                "Bucky context, and user intent drift out of alignment."
            ),
            "knowledge_loop": (
                "Daily Plus and GPT conversations strengthen the Obsidian library; LLM Wiki, Graphify, "
                "and Context Packs should route targeted knowledge instead of broad context loading."
            ),
            "session_continuity": (
                "When context bloat risks losing user feedback, agents must create a concise handoff "
                "with session-end reason, durable files, next-session reading order, and do-not-repeat rules."
            ),
            "bucky_role": "work operations orchestrator",
            "charlie_role": "independent system audit agent",
        },
        "findings": [finding.to_dict() for finding in findings],
        "authority_files": authority_files,
        "change_timeline": change_timeline,
        "git_status": git_status,
        "runtime_status": runtime_status,
        "operational_checks": operational_checks,
        "registries": load_registry_summary(),
    }


def write_status(status: dict[str, Any]) -> tuple[list[str], list[str]]:
    written: list[str] = []
    errors: list[str] = []
    for directory in [DATA_DIR, DOCS_DATA]:
        try:
            directory.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            errors.append(f"{directory}: mkdir failed: {exc}")
    targets = [
        DATA_DIR / "charlie_status.json",
        DOCS_DATA / "charlie_status.json",
    ]
    payload = json.dumps(status, ensure_ascii=False, indent=2)
    for target in targets:
        try:
            target.write_text(payload + "\n", encoding="utf-8")
            written.append(str(target.relative_to(ROOT)))
        except OSError as exc:
            errors.append(f"{target.relative_to(ROOT)}: write failed: {exc}")
    return written, errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Charlie deterministic system audit.")
    parser.add_argument("--json", action="store_true", help="Print JSON status to stdout.")
    parser.add_argument("--no-write", action="store_true", help="Do not write status files.")
    args = parser.parse_args()

    status = build_status()
    if not args.no_write:
        written_files, write_errors = write_status(status)
        status["written_files"] = written_files
        status["write_errors"] = write_errors
        if write_errors:
            status["findings"].append(
                Finding(
                    "P2",
                    "filesystem",
                    "Charlie status write was partially blocked",
                    "Google Drive or local filesystem permissions blocked one or more status outputs.",
                    "; ".join(write_errors),
                ).to_dict()
            )
            status["summary"]["p2"] = int(status["summary"].get("p2", 0)) + 1
            status["summary"]["findings"] = int(status["summary"].get("findings", 0)) + 1
            if status["state"] == "PASS":
                status["state"] = "WARNING"
    if args.json:
        print(json.dumps(status, ensure_ascii=False, indent=2))
    else:
        print(f"CHARLIE_STATE={status['state']}")
        print(f"CHARLIE_FINDINGS={status['summary']['findings']}")
        for path in status.get("written_files", []):
            print(f"CHARLIE_STATUS_FILE={path}")
        for error in status.get("write_errors", []):
            print(f"CHARLIE_WRITE_WARNING={error}")
    return 0 if status["state"] != "FAIL" else 2


if __name__ == "__main__":
    raise SystemExit(main())
