from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
VAULT = ROOT / "ObsidianVault"
COLLAB_INBOX = VAULT / "10_AgentBus" / "collab_inbox"


def _iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _stamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _split_lines(text: str) -> list[str]:
    if not text.strip():
        return []
    return [line.rstrip() for line in text.strip().splitlines()]


def normalize_inquiry(payload: dict[str, Any]) -> dict[str, Any]:
    request_id = str(payload.get("request_id") or f"collab-{uuid.uuid4().hex[:8]}")
    links = payload.get("links") or []
    if isinstance(links, str):
        links = [links]
    name = str(payload.get("name") or payload.get("requester_name") or "").strip()
    email = str(payload.get("email") or payload.get("requester_email") or "").strip()
    summary = str(payload.get("summary") or "").strip()
    body = str(payload.get("body") or payload.get("message") or "").strip()
    return {
        "type": "collab_inquiry",
        "source": str(payload.get("source") or "bni_collab_form"),
        "request_id": request_id,
        "status": str(payload.get("status") or "new"),
        "created_at": str(payload.get("created_at") or _iso()),
        "name": name,
        "email": email,
        "company": str(payload.get("company") or "").strip(),
        "budget": str(payload.get("budget") or "").strip(),
        "timeline": str(payload.get("timeline") or "").strip(),
        "summary": summary,
        "body": body,
        "links": [str(link).strip() for link in links if str(link).strip()],
        "discord_dispatched": bool(payload.get("discord_dispatched", False)),
        "proposal_started": bool(payload.get("proposal_started", False)),
        "proposal_approved": bool(payload.get("proposal_approved", False)),
        "development_requested": bool(payload.get("development_requested", False)),
        "codex_review_requested": bool(payload.get("codex_review_requested", False)),
        "admin_notes": str(payload.get("admin_notes") or "").strip(),
        "activity": [str(line).rstrip() for line in payload.get("activity") or [] if str(line).strip()],
    }


def render_inquiry_markdown(record: dict[str, Any]) -> str:
    frontmatter = [
        "---",
        f'type: {json.dumps(record["type"], ensure_ascii=False)}',
        f'source: {json.dumps(record["source"], ensure_ascii=False)}',
        f'request_id: {json.dumps(record["request_id"], ensure_ascii=False)}',
        f'status: {json.dumps(record["status"], ensure_ascii=False)}',
        f'created_at: {json.dumps(record["created_at"], ensure_ascii=False)}',
        f'name: {json.dumps(record["name"], ensure_ascii=False)}',
        f'email: {json.dumps(record["email"], ensure_ascii=False)}',
        f'company: {json.dumps(record["company"], ensure_ascii=False)}',
        f'budget: {json.dumps(record["budget"], ensure_ascii=False)}',
        f'timeline: {json.dumps(record["timeline"], ensure_ascii=False)}',
        f'summary: {json.dumps(record["summary"], ensure_ascii=False)}',
        f'links: {json.dumps(record["links"], ensure_ascii=False)}',
        f'discord_dispatched: {json.dumps(record["discord_dispatched"], ensure_ascii=False)}',
        f'proposal_started: {json.dumps(record["proposal_started"], ensure_ascii=False)}',
        f'proposal_approved: {json.dumps(record["proposal_approved"], ensure_ascii=False)}',
        f'development_requested: {json.dumps(record["development_requested"], ensure_ascii=False)}',
        f'codex_review_requested: {json.dumps(record["codex_review_requested"], ensure_ascii=False)}',
        "---",
        "",
        "## Inquiry Detail",
        "",
        record["body"] or "",
        "",
        "## Admin Notes",
        "",
        record["admin_notes"] or "",
        "",
        "## Activity Log",
        "",
    ]
    activity = record["activity"] or []
    if activity:
        frontmatter.extend(f"- {line}" for line in activity)
    return "\n".join(frontmatter).rstrip() + "\n"


def _parse_frontmatter(raw: str) -> tuple[dict[str, Any], str]:
    if not raw.startswith("---\n"):
        raise ValueError("missing frontmatter")
    parts = raw.split("\n---\n", 1)
    if len(parts) != 2:
        raise ValueError("unterminated frontmatter")
    frontmatter_text = parts[0].splitlines()[1:]
    body = parts[1]
    frontmatter: dict[str, Any] = {}
    for line in frontmatter_text:
        if ": " not in line:
            continue
        key, value = line.split(": ", 1)
        frontmatter[key.strip()] = json.loads(value.strip())
    return frontmatter, body


def load_inquiry(path: Path) -> dict[str, Any]:
    frontmatter, body = _parse_frontmatter(path.read_text(encoding="utf-8"))
    sections = body.split("\n## ")
    detail = ""
    notes = ""
    activity: list[str] = []
    for section in sections:
        normalized = section.strip()
        if not normalized:
            continue
        if normalized.startswith("Inquiry Detail"):
            detail = normalized[len("Inquiry Detail"):].strip()
        elif normalized.startswith("Admin Notes"):
            notes = normalized[len("Admin Notes"):].strip()
        elif normalized.startswith("Activity Log"):
            lines = normalized[len("Activity Log"):].strip().splitlines()
            activity = [line[2:] if line.startswith("- ") else line for line in lines if line.strip()]
    return {
        **frontmatter,
        "body": detail,
        "admin_notes": notes,
        "activity": activity,
    }


def write_inquiry(path: Path, record: dict[str, Any]) -> Path:
    normalized = normalize_inquiry(record)
    path.write_text(render_inquiry_markdown(normalized), encoding="utf-8")
    return path


def create_inquiry(payload: dict[str, Any]) -> Path:
    COLLAB_INBOX.mkdir(parents=True, exist_ok=True)
    normalized = normalize_inquiry(payload)
    path = COLLAB_INBOX / f"{_stamp()}_{normalized['request_id']}.md"
    return write_inquiry(path, normalized)


def list_inquiries() -> list[dict[str, Any]]:
    if not COLLAB_INBOX.exists():
        return []
    items: list[dict[str, Any]] = []
    for path in sorted(COLLAB_INBOX.glob("*.md"), reverse=True):
        try:
            record = load_inquiry(path)
        except Exception:
            continue
        record["path"] = str(path)
        items.append(record)
    return items


def find_inquiry_by_request_id(request_id: str) -> Path | None:
    if not request_id or not COLLAB_INBOX.exists():
        return None
    for path in COLLAB_INBOX.glob("*.md"):
        try:
            record = load_inquiry(path)
        except Exception:
            continue
        if record.get("request_id") == request_id:
            return path
    return None


def update_status(path: Path, status: str, actor: str = "admin") -> Path:
    record = load_inquiry(path)
    record["status"] = status
    record["activity"] = list(record.get("activity") or [])
    record["activity"].append(f"{actor} changed status to {status}")
    return write_inquiry(path, record)


def save_admin_note(path: Path, note: str) -> Path:
    record = load_inquiry(path)
    record["admin_notes"] = note.strip()
    record["activity"] = list(record.get("activity") or [])
    record["activity"].append("admin saved note")
    return write_inquiry(path, record)
