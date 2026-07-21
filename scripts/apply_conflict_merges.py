#!/usr/bin/env python3
"""Apply reviewed migration conflict additions to canonical notes.

Only rows marked merge-candidate or needs-merge are processed. The script does
not overwrite canonical content; it appends missing lines under a source-marked
section so the original note remains intact and reviewable.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
from datetime import datetime
from pathlib import Path


DEFAULT_ROOT = r"D:\ai프로젝트\obsidian-agent-brain-system"
DEFAULT_DATE = "2026-05-24"
MERGE_DECISIONS = {"merge-candidate", "needs-merge"}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def normalize(line: str) -> str:
    return line.strip()


def content_lines(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    lines = text.splitlines()
    if lines and lines[0].strip() == "---":
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                return lines[i + 1 :]
    return lines


def missing_lines(conflict: Path, canonical: Path) -> list[str]:
    canonical_norm = {normalize(line) for line in content_lines(canonical) if normalize(line)}
    missing: list[str] = []
    seen: set[str] = set()
    for line in content_lines(conflict):
        norm = normalize(line)
        if not norm or norm in {"---", "```"}:
            continue
        if norm in canonical_norm or norm in seen:
            continue
        missing.append(line.rstrip())
        seen.add(norm)
    return missing


def append_section(canonical: Path, conflict: Path, lines: list[str], date: str) -> bool:
    marker = f"<!-- migration-merge:{date}:{sha256(conflict)[:12]} -->"
    text = canonical.read_text(encoding="utf-8", errors="ignore")
    if marker in text:
        return False
    if not lines:
        return False
    section = [
        "",
        marker,
        f"## Legacy merge additions ({date})",
        "",
        f"Source: `{conflict}`",
        "",
        *lines,
        "",
        "<!-- migration-merge-end -->",
        "",
    ]
    canonical.write_text(text.rstrip() + "\n" + "\n".join(section), encoding="utf-8")
    return True


def write_report(report_path: Path, rows: list[dict[str, str]], created: str) -> None:
    counts: dict[str, int] = {}
    for row in rows:
        counts[row["status"]] = counts.get(row["status"], 0) + 1

    lines = [
        "---",
        "type: conflict-merge-report",
        "scope: four-folder-migration",
        f"created: {created}",
        "status: applied",
        "---",
        "",
        "# Conflict Merge Apply Report",
        "",
        "## Counts",
        "",
        "| Status | Count |",
        "|---|---:|",
    ]
    for status in sorted(counts):
        lines.append(f"| {status} | {counts[status]} |")

    lines.extend(["", "## Applied Files", ""])
    for row in rows:
        lines.append(
            f"- `{row['status']}` / {row['added_lines']} lines :: "
            f"`{row['canonical']}` <- `{row['conflict']}`"
        )
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=DEFAULT_ROOT)
    parser.add_argument("--date", default=DEFAULT_DATE)
    args = parser.parse_args()

    repo = Path(args.root)
    run_dir = repo / "ObsidianVault" / "00_UPGRADE" / "migration-runs" / args.date
    resolution_csv = run_dir / "conflict-resolution.csv"
    apply_csv = run_dir / "conflict-merge-apply.csv"
    apply_report = run_dir / "conflict-merge-apply.md"
    created = datetime.now().isoformat(timespec="seconds")

    rows: list[dict[str, str]] = []
    with resolution_csv.open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            if row["decision"] not in MERGE_DECISIONS:
                continue
            conflict = Path(row["conflict"])
            canonical = Path(row["canonical"])
            lines = missing_lines(conflict, canonical)
            changed = append_section(canonical, conflict, lines, args.date)
            rows.append(
                {
                    "decision": row["decision"],
                    "status": "applied" if changed else "skipped",
                    "added_lines": str(len(lines) if changed else 0),
                    "conflict": str(conflict),
                    "canonical": str(canonical),
                }
            )

    with apply_csv.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["decision", "status", "added_lines", "conflict", "canonical"],
        )
        writer.writeheader()
        writer.writerows(rows)

    write_report(apply_report, rows, created)
    print({"csv": str(apply_csv), "report": str(apply_report), "rows": len(rows)})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
