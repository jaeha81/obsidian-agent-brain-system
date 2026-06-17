#!/usr/bin/env python3
"""Workflow helpers for JH Google automation revenue dashboard.

The module prepares Bucky/AgentBus requests for a Blogger and AdSense revenue
operation. It never clicks ads, manipulates traffic, publishes in bulk, or
stores secrets. Content generation actions always keep a human-review gate.
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
INBOX_DIR = VAULT / "10_AgentBus" / "jh_google_revenue_inbox"

REQUEST_TYPE = "jh_google_revenue_request"
DASHBOARD_TYPE = "jh_google_revenue"
PROJECT_NAME = "JH-구글자동화수익대시보드"
DISCORD_CHANNEL = "jh-google-revenue-dashboard"
DEFAULT_CREDENTIAL_SOURCE = "environment"

SECRET_FIELD_NAMES = {
    "password",
    "passwd",
    "secret",
    "token",
    "cookie",
    "session",
    "authorization",
    "auth",
    "webhook",
    "client_secret",
    "refresh_token",
    "access_token",
}

IMMEDIATE_ACTIONS: frozenset[str] = frozenset(
    {
        "analyze_plan",
        "score_keyword",
        "draft_outline",
        "draft_article",
        "run_policy_check",
        "create_review_packet",
        "update_kpi_snapshot",
        "prepare_make_webhook_payload",
        "draft_blogger_post",
        "sync_manual_metrics",
    }
)

APPROVAL_REQUIRED_ACTIONS: frozenset[str] = frozenset(
    {
        "create_discord_channel",
        "send_make_webhook",
        "import_search_console_data",
        "import_adsense_data",
        "publish_blogger_draft",
        "request_adsense_review",
        "send_weekly_report",
        "update_public_site",
    }
)

FORBIDDEN_ACTIONS: frozenset[str] = frozenset(
    {
        "click_ads",
        "self_click_ads",
        "ask_others_to_click_ads",
        "simulate_traffic",
        "buy_traffic",
        "mass_publish",
        "auto_publish_without_review",
        "generate_low_value_content",
        "bypass_adsense_policy",
        "scrape_private_data",
    }
)

CONTENT_ACTIONS: frozenset[str] = frozenset(
    {
        "draft_outline",
        "draft_article",
        "draft_blogger_post",
        "publish_blogger_draft",
        "request_adsense_review",
    }
)

AGENT_ROSTER: tuple[dict[str, str], ...] = (
    {
        "id": "keyword_scout",
        "name": "KeywordScout",
        "role": "Google Trends, Search Console, and manual keyword scoring",
    },
    {
        "id": "content_draft",
        "name": "ContentDraft",
        "role": "SEO outline and Blogger draft preparation",
    },
    {
        "id": "policy_guard",
        "name": "PolicyGuard",
        "role": "AdSense, spam, invalid-traffic, and AI-content policy checks",
    },
    {
        "id": "human_review",
        "name": "HumanReview",
        "role": "Required approval gate before publication or external send",
    },
    {
        "id": "revenue_analyst",
        "name": "RevenueAnalyst",
        "role": "RPM, pageview, lead, and content performance analysis",
    },
    {
        "id": "make_bridge",
        "name": "MakeBridge",
        "role": "Make.com webhook packet preparation and low-cost automation bridge",
    },
    {
        "id": "discord_ops",
        "name": "DiscordOps",
        "role": f"Queue status reporting for #{DISCORD_CHANNEL}",
    },
)


def _iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def safe_slug(title: str, fallback: str = "jh-google-revenue") -> str:
    ascii_title = (
        unicodedata.normalize("NFKD", title or "")
        .encode("ascii", "ignore")
        .decode("ascii")
        .lower()
    )
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_title).strip("-")
    slug = slug[:72].strip("-")
    return slug if len(slug) >= 4 else fallback


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


def split_actions(requested_actions: list[str]) -> dict[str, list[str]]:
    immediate: list[str] = []
    approval_required: list[str] = []
    forbidden: list[str] = []
    for action in requested_actions:
        if action in FORBIDDEN_ACTIONS:
            forbidden.append(action)
        elif action in IMMEDIATE_ACTIONS:
            immediate.append(action)
        elif action in APPROVAL_REQUIRED_ACTIONS:
            approval_required.append(action)
        else:
            approval_required.append(action)
    return {
        "immediate": immediate,
        "approval_required": approval_required,
        "forbidden": forbidden,
    }


def normalize_payload(data: dict[str, Any]) -> dict[str, Any]:
    clean_input = sanitize_payload(dict(data))
    action = str(data.get("action") or "analyze_plan").strip()
    title = str(data.get("title") or data.get("project_title") or PROJECT_NAME).strip()
    raw_actions = data.get("requested_actions") or [action]
    if isinstance(raw_actions, str):
        raw_actions = [raw_actions]
    requested_actions = [str(item).strip() for item in raw_actions if str(item).strip()]
    actions = split_actions(requested_actions)
    request_id = str(data.get("request_id") or f"jhgrev-{uuid.uuid4()}")
    content_actions = [item for item in requested_actions if item in CONTENT_ACTIONS]
    blocked = bool(actions["forbidden"])
    approval_required = bool(actions["approval_required"]) or blocked

    return {
        "type": REQUEST_TYPE,
        "dashboard_type": DASHBOARD_TYPE,
        "project_name": PROJECT_NAME,
        "target_channel": DISCORD_CHANNEL,
        "request_id": request_id,
        "source": data.get("source") or "jh_google_revenue_dashboard",
        "source_dashboard_url": data.get("source_dashboard_url") or "",
        "action": action,
        "title": title,
        "work_slug": str(data.get("work_slug") or safe_slug(title)),
        "summary": str(data.get("summary") or data.get("description") or "").strip(),
        "keyword": str(data.get("keyword") or "").strip(),
        "content_cluster": str(data.get("content_cluster") or "google-adsense-basics").strip(),
        "stage": str(data.get("stage") or "phase-0").strip(),
        "requested_actions": requested_actions,
        "immediate_actions": actions["immediate"],
        "approval_required_actions": actions["approval_required"],
        "forbidden_actions": actions["forbidden"],
        "approval_required": approval_required,
        "execution_mode": "blocked" if blocked else "approval_required" if approval_required else "immediate",
        "human_review_required": bool(content_actions) or bool(data.get("human_review_required", True)),
        "policy": {
            "forbidden_actions": sorted(FORBIDDEN_ACTIONS),
            "requires_human_review_for_content": True,
            "no_ad_clicking": True,
            "no_traffic_manipulation": True,
            "no_bulk_auto_publish": True,
            "secrets_source": DEFAULT_CREDENTIAL_SOURCE,
        },
        "agent_roster": list(AGENT_ROSTER),
        "redacted_input": clean_input,
        "created_at": data.get("created_at") or _iso(),
    }


def render_agentbus_note(payload: dict[str, Any]) -> str:
    safe_payload = sanitize_payload(payload)
    forbidden = safe_payload.get("forbidden_actions") or []
    approval = safe_payload.get("approval_required_actions") or []
    immediate = safe_payload.get("immediate_actions") or []
    return (
        "# JH Google Revenue Automation Request\n\n"
        f"- Project: {safe_payload.get('project_name')}\n"
        f"- Discord channel: #{safe_payload.get('target_channel')}\n"
        f"- Title: {safe_payload.get('title') or '(none)'}\n"
        f"- Action: {safe_payload.get('action') or '(none)'}\n"
        f"- Stage: {safe_payload.get('stage') or '(none)'}\n"
        f"- Request ID: {safe_payload.get('request_id') or '(none)'}\n"
        f"- Execution mode: {safe_payload.get('execution_mode') or '(none)'}\n"
        f"- Immediate actions: {', '.join(immediate) or 'none'}\n"
        f"- Approval-required actions: {', '.join(approval) or 'none'}\n"
        f"- Forbidden actions blocked: {', '.join(forbidden) or 'none'}\n"
        f"- Human review required: {safe_payload.get('human_review_required')}\n\n"
        "## Operating Policy\n\n"
        "- Never click ads, ask others to click ads, simulate traffic, buy traffic, or bypass AdSense policy.\n"
        "- Never auto-publish generated content without a human review packet.\n"
        "- Keep Blogger, AdSense, Search Console, Make.com, and Discord secrets in environment variables only.\n"
        "- Use Make.com only as a low-cost bridge after review gates are satisfied.\n\n"
        "## Agent Roster\n\n"
        + "\n".join(
            f"- {agent['name']}: {agent['role']}" for agent in safe_payload.get("agent_roster", [])
        )
        + "\n\n## Payload\n\n"
        "```json\n"
        f"{json.dumps(safe_payload, ensure_ascii=False, indent=2)}\n"
        "```\n"
    )


def enqueue_request(payload: dict[str, Any]) -> Path:
    INBOX_DIR.mkdir(parents=True, exist_ok=True)
    request_id = str(payload.get("request_id") or f"jhgrev-{uuid.uuid4()}")
    slug = safe_slug(str(payload.get("title") or payload.get("action") or "jh-google-revenue"))
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = INBOX_DIR / f"{ts}_{slug}_{request_id[:10]}.md"
    frontmatter = {
        "type": REQUEST_TYPE,
        "dashboard_type": DASHBOARD_TYPE,
        "project": PROJECT_NAME,
        "status": "blocked" if payload.get("forbidden_actions") else "pending",
        "requires_approval": bool(payload.get("approval_required")),
        "human_review_required": bool(payload.get("human_review_required")),
        "created": _iso(),
        "request_id": request_id,
        "title": payload.get("title") or "",
    }
    fm = ["---"] + [f"{key}: {value}" for key, value in frontmatter.items()] + ["---", ""]
    path.write_text("\n".join(fm) + render_agentbus_note(payload), encoding="utf-8")
    return path


def sample_payload() -> dict[str, Any]:
    return normalize_payload(
        {
            "action": "draft_article",
            "title": "블로그 애드센스 승인 체크리스트",
            "keyword": "블로그 애드센스 승인 체크리스트",
            "requested_actions": ["score_keyword", "draft_outline", "draft_article", "run_policy_check"],
        }
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="JH Google revenue workflow normalizer")
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
