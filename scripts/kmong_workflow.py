#!/usr/bin/env python3
"""Kmong monetization workflow helpers for Bucky dashboard intake.

This module deliberately does not perform a live Kmong login on import or by
default. Login automation must read credentials from environment variables at
runtime and stop on captcha, OTP, or any manual-auth challenge.
"""

from __future__ import annotations

import argparse
import json
import re
import unicodedata
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
VAULT = ROOT / "ObsidianVault"
KMONG_INBOX_DIR = VAULT / "10_AgentBus" / "kmong_inbox"
KMONG_WORK_DIR = VAULT / "10_AgentBus" / "kmong_work"

REQUEST_TYPE = "kmong_workflow_request"
DASHBOARD_TYPE = "kmong"
DEFAULT_CREDENTIAL_SOURCE = "environment"

IMMEDIATE_ACTIONS: frozenset[str] = frozenset(
    {
        "check_login_status",
        "sync_kmong_requests",
        "analyze_request",
        "draft_customer_reply",
        "draft_delivery_plan",
        "update_work_status",
    }
)

APPROVAL_REQUIRED_ACTIONS: frozenset[str] = frozenset(
    {
        "login_kmong",
        "send_customer_reply",
        "accept_order",
        "submit_delivery",
        "change_price",
        "payment_or_billing_action",
        "download_customer_file",
        "upload_customer_file",
    }
)

SECRET_FIELD_NAMES = {
    "password",
    "passwd",
    "secret",
    "token",
    "cookie",
    "session",
    "authorization",
    "auth",
    "username",
    "email",
}


def _iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def safe_slug(title: str, fallback: str = "kmong-work") -> str:
    ascii_title = (
        unicodedata.normalize("NFKD", title or "")
        .encode("ascii", "ignore")
        .decode("ascii")
        .lower()
    )
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_title).strip("-")
    return slug[:60].strip("-") or fallback


def split_actions(requested_actions: list[str]) -> dict[str, list[str]]:
    immediate: list[str] = []
    approval_required: list[str] = []
    for action in requested_actions:
        if action in IMMEDIATE_ACTIONS:
            immediate.append(action)
        elif action in APPROVAL_REQUIRED_ACTIONS:
            approval_required.append(action)
        else:
            approval_required.append(action)
    return {"immediate": immediate, "approval_required": approval_required}


def redact_value(key: str, value: Any) -> Any:
    key_l = key.lower()
    if any(secret in key_l for secret in SECRET_FIELD_NAMES):
        return "[redacted]"
    return value


def sanitize_payload(data: dict[str, Any]) -> dict[str, Any]:
    clean: dict[str, Any] = {}
    for key, value in data.items():
        if isinstance(value, dict):
            clean[key] = sanitize_payload(value)
        elif isinstance(value, list):
            clean[key] = [sanitize_payload(v) if isinstance(v, dict) else v for v in value]
        else:
            clean[key] = redact_value(key, value)
    return clean


def normalize_payload(data: dict[str, Any]) -> dict[str, Any]:
    clean_input = sanitize_payload(dict(data))
    action = str(data.get("action") or "sync_requests").strip()
    title = str(data.get("title") or data.get("project_title") or action).strip()
    raw_actions = data.get("requested_actions") or [action]
    if isinstance(raw_actions, str):
        raw_actions = [raw_actions]
    requested_actions = [str(item).strip() for item in raw_actions if str(item).strip()]
    actions = split_actions(requested_actions)
    request_id = str(data.get("request_id") or f"kmong-{uuid.uuid4()}")

    return {
        "type": REQUEST_TYPE,
        "dashboard_type": DASHBOARD_TYPE,
        "target_channel": "jh-크몽수익화",
        "request_id": request_id,
        "source": data.get("source") or "kmong_dashboard",
        "source_dashboard_url": data.get("source_dashboard_url") or "",
        "action": action,
        "title": title,
        "work_slug": str(data.get("work_slug") or safe_slug(title)),
        "summary": str(data.get("summary") or data.get("description") or "").strip(),
        "customer_alias": str(data.get("customer_alias") or "").strip(),
        "kmong_url": str(data.get("kmong_url") or data.get("url") or "").strip(),
        "credential_source": DEFAULT_CREDENTIAL_SOURCE,
        "requested_actions": requested_actions,
        "immediate_actions": actions["immediate"],
        "approval_required_actions": actions["approval_required"],
        "approval_required": bool(actions["approval_required"]),
        "execution_mode": "approval_required" if actions["approval_required"] else "immediate",
        "login_policy": {
            "credential_source": DEFAULT_CREDENTIAL_SOURCE,
            "env_keys": ["KMONG_EMAIL", "KMONG_PASSWORD"],
            "manual_challenge_state": "manual_auth_required",
            "store_secrets_in_dashboard": False,
        },
        "redacted_input": clean_input,
        "created_at": data.get("created_at") or _iso(),
    }


def login_status_from_event(event: dict[str, Any]) -> dict[str, Any]:
    status = str(event.get("status") or "unknown").strip().lower()
    challenge_type = str(event.get("challenge_type") or event.get("reason") or "").strip().lower()
    if status in {"challenge", "captcha", "otp", "2fa", "manual_auth_required"}:
        reason = challenge_type or status
        return {
            "state": "manual_auth_required",
            "can_continue": False,
            "reason": reason,
            "message": str(event.get("message") or "Manual Kmong authentication is required."),
        }
    if status in {"ok", "logged_in", "success"}:
        return {
            "state": "logged_in",
            "can_continue": True,
            "reason": "",
            "message": str(event.get("message") or "Kmong login session is active."),
        }
    return {
        "state": "unknown",
        "can_continue": False,
        "reason": status or "unknown",
        "message": str(event.get("message") or "Kmong login state is unknown."),
    }


def render_agentbus_note(payload: dict[str, Any]) -> str:
    safe_payload = sanitize_payload(payload)
    return (
        "# Kmong Workflow Request\n\n"
        f"- Title: {safe_payload.get('title') or '(none)'}\n"
        f"- Action: {safe_payload.get('action') or '(none)'}\n"
        f"- Request ID: {safe_payload.get('request_id') or '(none)'}\n"
        f"- Execution mode: {safe_payload.get('execution_mode') or '(none)'}\n"
        f"- Immediate actions: {', '.join(safe_payload.get('immediate_actions') or []) or 'none'}\n"
        f"- Approval-required actions: {', '.join(safe_payload.get('approval_required_actions') or []) or 'none'}\n\n"
        "## Security Policy\n\n"
        "- Kmong credentials are read only from KMONG_EMAIL / KMONG_PASSWORD at runtime.\n"
        "- Captcha, OTP, or suspicious-login challenges stop automation as manual_auth_required.\n"
        "- Customer-facing send, order acceptance, delivery, payment, and file-transfer actions require approval.\n\n"
        "## Payload\n\n"
        "```json\n"
        f"{json.dumps(safe_payload, ensure_ascii=False, indent=2)}\n"
        "```\n"
    )


def enqueue_request(payload: dict[str, Any]) -> Path:
    KMONG_INBOX_DIR.mkdir(parents=True, exist_ok=True)
    request_id = str(payload.get("request_id") or f"kmong-{uuid.uuid4()}")
    slug = safe_slug(str(payload.get("title") or payload.get("action") or "kmong-work"))
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = KMONG_INBOX_DIR / f"{ts}_{slug}_{request_id[:8]}.md"
    frontmatter = {
        "type": REQUEST_TYPE,
        "dashboard_type": DASHBOARD_TYPE,
        "status": "pending",
        "requires_approval": bool(payload.get("approval_required")),
        "created": _iso(),
        "kmong_request_id": request_id,
        "title": payload.get("title") or "",
    }
    fm = ["---"] + [f"{k}: {v}" for k, v in frontmatter.items()] + ["---", ""]
    path.write_text("\n".join(fm) + render_agentbus_note(payload), encoding="utf-8")
    return path


def sample_payload() -> dict[str, Any]:
    return normalize_payload(
        {
            "action": "sync_requests",
            "title": "Kmong request sync",
            "requested_actions": ["sync_kmong_requests", "analyze_request", "draft_customer_reply"],
        }
    )


KMONG_WORK_ITEMS_PATH = ROOT / "data" / "kmong_work_items.json"

# Patterns found in Kmong notification emails
_KMONG_URL_RE = re.compile(r"https://kmong\.com/(?:gig|service|chat|order)/[\w\-/]+", re.IGNORECASE)
_SUBJECT_KEYWORDS = ("크몽", "새 메시지", "새 주문", "견적 요청", "문의", "새 의뢰")


def parse_kmong_email(subject: str, body: str) -> dict[str, Any] | None:
    """Extract Kmong inquiry info from a notification email.

    Returns a work-item dict ready to merge into kmong_work_items.json,
    or None if the email doesn't look like a Kmong notification.
    """
    subject_l = subject.lower()
    if not any(kw in subject_l or kw in body[:200] for kw in _SUBJECT_KEYWORDS):
        return None

    urls = _KMONG_URL_RE.findall(body)
    kmong_url = urls[0] if urls else ""

    # Derive a human-readable title from subject
    title = subject.strip() or "크몽 신규 의뢰"

    return {
        "id": f"km-email-{uuid.uuid4().hex[:8]}",
        "title": title,
        "customer": "",
        "state": "new",
        "price": "견적 필요",
        "kmong_url": kmong_url,
        "draft_reply": "",
        "email_subject": subject,
        "created_at": _iso(),
        "updated_at": _iso(),
    }


def sync_email_to_work_items(email_items: list[dict[str, Any]]) -> dict[str, Any]:
    """Merge parsed email items into data/kmong_work_items.json.

    Skips duplicates by email_subject. Returns {added, skipped, total}.
    """
    if KMONG_WORK_ITEMS_PATH.exists():
        data = json.loads(KMONG_WORK_ITEMS_PATH.read_text(encoding="utf-8"))
    else:
        data = {"meta": {"last_updated": _iso(), "source": "email", "version": "1.0"}, "items": []}

    existing_subjects = {item.get("email_subject", "") for item in data.get("items", []) if item.get("email_subject")}

    added = 0
    skipped = 0
    for item in email_items:
        subj = item.get("email_subject", "")
        if subj and subj in existing_subjects:
            skipped += 1
            continue
        data.setdefault("items", []).append(item)
        if subj:
            existing_subjects.add(subj)
        added += 1

    data["meta"]["last_updated"] = _iso()
    data["meta"]["source"] = "email"
    KMONG_WORK_ITEMS_PATH.parent.mkdir(parents=True, exist_ok=True)
    KMONG_WORK_ITEMS_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"added": added, "skipped": skipped, "total": len(data["items"])}


def main() -> int:
    parser = argparse.ArgumentParser(description="Kmong workflow request normalizer")
    parser.add_argument("--sample", action="store_true")
    parser.add_argument("--payload-json")
    parser.add_argument("--queue", action="store_true")
    args = parser.parse_args()

    if args.sample:
        payload = sample_payload()
    elif args.payload_json:
        payload = normalize_payload(json.loads(args.payload_json))
    else:
        parser.error("provide --sample or --payload-json")

    if args.queue:
        path = enqueue_request(payload)
        payload["queued_path"] = str(path)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
