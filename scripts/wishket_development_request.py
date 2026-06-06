#!/usr/bin/env python3
"""Wishket development request planner.

Default mode is dry-run. Non-dry-run local project creation is explicit and
still does not create a GitHub repository or run workers by itself.
"""

from __future__ import annotations

import argparse
import json
import re
import unicodedata
import uuid as _uuid_mod
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
VAULT = ROOT / "ObsidianVault"
PENDING_DIR = VAULT / "10_AgentBus" / "pending_approval"
DEV_ROOT = Path(r"D:\ai프로젝트")

REQUEST_TYPE = "wishket_development_request"
REQUESTED_ACTIONS = [
    "create_local_project_folder",
    "create_github_repository",
    "generate_development_plan",
    "route_to_claude_for_implementation",
    "route_to_codex_for_review",
]

IMMEDIATE_ACTIONS: frozenset[str] = frozenset({
    # 읽기/분석 전용 — 파일시스템·에이전트 실행 없음
    "analyze_requirements",
    "create_design_doc",
    "create_task_queue_entry",
    "generate_development_plan",
})

APPROVAL_REQUIRED_ACTIONS: frozenset[str] = frozenset({
    # 로컬 파일시스템·에이전트 실행 → 모두 승인 필요
    "create_local_project_folder",
    "route_to_claude_for_implementation",
    "route_to_codex_for_review",
    # 외부/파괴적 작업
    "create_github_repository",
    "delete_repository",
    "git_push",
    "git_force_push",
    "deploy_vercel",
    "deploy_cloudflare",
    "modify_supabase",
    "create_supabase_project",
    "publish_chrome_extension",
    "payment_or_billing_action",
    "scrape_external_site",
})


def split_actions(requested_actions: list[str]) -> dict[str, list[str]]:
    """Split actions into immediately executable vs approval-required.

    Unknown actions default to approval_required for safety.
    """
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


def _iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def safe_slug(title: str, link: str = "", fallback: str = "wishket-project") -> str:
    """Return ASCII-only slug with [a-z0-9-]."""
    link_id = ""
    match = re.search(r"/project/(\d+)/?", link or "")
    if match:
        link_id = match.group(1)

    ascii_title = (
        unicodedata.normalize("NFKD", title or "")
        .encode("ascii", "ignore")
        .decode("ascii")
        .lower()
    )
    title_slug = re.sub(r"[^a-z0-9]+", "-", ascii_title).strip("-")
    parts = ["wishket"]
    if link_id:
        parts.append(link_id)
    if title_slug:
        parts.append(title_slug[:48].strip("-"))
    slug = "-".join(p for p in parts if p)
    slug = re.sub(r"-{2,}", "-", slug).strip("-")
    return slug or fallback


def normalize_payload(data: dict[str, Any]) -> dict[str, Any]:
    project_title = str(data.get("project_title") or data.get("title") or "").strip()
    link = str(data.get("url") or data.get("link") or "").strip()
    slug = str(data.get("project_slug") or "").strip()
    if not re.fullmatch(r"[a-z0-9-]+", slug or ""):
        slug = safe_slug(project_title, link)
    raw_actions = data.get("requested_actions") or REQUESTED_ACTIONS
    if isinstance(raw_actions, str):
        raw_actions = [raw_actions]
    requested_actions = [str(a).strip() for a in raw_actions if str(a).strip()]
    actions = split_actions(requested_actions)

    return {
        "type": REQUEST_TYPE,
        "request_id": str(data.get("request_id") or _uuid_mod.uuid4()),
        "source": data.get("source") or "wishket_dashboard",
        "project_title": project_title or slug,
        "project_slug": slug,
        "summary": str(data.get("summary") or data.get("description") or "").strip(),
        "budget": str(data.get("budget") or "").strip(),
        "deadline": str(data.get("deadline") or "").strip(),
        "url": link,
        "requested_actions": requested_actions,
        "immediate_actions": actions["immediate"],
        "approval_required_actions": actions["approval_required"],
        "approval_required": bool(actions["approval_required"]),
        "created_at": data.get("created_at") or _iso(),
    }


def target_dir_for(slug: str) -> Path:
    if not re.fullmatch(r"[a-z0-9-]+", slug):
        raise ValueError(f"unsafe project_slug: {slug!r}")
    target = DEV_ROOT / slug
    resolved_base = DEV_ROOT.resolve(strict=False)
    resolved_target = target.resolve(strict=False)
    if resolved_base != resolved_target and resolved_base not in resolved_target.parents:
        raise ValueError(f"target escapes dev root: {target}")
    return target


def build_plan(payload: dict[str, Any]) -> dict[str, Any]:
    target = target_dir_for(payload["project_slug"])
    return {
        "mode": "dry_run",
        "payload": payload,
        "local_project": {
            "root": str(DEV_ROOT),
            "target": str(target),
            "exists": target.exists(),
            "will_create": not target.exists(),
        },
        "github": {
            "repository_name": payload["project_slug"],
            "will_create_without_approval": False,
            "note": "GitHub repository creation requires explicit approval.",
        },
        "artifacts": [
            str(target / "README.md"),
            str(target / "docs" / "development-plan.md"),
            str(target / "docs" / "codex-review-plan.md"),
        ],
        "routing": {
            "implementation": "Claude Code",
            "review": "Codex",
            "worker_execution_requires_approval": True,
        },
    }


def render_plan_markdown(payload: dict[str, Any], plan: dict[str, Any]) -> str:
    immediate_actions = payload.get("immediate_actions") or []
    approval_actions = payload.get("approval_required_actions") or []
    approval_text = (
        "The approval-required actions above must be approved before execution."
        if approval_actions
        else "All actions are analysis-only. Approval is still required to proceed with any execution."
    )
    return f"""# Wishket Development Request

## Payload

```json
{json.dumps(payload, ensure_ascii=False, indent=2)}
```

## Dry-run Plan

- Local folder: `{plan["local_project"]["target"]}`
- Folder exists: `{plan["local_project"]["exists"]}`
- GitHub repo candidate: `{plan["github"]["repository_name"]}`
- Claude Code role: implementation after approval
- Codex role: independent review after Claude output
- Immediate actions: `{", ".join(immediate_actions) or "none"}`
- Approval-required actions: `{", ".join(approval_actions) or "none"}`

## Approval Gate

{approval_text}
"""


def queue_for_approval(payload: dict[str, Any]) -> Path:
    plan = build_plan(payload)
    PENDING_DIR.mkdir(parents=True, exist_ok=True)

    # Idempotency: same request_id must not produce duplicate pending files
    request_id = str(payload.get("request_id") or "")
    if request_id:
        for existing in PENDING_DIR.glob("*_wishket_development_request.md"):
            try:
                content = existing.read_text(encoding="utf-8")
                if f'"request_id": "{request_id}"' in content:
                    return existing
            except OSError:
                pass

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    rid_short = request_id[:8] if request_id else ts
    path = PENDING_DIR / f"{ts}_{payload['project_slug']}_{rid_short}_wishket_development_request.md"
    body = render_plan_markdown(payload, plan)
    # Wishket 개발요청은 내용과 무관하게 항상 사람 승인 필요
    frontmatter = {
        "type": REQUEST_TYPE,
        "source": payload["source"],
        "status": "pending_approval",
        "requires_approval": True,
        "queued_at": _iso(),
        "project_slug": payload["project_slug"],
        "approval_note": "All Wishket development requests require explicit approval before execution.",
    }
    fm_lines = ["---"] + [f"{k}: {json.dumps(v, ensure_ascii=False)}" for k, v in frontmatter.items()] + ["---", ""]
    path.write_text("\n".join(fm_lines) + body, encoding="utf-8")
    return path


def execute_local_creation(payload: dict[str, Any]) -> dict[str, Any]:
    plan = build_plan(payload)
    target = Path(plan["local_project"]["target"])
    if target.exists():
        raise FileExistsError(f"target already exists: {target}")

    docs = target / "docs"
    docs.mkdir(parents=True, exist_ok=False)
    (target / "README.md").write_text(
        f"# {payload['project_title']}\n\n"
        f"- Source: {payload['url']}\n"
        f"- Budget: {payload['budget']}\n"
        f"- Project slug: `{payload['project_slug']}`\n\n"
        f"## Summary\n\n{payload['summary'] or 'No summary provided.'}\n",
        encoding="utf-8",
    )
    (docs / "development-plan.md").write_text(
        "# Development Plan\n\n"
        "Owner: Claude Code\n\n"
        "1. Confirm requirements from Wishket request.\n"
        "2. Create implementation plan.\n"
        "3. Implement only after user/Bucky approval.\n",
        encoding="utf-8",
    )
    (docs / "codex-review-plan.md").write_text(
        "# Codex Review Plan\n\n"
        "Owner: Codex\n\n"
        "- Review Claude Code output independently.\n"
        "- Check security, data loss, routing role violations, and AI-slop.\n",
        encoding="utf-8",
    )
    return {"created": str(target), "artifacts": plan["artifacts"]}


def sample_payload() -> dict[str, Any]:
    return normalize_payload(
        {
            "project_title": "Python FastAPI AI Agent development",
            "summary": "Sample Wishket development request for dry-run verification.",
            "budget": "780만원",
            "url": "https://www.wishket.com/project/155301/",
        }
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Wishket development request dry-run and approval queue")
    parser.add_argument("--payload-json", help="JSON payload string")
    parser.add_argument("--payload-file", type=Path, help="JSON payload file")
    parser.add_argument("--sample", action="store_true", help="Use built-in sample payload")
    parser.add_argument("--queue", action="store_true", help="Write pending_approval request")
    parser.add_argument("--execute-local", action="store_true", help="Create local project folder and plan files")
    args = parser.parse_args()

    if args.sample:
        payload = sample_payload()
    elif args.payload_file:
        payload = normalize_payload(json.loads(args.payload_file.read_text(encoding="utf-8")))
    elif args.payload_json:
        payload = normalize_payload(json.loads(args.payload_json))
    else:
        parser.error("provide --sample, --payload-json, or --payload-file")

    if args.execute_local:
        print(json.dumps(execute_local_creation(payload), ensure_ascii=False, indent=2))
        return 0

    plan = build_plan(payload)
    if args.queue:
        queued = queue_for_approval(payload)
        plan["queued_for_approval"] = str(queued)
    print(json.dumps(plan, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
