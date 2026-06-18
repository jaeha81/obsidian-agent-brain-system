"""Build workflow dashboard data from docs/*/AGENT.md and runtime status files.

Outputs:
  - docs/workflow/agents.json   : parsed AGENT.md frontmatter + sections (per channel)
  - docs/workflow/health.json   : synthesized health snapshot for real-time error detection

Run:
  python -X utf8 scripts/build_workflow_data.py

The HTML dashboard (docs/workflow/index.html) fetches these two files and renders
the workflow graph + agent matrix + Bucky inheritance + real-time error icons.
"""
from __future__ import annotations

import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
WORKFLOW_DIR = DOCS / "workflow"
DATA_DIR = ROOT / "data"
DOCS_DATA = DOCS / "data"
LOGS = ROOT / "logs"

SECTION_RE = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)


def parse_agent_md(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    fm: dict = {}
    body = text
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end > 0:
            fm_block = text[3:end].strip()
            body = text[end + 4 :].lstrip("\n")
            for line in fm_block.splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    fm[k.strip()] = v.strip()

    sections: dict[str, str] = {}
    matches = list(SECTION_RE.finditer(body))
    for i, m in enumerate(matches):
        title = m.group(1).strip()
        start = m.end()
        stop = matches[i + 1].start() if i + 1 < len(matches) else len(body)
        sections[title] = body[start:stop].strip()

    def get(*keys: str) -> str:
        for k in keys:
            for sk in sections:
                if sk.lower().startswith(k.lower()):
                    return sections[sk]
        return ""

    role_text = get("Role")
    skills_text = get("Domain Skills", "Watch Scope", "Skills")
    scope_text = get("Scope")
    contract_text = get("Channel Contract")
    routing_text = get("Routing Rules")

    return {
        "slug": path.parent.name,
        "agent": fm.get("agent", path.parent.name),
        "channel": fm.get("channel", ""),
        "dashboard": fm.get("dashboard", "") or None,
        "bucky_inheritance": fm.get("bucky_inheritance", "false").lower() == "true",
        "status": fm.get("status", "unknown"),
        "authority": fm.get("authority", ""),
        "role": role_text,
        "skills": [
            l.lstrip("- ").strip()
            for l in skills_text.splitlines()
            if l.strip().startswith("-")
        ],
        "scope": scope_text,
        "channel_contract": contract_text,
        "routing_rules": routing_text,
    }


def load_json(path: Path) -> dict | list | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def file_age_minutes(path: Path) -> float | None:
    if not path.exists():
        return None
    return (time.time() - path.stat().st_mtime) / 60.0


def derive_health(agents: list[dict]) -> dict:
    """Compute per-agent + global health from runtime sources."""
    checklist = load_json(DATA_DIR / "user_checklist.json") or {}
    tasks = checklist.get("tasks", []) if isinstance(checklist, dict) else []

    pending = [t for t in tasks if t.get("status") in ("pending", "in_progress")]
    blocked = [t for t in tasks if t.get("status") == "blocked"]

    bot_pid_age = file_age_minutes(LOGS / "discord_bot.pid")
    bot_log_age = file_age_minutes(LOGS / "discord_bot.log")
    chat_log_age = file_age_minutes(LOGS / "chat_server.log")

    per_agent: dict[str, dict] = {}
    for a in agents:
        slug = a["slug"]
        warnings: list[str] = []
        errors: list[str] = []

        # Per-agent task signals
        related = [
            t
            for t in tasks
            if slug in (t.get("description", "") + " " + t.get("title", "")).lower()
        ]
        in_prog = [t for t in related if t.get("status") == "in_progress"]
        if any(t.get("priority") == "P0" for t in related if t.get("status") == "pending"):
            warnings.append("P0 pending task")

        # Dashboard freshness (if dashboard path exists in repo)
        dash = a.get("dashboard")
        if dash:
            dash_path = ROOT / dash
            if dash_path.exists():
                age = file_age_minutes(dash_path)
                if age and age > 60 * 24 * 7:
                    warnings.append(f"dashboard stale {int(age/60/24)}d")

        per_agent[slug] = {
            "status": "error" if errors else ("warn" if warnings else "ok"),
            "warnings": warnings,
            "errors": errors,
            "active_tasks": len(in_prog),
        }

    runtime_signals: list[dict] = []
    if bot_pid_age is None:
        runtime_signals.append({"id": "discord_bot", "status": "error", "msg": "PID file missing"})
    elif bot_pid_age > 60 * 12:
        runtime_signals.append({"id": "discord_bot", "status": "warn", "msg": f"PID {int(bot_pid_age/60)}h old"})
    else:
        runtime_signals.append({"id": "discord_bot", "status": "ok", "msg": f"PID {int(bot_pid_age)}m old"})

    if chat_log_age is not None and chat_log_age > 60:
        runtime_signals.append({"id": "chat_server", "status": "warn", "msg": f"log {int(chat_log_age)}m idle"})
    elif chat_log_age is not None:
        runtime_signals.append({"id": "chat_server", "status": "ok", "msg": f"log {int(chat_log_age)}m old"})

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "global": {
            "tasks_total": len(tasks),
            "tasks_pending": len(pending),
            "tasks_blocked": len(blocked),
            "bot_pid_minutes": bot_pid_age,
            "bot_log_minutes": bot_log_age,
        },
        "runtime": runtime_signals,
        "agents": per_agent,
    }


def main() -> int:
    WORKFLOW_DIR.mkdir(parents=True, exist_ok=True)

    md_files = sorted(DOCS.glob("*/AGENT.md"))
    if not md_files:
        print("[error] no AGENT.md files found under docs/*/", file=sys.stderr)
        return 1

    EXCLUDED = {"workflow"}
    agents = [parse_agent_md(p) for p in md_files if p.parent.name not in EXCLUDED]

    # Hardcoded display order (Bucky orchestrator first, audit last)
    order = [
        "chat",
        "task-board",
        "claude-code",
        "codex",
        "daily-plus",
        "chris",
        "repo",
        "wishket",
        "kmong",
        "my-dev",
        "charlie",
    ]
    agents.sort(key=lambda a: order.index(a["slug"]) if a["slug"] in order else 99)

    workflow_meta = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "count": len(agents),
        "agents": agents,
        "flow": {
            "orchestrator": "chat",
            "executors": ["claude-code", "codex"],
            "domain_inputs": ["task-board", "daily-plus", "chris", "repo", "wishket", "kmong", "my-dev"],
            "auditor": "charlie",
        },
        "edges": [
            {"from": "chat", "to": "task-board", "label": "dispatch"},
            {"from": "chat", "to": "daily-plus", "label": "knowledge"},
            {"from": "chat", "to": "repo", "label": "release"},
            {"from": "chat", "to": "wishket", "label": "client"},
            {"from": "chat", "to": "kmong", "label": "revenue"},
            {"from": "chat", "to": "my-dev", "label": "personal"},
            {"from": "task-board", "to": "claude-code", "label": "implement"},
            {"from": "task-board", "to": "codex", "label": "verify"},
            {"from": "daily-plus", "to": "chris", "label": "intake"},
            {"from": "wishket", "to": "claude-code", "label": "build"},
            {"from": "kmong", "to": "claude-code", "label": "deliver"},
            {"from": "kmong", "to": "codex", "label": "qa"},
            {"from": "my-dev", "to": "claude-code", "label": "build"},
            {"from": "my-dev", "to": "codex", "label": "verify"},
            {"from": "claude-code", "to": "codex", "label": "handoff"},
            {"from": "charlie", "to": "chat", "label": "audit"},
        ],
    }

    health = derive_health(agents)

    (WORKFLOW_DIR / "agents.json").write_text(
        json.dumps(workflow_meta, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (WORKFLOW_DIR / "health.json").write_text(
        json.dumps(health, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"[ok] wrote {WORKFLOW_DIR / 'agents.json'} ({len(agents)} agents)")
    print(f"[ok] wrote {WORKFLOW_DIR / 'health.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
