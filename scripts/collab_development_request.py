from __future__ import annotations

import json
import re
import unicodedata
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

import collab_proposal_workflow as workflow


ROOT = Path(__file__).resolve().parent.parent
VAULT = ROOT / "ObsidianVault"
INBOX_DIR = VAULT / "10_AgentBus" / "inbox"

REQUEST_TYPE = "collab_development_request"
REQUESTED_ACTIONS = [
    "generate_development_plan",
    "route_to_claude_for_implementation",
    "route_to_codex_for_review",
]


def _iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def safe_slug(title: str, fallback: str) -> str:
    ascii_title = (
        unicodedata.normalize("NFKD", title or "")
        .encode("ascii", "ignore")
        .decode("ascii")
        .lower()
    )
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_title).strip("-")
    return slug or fallback


def normalize_payload(data: dict[str, Any]) -> dict[str, Any]:
    request_id = str(data.get("request_id") or f"collab-{uuid.uuid4().hex[:8]}")
    summary = str(data.get("summary") or "").strip()
    requester_name = str(data.get("requester_name") or data.get("name") or "").strip()
    requester_email = str(data.get("requester_email") or data.get("email") or "").strip()
    request_slug = str(data.get("request_slug") or "").strip()
    if not request_slug:
        request_slug = safe_slug(f"{request_id}-{summary}", request_id)
    return {
        "type": REQUEST_TYPE,
        "request_id": request_id,
        "request_slug": request_slug,
        "project_title": str(data.get("project_title") or summary or request_slug).strip(),
        "summary": summary,
        "requester_name": requester_name,
        "requester_email": requester_email,
        "email": requester_email,
        "company": str(data.get("company") or "").strip(),
        "budget": str(data.get("budget") or "").strip(),
        "timeline": str(data.get("timeline") or "").strip(),
        "body": str(data.get("body") or "").strip(),
        "links": [str(link).strip() for link in (data.get("links") or []) if str(link).strip()],
        "requested_actions": list(data.get("requested_actions") or REQUESTED_ACTIONS),
        "source": str(data.get("source") or "collab_admin"),
        "created_at": str(data.get("created_at") or _iso()),
    }


def _find_existing_by_request_id(directory: Path, request_id: str, needle: str) -> Path | None:
    if not directory.exists():
        return None
    for existing in directory.glob("*.md"):
        try:
            content = existing.read_text(encoding="utf-8")
        except OSError:
            continue
        if needle in content:
            return existing
    return None


def _write_note(path: Path, frontmatter: dict[str, Any], body: str) -> Path:
    fm_lines = ["---"] + [f"{k}: {json.dumps(v, ensure_ascii=False)}" for k, v in frontmatter.items()] + ["---", ""]
    path.write_text("\n".join(fm_lines) + body, encoding="utf-8")
    return path


def enqueue_claude_request(payload: dict[str, Any]) -> Path:
    INBOX_DIR.mkdir(parents=True, exist_ok=True)
    request_id = payload["request_id"]
    existing = _find_existing_by_request_id(INBOX_DIR, request_id, f"collab_request_id: {request_id}")
    if existing:
        return existing
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = INBOX_DIR / f"{ts}_{payload['request_slug']}_collab_impl.md"
    frontmatter = {
        "type": "implementation_request",
        "source": payload["source"],
        "status": "pending",
        "requires_approval": False,
        "created": _iso(),
        "project_slug": payload["request_slug"],
        "collab_request_id": request_id,
        "title": payload["project_title"],
        "router": "ClaudeCode",
    }
    body = (
        "# Collaboration Immediate Execution Request\n\n"
        f"- Project: {payload['project_title']}\n"
        f"- Company: {payload['company'] or '(none)'}\n"
        f"- Requester: {payload['requester_name'] or '(none)'}\n"
        f"- Requester email: {payload['requester_email'] or '(none)'}\n"
        f"- Budget: {payload['budget'] or '(none)'}\n"
        f"- Timeline: {payload['timeline'] or '(none)'}\n\n"
        "## Summary\n\n"
        f"{payload['summary'] or 'No summary provided.'}\n\n"
        "## Detail\n\n"
        f"{payload['body'] or 'No detail provided.'}\n"
    )
    if payload["links"]:
        body += "\n## Links\n\n" + "\n".join(f"- {link}" for link in payload["links"]) + "\n"
    return _write_note(path, frontmatter, body)


def enqueue_codex_review_request(payload: dict[str, Any]) -> Path:
    INBOX_DIR.mkdir(parents=True, exist_ok=True)
    request_id = payload["request_id"]
    existing = _find_existing_by_request_id(INBOX_DIR, request_id, f"collab_review_id: {request_id}")
    if existing:
        return existing
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = INBOX_DIR / f"{ts}_{payload['request_slug']}_collab_review.md"
    frontmatter = {
        "type": "review_request",
        "source": payload["source"],
        "status": "pending",
        "requires_approval": False,
        "created": _iso(),
        "project_slug": payload["request_slug"],
        "collab_review_id": request_id,
        "title": f"[Codex Review] {payload['project_title']}",
        "router": "Codex",
    }
    body = (
        "# Collaboration Codex Review Request\n\n"
        f"- Project: {payload['project_title']}\n"
        f"- Company: {payload['company'] or '(none)'}\n\n"
        "## Summary\n\n"
        f"{payload['summary'] or 'No summary provided.'}\n"
    )
    return _write_note(path, frontmatter, body)


def dispatch_request(payload: dict[str, Any], require_workflow_approval: bool = False) -> tuple[str, Path, Path]:
    if require_workflow_approval:
        status = workflow.load_status(payload["request_slug"])
        if not status.get("approved"):
            raise PermissionError("Collaboration proposal workflow is not approved yet.")
    claude_path = enqueue_claude_request(payload)
    codex_path = enqueue_codex_review_request(payload)
    workflow.mark_development_requested(payload, "admin")
    return "immediate", claude_path, codex_path
