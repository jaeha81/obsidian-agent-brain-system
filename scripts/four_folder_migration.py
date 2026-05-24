#!/usr/bin/env python3
"""Migrate selected legacy JH folders into the Obsidian Agent Brain vault.

The script is intentionally conservative:
- never deletes or moves source files
- never copies secrets, Git folders, Obsidian local settings, caches, or logs
- skips exact duplicates already present in the destination vault
- quarantines same-filename/different-content Markdown conflicts
- writes manifests so Bucky/Codex/Claude can review what happened
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


DEFAULT_SOURCES = [
    r"G:\내 드라이브\JH-Agent-Room",
    r"G:\내 드라이브\Obsidian",
    r"G:\내 드라이브\Obsidian Vault",
    r"G:\내 드라이브\OBSIDIAN-SECOND",
]

DEFAULT_ROOT = r"G:\내 드라이브\obsidian-agent-brain-system"

EXCLUDE_DIRS = {
    ".git",
    ".obsidian",
    ".claude",
    ".trash",
    "__pycache__",
    "node_modules",
    "dist",
    "build",
    "out",
    ".next",
    ".nuxt",
    ".cache",
    "coverage",
    "logs",
    "graphify-out",
}

SECRET_NAMES = {
    ".env",
    "token.txt",
}

EXCLUDE_SUFFIXES = {
    ".log",
    ".err",
    ".tmp",
    ".pyc",
    ".pem",
    ".key",
    ".crt",
    ".zip",
    ".tar",
    ".gz",
    ".7z",
    ".rar",
}


@dataclass(frozen=True)
class Decision:
    action: str
    reason: str
    target: Path | None


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def is_excluded(path: Path) -> str | None:
    name = path.name.lower()
    if name in SECRET_NAMES or name.startswith(".env."):
        return "secret-name"
    if any(part.lower() in EXCLUDE_DIRS for part in path.parts):
        return "excluded-dir"
    if path.suffix.lower() in EXCLUDE_SUFFIXES:
        return "excluded-suffix"
    if "secret" in name or "credential" in name:
        return "secret-like-name"
    return None


def source_slug(root: Path) -> str:
    name = root.name.strip()
    if name.lower() == "obsidian":
        return "Obsidian-wrapper"
    return "".join(ch if ch.isalnum() or ch in ("-", "_") else "-" for ch in name)


def bucket_for(root: Path, rel: Path, vault: Path) -> Path:
    slug = source_slug(root)
    first = rel.parts[0].lower() if rel.parts else ""
    suffix = Path(slug) / rel

    if slug == "JH-Agent-Room":
        return vault / "03_Projects" / "agents" / "agent-room" / "legacy-import" / rel
    if first in {"wiki"}:
        return vault / "04_Wiki" / "JH" / "legacy-import" / suffix
    if "prompt" in first or "playbook" in rel.name.lower():
        return vault / "05_Frameworks" / "legacy-import" / suffix
    if first in {"00_inbox", "raw"}:
        return vault / "01_RAW" / "legacy-import" / suffix
    if "daily" in first or "log" in first or "archive" in first or "sessions" in first:
        return vault / "09_Archive" / "legacy-import" / suffix
    if first in {"infranodus", "output"}:
        return vault / "07_Reports" / "legacy-import" / suffix
    return vault / "01_RAW" / "legacy-import" / suffix


def build_destination_index(vault: Path) -> tuple[set[str], dict[str, set[str]]]:
    hashes: set[str] = set()
    names: dict[str, set[str]] = {}
    for f in vault.rglob("*"):
        if not f.is_file():
            continue
        if is_excluded(f):
            continue
        try:
            digest = sha256(f)
        except OSError:
            continue
        hashes.add(digest)
        if f.suffix.lower() == ".md":
            names.setdefault(f.name.lower(), set()).add(digest)
    return hashes, names


def decide(
    src_root: Path,
    src_file: Path,
    vault: Path,
    dest_hashes: set[str],
    dest_md_names: dict[str, set[str]],
    conflict_root: Path,
) -> tuple[Decision, str]:
    excluded = is_excluded(src_file)
    if excluded:
        return Decision("excluded", excluded, None), ""

    digest = sha256(src_file)
    if digest in dest_hashes:
        return Decision("skipped", "exact-duplicate", None), digest

    rel = src_file.relative_to(src_root)
    if src_file.suffix.lower() == ".md":
        variants = dest_md_names.get(src_file.name.lower(), set())
        if variants and digest not in variants:
            target = conflict_root / source_slug(src_root) / rel
            return Decision("conflict", "same-md-name-different-hash", target), digest

    target = bucket_for(src_root, rel, vault)
    return Decision("copied", "safe-import", target), digest


def copy_file(src: Path, target: Path, dry_run: bool) -> None:
    if dry_run:
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        stem = target.stem
        suffix = target.suffix
        target = target.with_name(f"{stem}__imported{suffix}")
    shutil.copy2(src, target)


def write_markdown_summary(path: Path, rows: list[dict[str, str]], created: str) -> None:
    counts: dict[str, int] = {}
    for row in rows:
        counts[row["action"]] = counts.get(row["action"], 0) + 1

    conflict_rows = [r for r in rows if r["action"] == "conflict"]
    copied_rows = [r for r in rows if r["action"] == "copied"]

    lines = [
        "---",
        "type: migration-summary",
        "scope: four-folder-import",
        f"created: {created}",
        "status: imported-with-review-queue",
        "---",
        "",
        "# Four Folder Migration Summary",
        "",
        "## Counts",
        "",
        "| Action | Count |",
        "|---|---:|",
    ]
    for action in sorted(counts):
        lines.append(f"| {action} | {counts[action]} |")

    lines.extend(
        [
            "",
            "## Review Required",
            "",
            "Conflicts were copied to `ObsidianVault/09_Archive/migration-conflicts/2026-05-24/` for manual review. No source files were moved or deleted.",
            "",
            "## Copied Buckets",
            "",
        ]
    )

    bucket_counts: dict[str, int] = {}
    for row in copied_rows:
        target = row.get("target", "")
        parts = Path(target).parts
        bucket = "/".join(parts[-6:-4]) if len(parts) >= 6 else target
        bucket_counts[bucket] = bucket_counts.get(bucket, 0) + 1
    for bucket in sorted(bucket_counts):
        lines.append(f"- `{bucket}`: {bucket_counts[bucket]}")

    lines.extend(["", "## Conflict Samples", ""])
    for row in conflict_rows[:50]:
        lines.append(f"- `{row['source']}` -> `{row['target']}`")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=DEFAULT_ROOT)
    parser.add_argument("--date", default="2026-05-24")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    repo = Path(args.root)
    vault = repo / "ObsidianVault"
    out_dir = vault / "00_UPGRADE" / "migration-runs" / args.date
    conflict_root = vault / "09_Archive" / "migration-conflicts" / args.date
    created = datetime.now().isoformat(timespec="seconds")

    out_dir.mkdir(parents=True, exist_ok=True)
    dest_hashes, dest_md_names = build_destination_index(vault)

    rows: list[dict[str, str]] = []
    for root_text in DEFAULT_SOURCES:
        src_root = Path(root_text)
        if not src_root.exists():
            rows.append(
                {
                    "source_root": str(src_root),
                    "source": "",
                    "target": "",
                    "action": "missing-root",
                    "reason": "source-root-not-found",
                    "size": "0",
                    "sha256": "",
                }
            )
            continue
        for src_file in src_root.rglob("*"):
            if not src_file.is_file():
                continue
            decision, digest = decide(src_root, src_file, vault, dest_hashes, dest_md_names, conflict_root)
            if decision.target:
                copy_file(src_file, decision.target, args.dry_run)
            rows.append(
                {
                    "source_root": str(src_root),
                    "source": str(src_file),
                    "target": str(decision.target or ""),
                    "action": decision.action,
                    "reason": decision.reason,
                    "size": str(src_file.stat().st_size),
                    "sha256": digest,
                }
            )
            if decision.action in {"copied", "conflict"} and digest:
                dest_hashes.add(digest)

    manifest = out_dir / ("dry-run-manifest.csv" if args.dry_run else "manifest.csv")
    with manifest.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["source_root", "source", "target", "action", "reason", "size", "sha256"],
        )
        writer.writeheader()
        writer.writerows(rows)

    summary_path = out_dir / ("dry-run-summary.md" if args.dry_run else "summary.md")
    write_markdown_summary(summary_path, rows, created)

    counts: dict[str, int] = {}
    for row in rows:
        counts[row["action"]] = counts.get(row["action"], 0) + 1
    print(json.dumps({"manifest": str(manifest), "summary": str(summary_path), "counts": counts}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
