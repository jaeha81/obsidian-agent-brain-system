from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
VAULT = ROOT / "ObsidianVault"
WORKFLOW_ROOT = VAULT / "10_AgentBus" / "collab_dev"


def _iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _workspace(slug: str) -> Path:
    return WORKFLOW_ROOT / slug


def default_status(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "request_id": payload["request_id"],
        "request_slug": payload["request_slug"],
        "project_title": payload.get("project_title") or payload.get("summary") or payload["request_slug"],
        "workflow_state": "new",
        "proposal_version": 0,
        "current_proposal_file": None,
        "feedback_count": 0,
        "approved": False,
        "approved_via": None,
        "approved_at": None,
        "development_requested": False,
        "discord_dispatched": False,
        "codex_review_requested": False,
        "updated_at": _iso(),
    }


def ensure_workspace(payload: dict[str, Any]) -> Path:
    workspace = _workspace(payload["request_slug"])
    workspace.mkdir(parents=True, exist_ok=True)
    status_path = workspace / "status.json"
    if not status_path.exists():
        status_path.write_text(json.dumps(default_status(payload), ensure_ascii=False, indent=2), encoding="utf-8")
    return workspace


def load_status(request_slug: str) -> dict[str, Any]:
    return json.loads((_workspace(request_slug) / "status.json").read_text(encoding="utf-8"))


def save_status(request_slug: str, status: dict[str, Any]) -> dict[str, Any]:
    status["updated_at"] = _iso()
    (_workspace(request_slug) / "status.json").write_text(
        json.dumps(status, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return status


def mark_proposal_started(payload: dict[str, Any], source: str) -> dict[str, Any]:
    ensure_workspace(payload)
    status = load_status(payload["request_slug"])
    status["workflow_state"] = "proposal_in_progress"
    status["discord_dispatched"] = True
    status["updated_via"] = source
    return save_status(payload["request_slug"], status)


def mark_discord_dispatched(payload: dict[str, Any], source: str) -> dict[str, Any]:
    ensure_workspace(payload)
    status = load_status(payload["request_slug"])
    status["discord_dispatched"] = True
    status["updated_via"] = source
    return save_status(payload["request_slug"], status)


def record_feedback(payload: dict[str, Any], source: str) -> dict[str, Any]:
    ensure_workspace(payload)
    status = load_status(payload["request_slug"])
    status["workflow_state"] = "feedback_in_progress"
    status["feedback_count"] = int(status.get("feedback_count") or 0) + 1
    status["updated_via"] = source
    return save_status(payload["request_slug"], status)


def record_approval(payload: dict[str, Any], source: str) -> dict[str, Any]:
    ensure_workspace(payload)
    status = load_status(payload["request_slug"])
    status["workflow_state"] = "approved"
    status["approved"] = True
    status["approved_via"] = source
    status["approved_at"] = _iso()
    return save_status(payload["request_slug"], status)


def mark_development_requested(payload: dict[str, Any], source: str) -> dict[str, Any]:
    ensure_workspace(payload)
    status = load_status(payload["request_slug"])
    status["workflow_state"] = "development_requested"
    status["development_requested"] = True
    status["updated_via"] = source
    return save_status(payload["request_slug"], status)


def mark_codex_review_requested(payload: dict[str, Any], source: str) -> dict[str, Any]:
    ensure_workspace(payload)
    status = load_status(payload["request_slug"])
    status["codex_review_requested"] = True
    status["updated_via"] = source
    return save_status(payload["request_slug"], status)
