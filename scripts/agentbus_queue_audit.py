#!/usr/bin/env python3
"""Read-only AgentBus queue audit."""

from __future__ import annotations

import argparse
import csv
import json
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_AGENTBUS = ROOT / "ObsidianVault" / "10_AgentBus"
QUEUE_DIRS = (
    "inbox",
    "outbox/Bucky",
    "outbox/Codex",
    "completed",
    "failed",
    "handoffs",
    "awareness",
    "tasks",
)


def _files(path: Path) -> list[Path]:
    if not path.exists():
        return []
    return [p for p in path.iterdir() if p.is_file()]


def _queue_summary(path: Path) -> dict:
    files = sorted(_files(path), key=lambda p: p.stat().st_mtime, reverse=True)
    return {
        "path": str(path),
        "exists": path.exists(),
        "count": len(files),
        "recent": [p.name for p in files[:5]],
    }


def audit_agentbus(agentbus: Path = DEFAULT_AGENTBUS, *, inbox_attention_threshold: int = 100) -> dict:
    queues = {name: _queue_summary(agentbus / name) for name in QUEUE_DIRS}
    total = sum(item["count"] for item in queues.values())
    warnings: list[str] = []

    if queues["inbox"]["count"] > inbox_attention_threshold:
        warnings.append("inbox_over_threshold")
    if queues["failed"]["count"] > 0:
        warnings.append("failed_items_present")
    if not agentbus.exists():
        warnings.append("agentbus_missing")

    return {
        "agentbus": str(agentbus),
        "queues": queues,
        "total_files": total,
        "warnings": warnings,
        "runtime_risk": "warning" if warnings else "none",
        "next_action": "triage warnings before legacy absorption" if warnings else "safe to continue",
    }


def _decision_for(queue: str, age_days: int, active_days: int) -> str:
    if queue == "failed":
        return "failed_review"
    if queue == "completed":
        return "historical_completed"
    if queue.startswith("outbox/"):
        return "outbox_review"
    if queue == "inbox":
        return "active_candidate" if age_days <= active_days else "historical_residue"
    if queue in {"handoffs", "awareness", "tasks"}:
        return "system_record"
    return "review_needed"


def build_triage_manifest(
    agentbus: Path = DEFAULT_AGENTBUS,
    *,
    now: float | None = None,
    active_days: int = 3,
) -> list[dict]:
    current = time.time() if now is None else now
    entries: list[dict] = []
    for queue in QUEUE_DIRS:
        queue_path = agentbus / queue
        for path in sorted(_files(queue_path), key=lambda p: p.stat().st_mtime, reverse=True):
            age_days = max(0, int((current - path.stat().st_mtime) // 86400))
            entries.append({
                "queue": queue,
                "name": path.name,
                "decision": _decision_for(queue, age_days, active_days),
                "age_days": age_days,
                "path": str(path),
            })
    return entries


def write_triage_manifest_csv(entries: list[dict], output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["queue", "name", "decision", "age_days", "path"]
    with output_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(entries)
    return output_path


def format_text(report: dict) -> str:
    lines = ["[AgentBus Queue Audit]", f"AgentBus: {report['agentbus']}"]
    for name, item in report["queues"].items():
        lines.append(f"- {name}: {item['count']} files")
    warnings = ", ".join(report["warnings"]) if report["warnings"] else "none"
    lines.extend([
        f"Total files: {report['total_files']}",
        f"Runtime risk: {report['runtime_risk']}",
        f"Warnings: {warnings}",
        f"Next action: {report['next_action']}",
    ])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit AgentBus queue counts without modifying files.")
    parser.add_argument("--agentbus", type=Path, default=DEFAULT_AGENTBUS)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--manifest", type=Path, help="Write non-destructive triage manifest CSV.")
    parser.add_argument("--inbox-threshold", type=int, default=100)
    parser.add_argument("--active-days", type=int, default=3)
    args = parser.parse_args()

    report = audit_agentbus(args.agentbus, inbox_attention_threshold=args.inbox_threshold)
    if args.manifest:
        entries = build_triage_manifest(args.agentbus, active_days=args.active_days)
        write_triage_manifest_csv(entries, args.manifest)
        report["triage_manifest"] = str(args.manifest)
        report["triage_rows"] = len(entries)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(format_text(report))
    return 1 if report["runtime_risk"] == "warning" else 0


if __name__ == "__main__":
    raise SystemExit(main())
