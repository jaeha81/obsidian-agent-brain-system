#!/usr/bin/env python3
"""Classify and organize four-folder migration Markdown conflicts.

This does not delete conflict files or overwrite canonical notes. It writes:
- conflict-resolution.csv
- conflict-resolution.md
- organized/<decision>/ copies for easier review
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


DEFAULT_ROOT = r"G:\내 드라이브\obsidian-agent-brain-system"
DEFAULT_DATE = "2026-05-24"

SKIP_PARTS = {
    ".git",
    ".obsidian",
    "graphify-out",
    "migration-conflicts",
    "migration-runs",
}

CANONICAL_HINTS = (
    "04_Wiki",
    "03_Projects",
    "05_Frameworks",
    "07_Reports",
    "09_Archive",
    "01_RAW",
)


@dataclass
class Resolution:
    conflict: Path
    canonical: Path | None
    decision: str
    reason: str
    conflict_lines: int
    canonical_lines: int
    similarity: float


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def normalized_lines(text: str) -> set[str]:
    lines = set()
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line in {"---", "```"}:
            continue
        lines.add(line)
    return lines


def path_score(path: Path) -> int:
    text = str(path)
    score = 0
    for index, hint in enumerate(CANONICAL_HINTS):
        if hint in text:
            score += 100 - index * 5
    if "legacy-import" in text:
        score -= 40
    if "09_Archive" in text:
        score -= 10
    return score


def build_name_index(vault: Path, conflict_root: Path) -> dict[str, list[Path]]:
    index: dict[str, list[Path]] = {}
    for p in vault.rglob("*.md"):
        if not p.is_file():
            continue
        if conflict_root in p.parents:
            continue
        if any(part in SKIP_PARTS for part in p.parts):
            continue
        index.setdefault(p.name.lower(), []).append(p)
    for paths in index.values():
        paths.sort(key=path_score, reverse=True)
    return index


def choose_resolution(conflict: Path, candidates: list[Path]) -> Resolution:
    conflict_text = read_text(conflict)
    conflict_set = normalized_lines(conflict_text)
    conflict_hash = sha256(conflict)

    if not candidates:
        return Resolution(conflict, None, "preserve-legacy", "no-canonical-same-name", len(conflict_set), 0, 0.0)

    best: tuple[float, Path, set[str], str] | None = None
    for candidate in candidates:
        candidate_text = read_text(candidate)
        candidate_set = normalized_lines(candidate_text)
        union = conflict_set | candidate_set
        similarity = len(conflict_set & candidate_set) / len(union) if union else 1.0
        reason = "same-name"
        if conflict_hash == sha256(candidate):
            similarity = 1.0
            reason = "same-hash"
        item = (similarity + path_score(candidate) / 1000.0, candidate, candidate_set, reason)
        if best is None or item[0] > best[0]:
            best = item

    assert best is not None
    _, canonical, canonical_set, base_reason = best
    union = conflict_set | canonical_set
    similarity = len(conflict_set & canonical_set) / len(union) if union else 1.0

    if base_reason == "same-hash":
        return Resolution(conflict, canonical, "superseded", "same-hash-existing-note", len(conflict_set), len(canonical_set), similarity)
    if conflict_set and conflict_set <= canonical_set:
        return Resolution(conflict, canonical, "superseded", "canonical-contains-conflict-lines", len(conflict_set), len(canonical_set), similarity)
    if canonical_set and canonical_set <= conflict_set:
        return Resolution(conflict, canonical, "merge-candidate", "conflict-contains-canonical-lines", len(conflict_set), len(canonical_set), similarity)
    if similarity >= 0.82:
        return Resolution(conflict, canonical, "merge-candidate", "high-similarity-different-content", len(conflict_set), len(canonical_set), similarity)
    if similarity >= 0.35:
        return Resolution(conflict, canonical, "needs-merge", "partial-overlap", len(conflict_set), len(canonical_set), similarity)
    return Resolution(conflict, canonical, "preserve-legacy", "low-overlap-legacy-note", len(conflict_set), len(canonical_set), similarity)


def safe_copy_to_bucket(resolution: Resolution, organized_root: Path, conflict_root: Path) -> Path:
    rel = resolution.conflict.relative_to(conflict_root)
    target = organized_root / resolution.decision / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(resolution.conflict, target)
    return target


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "decision",
                "reason",
                "similarity",
                "conflict_lines",
                "canonical_lines",
                "conflict",
                "canonical",
                "organized_copy",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)


def write_report(path: Path, rows: list[dict[str, str]], created: str) -> None:
    counts: dict[str, int] = {}
    for row in rows:
        counts[row["decision"]] = counts.get(row["decision"], 0) + 1

    lines = [
        "---",
        "type: conflict-resolution",
        "scope: four-folder-migration",
        f"created: {created}",
        "status: classified",
        "---",
        "",
        "# Migration Conflict Resolution",
        "",
        "## Counts",
        "",
        "| Decision | Count | Meaning |",
        "|---|---:|---|",
    ]
    meanings = {
        "superseded": "Existing canonical note already covers the conflict file.",
        "merge-candidate": "Conflict file likely has newer/additional lines; merge carefully.",
        "needs-merge": "Partial overlap; manual content merge required.",
        "preserve-legacy": "Low overlap or no canonical note; keep as legacy archive unless promoted later.",
    }
    for decision in sorted(counts):
        lines.append(f"| {decision} | {counts[decision]} | {meanings.get(decision, '')} |")

    lines.extend(
        [
            "",
            "## Operating Rule",
            "",
            "No canonical note was overwritten. Files were copied into `organized/<decision>/` to make review easier.",
            "",
            "## All 134 Files",
            "",
        ]
    )

    for row in rows:
        canonical = row["canonical"] or "(none)"
        lines.append(
            f"- `{row['decision']}` / {row['reason']} / sim {row['similarity']} "
            f":: `{row['conflict']}` -> `{canonical}`"
        )

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=DEFAULT_ROOT)
    parser.add_argument("--date", default=DEFAULT_DATE)
    args = parser.parse_args()

    repo = Path(args.root)
    vault = repo / "ObsidianVault"
    conflict_root = vault / "09_Archive" / "migration-conflicts" / args.date
    organized_root = conflict_root / "_organized"
    out_dir = vault / "00_UPGRADE" / "migration-runs" / args.date
    created = datetime.now().isoformat(timespec="seconds")

    index = build_name_index(vault, conflict_root)
    resolutions: list[Resolution] = []
    for conflict in sorted(conflict_root.rglob("*.md")):
        if "_organized" in conflict.parts:
            continue
        candidates = index.get(conflict.name.lower(), [])
        resolutions.append(choose_resolution(conflict, candidates))

    rows: list[dict[str, str]] = []
    for resolution in resolutions:
        organized_copy = safe_copy_to_bucket(resolution, organized_root, conflict_root)
        rows.append(
            {
                "decision": resolution.decision,
                "reason": resolution.reason,
                "similarity": f"{resolution.similarity:.3f}",
                "conflict_lines": str(resolution.conflict_lines),
                "canonical_lines": str(resolution.canonical_lines),
                "conflict": str(resolution.conflict),
                "canonical": str(resolution.canonical or ""),
                "organized_copy": str(organized_copy),
            }
        )

    csv_path = out_dir / "conflict-resolution.csv"
    report_path = out_dir / "conflict-resolution.md"
    write_csv(csv_path, rows)
    write_report(report_path, rows, created)

    counts: dict[str, int] = {}
    for row in rows:
        counts[row["decision"]] = counts.get(row["decision"], 0) + 1
    print({"csv": str(csv_path), "report": str(report_path), "counts": counts})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
