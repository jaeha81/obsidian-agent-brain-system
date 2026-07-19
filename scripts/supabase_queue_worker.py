#!/usr/bin/env python3
"""Consume the Supabase agent_commands queue and run Codex reviews (Bucky control plane, branch B).

Pipeline: dashboard/Discord -> /api/agent-intake -> Supabase `agent_commands`(pending)
          -> THIS worker (home PC) claims -> runs Codex -> writes result back
          -> dashboard shows the review with PASS/FAIL buttons for the human verdict.

Codex execution logic is reused from codex_review_runner (single source of truth);
this file is only the queue adapter (fetch -> claim -> record).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

# Allow importing the sibling runner module regardless of CWD.
sys.path.insert(0, str(Path(__file__).parent))
import codex_review_runner as runner  # loads .env on import; reused execution logic

SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
AGENT = os.getenv("SUPABASE_QUEUE_AGENT", "codex").strip() or "codex"
INTERVAL = runner.env_int("SUPABASE_QUEUE_INTERVAL", 15)
BATCH = runner.env_int("SUPABASE_QUEUE_BATCH", 5)
TABLE = "agent_commands"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _headers(extra: dict | None = None) -> dict:
    h = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
    }
    if extra:
        h.update(extra)
    return h


def _http(method: str, url: str, *, data: dict | None = None, headers: dict | None = None, timeout: int = 30):
    raw = json.dumps(data).encode("utf-8") if data is not None else None
    req = urllib.request.Request(url, data=raw, method=method, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", "replace")


def fetch_pending(limit: int = BATCH) -> list[dict]:
    url = (
        f"{SUPABASE_URL}/rest/v1/{TABLE}"
        f"?agent=eq.{AGENT}&status=eq.pending&order=created_at.asc&limit={limit}"
    )
    status, text = _http("GET", url, headers=_headers())
    if status != 200:
        raise RuntimeError(f"fetch_pending {status}: {text[:300]}")
    return json.loads(text) if text.strip() else []


def claim(row_id: str) -> dict | None:
    """Atomically move pending -> reviewing. Returns the row, or None if already claimed."""
    url = f"{SUPABASE_URL}/rest/v1/{TABLE}?id=eq.{row_id}&status=eq.pending"
    body = {"status": "reviewing", "claimed_at": now_iso()}
    status, text = _http("PATCH", url, data=body, headers=_headers({"Prefer": "return=representation"}))
    if status not in (200, 204):
        raise RuntimeError(f"claim {status}: {text[:300]}")
    rows = json.loads(text) if text.strip() else []
    return rows[0] if rows else None


def record_result(row_id: str, review_text: str) -> None:
    """Store the review; leave status='reviewing' so the human decides PASS/FAIL on the dashboard."""
    url = f"{SUPABASE_URL}/rest/v1/{TABLE}?id=eq.{row_id}"
    body = {"result": review_text[:20000], "error": None}
    status, text = _http("PATCH", url, data=body, headers=_headers())
    if status not in (200, 204):
        raise RuntimeError(f"record_result {status}: {text[:300]}")


def record_failure(row_id: str, detail: str) -> None:
    url = f"{SUPABASE_URL}/rest/v1/{TABLE}?id=eq.{row_id}"
    body = {
        "status": "failed",
        "error": detail[:2000],
        "result": f"[worker error] {detail[:500]}",
        "completed_at": now_iso(),
    }
    status, text = _http("PATCH", url, data=body, headers=_headers())
    if status not in (200, 204):
        raise RuntimeError(f"record_failure {status}: {text[:300]}")


def process(row: dict) -> str:
    row_id = row["id"]
    content = (row.get("content") or row.get("title") or "").strip()
    if not content:
        record_failure(row_id, "empty content in queue row")
        return "failed"

    label = f"supabase:{TABLE}/{row_id}"
    prompt = runner.build_prompt(label, content)
    if len(prompt) > runner.MAX_PROMPT_CHARS:
        record_failure(
            row_id,
            f"prompt {len(prompt)} chars exceeds MAX_PROMPT_CHARS={runner.MAX_PROMPT_CHARS}; split request",
        )
        return "failed"

    fd, tmp_name = tempfile.mkstemp(suffix=".md")
    os.close(fd)  # Windows: close the mkstemp handle or unlink() below fails (WinError 32)
    tmp = Path(tmp_name)
    try:
        runner.run_codex(prompt, tmp)
        review = tmp.read_text(encoding="utf-8", errors="replace").strip()
        record_result(row_id, review or "[empty review returned by Codex]")
        return "reviewed"
    except Exception as exc:  # noqa: BLE001 - record any Codex/tool failure to the queue
        record_failure(row_id, str(exc))
        return "failed"
    finally:
        tmp.unlink(missing_ok=True)


def run_once(*, dry_run: bool = False, limit: int = BATCH) -> int:
    rows = fetch_pending(limit=limit)
    handled = 0
    for row in rows:
        if dry_run:
            print(f"DRY RUN: would review {row['id']} - {(row.get('title') or '')[:60]}")
            handled += 1
            continue
        claimed = claim(row["id"])
        if not claimed:
            continue  # another tick/worker already took it
        outcome = process(claimed)
        print(f"[{outcome}] {row['id']}")
        handled += 1
    return handled


def watch(*, dry_run: bool = False) -> None:
    print(f"[SupabaseQueueWorker] agent={AGENT} interval={INTERVAL}s table={TABLE}")
    while True:
        try:
            run_once(dry_run=dry_run)
        except Exception as exc:  # noqa: BLE001 - keep the loop alive on transient queue errors
            print(f"[warn] tick failed: {exc}")
        time.sleep(INTERVAL)


def require_config() -> None:
    if not SUPABASE_URL or not SUPABASE_KEY:
        print(
            "SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY missing in .env; cannot run.\n"
            "Add both to the project .env (same sb_secret_... key as in Vercel).",
            file=sys.stderr,
        )
        sys.exit(2)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Codex reviews from the Supabase agent_commands queue")
    parser.add_argument("--once", action="store_true", help="Process pending rows once and exit")
    parser.add_argument("--dry-run", action="store_true", help="List pending rows without claiming or running Codex")
    args = parser.parse_args()

    if os.getenv("SUPABASE_QUEUE_ENABLED", "1").strip().lower() in {"0", "false", "no"}:
        print("SUPABASE_QUEUE_ENABLED=0; exiting.")
        return

    require_config()

    if args.once:
        run_once(dry_run=args.dry_run)
    else:
        watch(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
