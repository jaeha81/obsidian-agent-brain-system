#!/usr/bin/env python3
"""Create a value-free manifest for secret-like legacy instruction candidates."""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import legacy_instruction_inventory


ROOT = Path(__file__).resolve().parent.parent
VAULT = ROOT / "ObsidianVault"
DEFAULT_REPORT = VAULT / "00_System" / "LEGACY_SECRET_MANIFEST_2026-05-30.md"

PATTERNS = {
    "openai_key_shape": re.compile(r"sk-[A-Za-z0-9_-]{12,}", re.IGNORECASE),
    "api_key_word": re.compile(r"api[_-]?key", re.IGNORECASE),
    "secret_word": re.compile(r"\bsecret\b", re.IGNORECASE),
    "password_word": re.compile(r"password", re.IGNORECASE),
    "token_word": re.compile(r"token", re.IGNORECASE),
    "webhook_word": re.compile(r"webhook", re.IGNORECASE),
}


@dataclass(frozen=True)
class SecretEntry:
    path: Path
    status: str
    pattern_types: tuple[str, ...]
    line_numbers: tuple[int, ...]
    action: str


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8-sig", errors="replace")
    except OSError:
        return ""


def _scan_file(path: Path) -> tuple[tuple[str, ...], tuple[int, ...]]:
    text = _read_text(path)
    pattern_types: set[str] = set()
    line_numbers: set[int] = set()
    for line_no, line in enumerate(text.splitlines(), start=1):
        for name, regex in PATTERNS.items():
            if regex.search(line):
                pattern_types.add(name)
                line_numbers.add(line_no)
    return tuple(sorted(pattern_types)), tuple(sorted(line_numbers))


def build_manifest() -> list[SecretEntry]:
    entries: list[SecretEntry] = []
    for candidate in legacy_instruction_inventory.inventory():
        status = legacy_instruction_inventory._status(candidate)  # intentional shared classification
        if status not in {"secret-audit-mentioned", "secret-review-before-read"}:
            continue
        pattern_types, line_numbers = _scan_file(candidate.path)
        action = "quarantined; targeted redaction review required before promotion"
        if status == "secret-review-before-read":
            action = "untracked secret candidate; add audit decision before any read/promotion"
        entries.append(
            SecretEntry(
                path=candidate.path,
                status=status,
                pattern_types=pattern_types,
                line_numbers=line_numbers,
                action=action,
            )
        )
    return sorted(entries, key=lambda item: item.path.as_posix().lower())


def write_report(entries: list[SecretEntry], report_path: Path) -> None:
    status_counts: dict[str, int] = {}
    pattern_counts: dict[str, int] = {}
    for entry in entries:
        status_counts[entry.status] = status_counts.get(entry.status, 0) + 1
        for pattern_type in entry.pattern_types:
            pattern_counts[pattern_type] = pattern_counts.get(pattern_type, 0) + 1

    lines = [
        "---",
        "type: legacy-secret-manifest",
        f"created: {datetime.now().isoformat(timespec='seconds')}",
        "status: active",
        "owner: Bucky",
        "---",
        "",
        "# Legacy Secret Manifest",
        "",
        "This report intentionally omits secret values and line text. It records only paths, pattern classes, and line numbers.",
        "",
        f"- Secret-like candidates: {len(entries)}",
    ]
    for status, count in sorted(status_counts.items()):
        lines.append(f"- {status}: {count}")
    for pattern_type, count in sorted(pattern_counts.items()):
        lines.append(f"- pattern:{pattern_type}: {count}")

    lines.extend(
        [
            "",
            "## Handling",
            "",
            "1. Do not paste matched line text into chat or Context Packs.",
            "2. Open a listed file only for targeted redaction or rotation assessment.",
            "3. Promote compressed rules only after literal values/private examples are removed.",
            "4. Keep the archive path and final decision in the candidate audit.",
            "",
            "## Entries",
            "",
            "| Status | Path | Pattern classes | Lines | Action |",
            "|---|---|---|---|---|",
        ]
    )
    for entry in entries:
        rel = entry.path.relative_to(ROOT).as_posix()
        patterns = ", ".join(entry.pattern_types) if entry.pattern_types else "secret-hint"
        lines_text = ", ".join(str(line_no) for line_no in entry.line_numbers) if entry.line_numbers else "unknown"
        lines.append(f"| {entry.status} | `{rel}` | {patterns} | {lines_text} | {entry.action} |")

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a value-free manifest of secret-like legacy files.")
    parser.add_argument("--report", default=str(DEFAULT_REPORT))
    parser.add_argument("--fail-on-untracked", action="store_true")
    args = parser.parse_args()

    entries = build_manifest()
    write_report(entries, Path(args.report))
    untracked = sum(1 for entry in entries if entry.status == "secret-review-before-read")
    print(f"report={args.report}")
    print(f"secret_candidates={len(entries)}")
    print(f"secret_review_before_read={untracked}")
    print(f"secret_audit_mentioned={sum(1 for entry in entries if entry.status == 'secret-audit-mentioned')}")
    return 2 if args.fail_on_untracked and untracked else 0


if __name__ == "__main__":
    raise SystemExit(main())
