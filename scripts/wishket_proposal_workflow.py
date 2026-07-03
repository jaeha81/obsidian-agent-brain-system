from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
VAULT = ROOT / "ObsidianVault"
WORKFLOW_ROOT = VAULT / "10_AgentBus" / "wishket_dev"


def _iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _project_id_from_payload(payload: dict[str, Any]) -> str:
    link = str(payload.get("url") or payload.get("link") or "").strip()
    match = re.search(r"/project/(\d+)/?", link)
    if match:
        return f"project-{match.group(1)}"
    slug = str(payload.get("project_slug") or "wishket-project").strip()
    return f"project-{slug}"


def _workspace(slug: str) -> Path:
    if not re.fullmatch(r"[a-z0-9-]+", slug):
        raise ValueError(f"unsafe project slug: {slug!r}")
    return WORKFLOW_ROOT / slug


def _status_path(slug: str) -> Path:
    return _workspace(slug) / "status.json"


def default_status(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "project_id": _project_id_from_payload(payload),
        "project_slug": payload["project_slug"],
        "project_title": payload.get("project_title") or payload.get("title") or payload["project_slug"],
        "workflow_state": "idle",
        "proposal_version": 0,
        "current_proposal_file": None,
        "feedback_count": 0,
        "feedback_pending": False,
        "approved": False,
        "approved_via": None,
        "approved_at": None,
        "development_requested": False,
        "last_discord_message_type": None,
        "updated_at": _iso(),
    }


def ensure_project_workspace(payload: dict[str, Any]) -> Path:
    workspace = _workspace(payload["project_slug"])
    workspace.mkdir(parents=True, exist_ok=True)
    status_path = workspace / "status.json"
    if not status_path.exists():
        status_path.write_text(json.dumps(default_status(payload), ensure_ascii=False, indent=2), encoding="utf-8")
    return workspace


def load_status(project_slug: str) -> dict[str, Any]:
    status_path = _status_path(project_slug)
    return json.loads(status_path.read_text(encoding="utf-8"))


def save_status(project_slug: str, status: dict[str, Any]) -> dict[str, Any]:
    status["updated_at"] = _iso()
    status_path = _status_path(project_slug)
    status_path.write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8")
    return status


def _extract_version(filename: str) -> int:
    match = re.search(r"v(\d+)", filename)
    return int(match.group(1)) if match else 1


def mark_proposal_ready(payload: dict[str, Any], filename: str) -> dict[str, Any]:
    ensure_project_workspace(payload)
    status = load_status(payload["project_slug"])
    status["workflow_state"] = "proposal_ready"
    status["proposal_version"] = _extract_version(filename)
    status["current_proposal_file"] = filename
    status["feedback_pending"] = False
    return save_status(payload["project_slug"], status)


def mark_proposal_started(payload: dict[str, Any], source: str = "discord") -> dict[str, Any]:
    ensure_project_workspace(payload)
    status = load_status(payload["project_slug"])
    status["workflow_state"] = "proposal_in_progress"
    status["last_discord_message_type"] = source
    return save_status(payload["project_slug"], status)


def record_feedback(payload: dict[str, Any], feedback: str) -> dict[str, Any]:
    workspace = ensure_project_workspace(payload)
    feedback_path = workspace / "feedback.md"
    existing = feedback_path.read_text(encoding="utf-8") if feedback_path.exists() else ""
    entry = f"\n## {_iso()}\n\n{feedback.strip()}\n"
    feedback_path.write_text((existing + entry).strip() + "\n", encoding="utf-8")
    status = load_status(payload["project_slug"])
    status["workflow_state"] = "feedback_in_progress"
    status["feedback_pending"] = True
    status["feedback_count"] = int(status.get("feedback_count") or 0) + 1
    return save_status(payload["project_slug"], status)


def record_approval(payload: dict[str, Any], source: str) -> dict[str, Any]:
    ensure_project_workspace(payload)
    status = load_status(payload["project_slug"])
    status["workflow_state"] = "approved"
    status["approved"] = True
    status["approved_via"] = source
    status["approved_at"] = _iso()
    status["feedback_pending"] = False
    return save_status(payload["project_slug"], status)
