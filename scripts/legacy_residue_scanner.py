#!/usr/bin/env python3
"""Scan current operating docs for legacy instruction residue.

This scanner is intentionally conservative. It ignores archive/log/history
folders and focuses on files that can still influence Bucky, Claude Code, or
Codex behavior.
"""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
VAULT = ROOT / "ObsidianVault"
DEFAULT_REPORT = VAULT / "00_System" / "LEGACY_RESIDUE_SCAN_2026-05-30.md"

SCAN_ROOTS = (
    VAULT / "00_System",
    VAULT / "03_Projects" / "agents",
    VAULT / "05_Frameworks" / "guides",
    VAULT / "06_Context_Packs",
    ROOT / "scripts",
)

EXCLUDED_PARTS = {
    ".git",
    ".obsidian",
    "09_Archive",
    "archive",
    "legacy-import",
    "migration-conflicts",
    "gdrive-root-files",
    "MIGRATION",
    "daily-plus",
    "07_Reports",
    "04_Wiki",
    "__pycache__",
    "node_modules",
}

FILE_SUFFIXES = {".md", ".py"}
ROOT_FILES = {"AGENTS.md", "CLAUDE.md"}
EXCLUDED_NAMES = {
    "HANDOFF_LOG.md",
    "HANDOFF_LOG_ARCHIVE.md",
    "LEGACY_INSTRUCTION_CANDIDATE_AUDIT_2026-05-30.md",
    "LEGACY_MIGRATION_APPLIED_2026-05-30.md",
    "LEGACY_RESIDUE_SCAN_2026-05-30.md",
    "GDRIVE_SCRIPT_CLASSIFICATION_2026-05-30.md",
    "migration_status.md",
    "migration-gap-report.md",
    "knowledge-gaps.md",
    "TASKS.md",
    "legal-node-cleanup-plan.md",
    "boris-phase2-plan.md",
    "boris-phase2-report.md",
    "agent_room_migrator.py",
    "four_folder_migration.py",
    "gdrive_agent_room_migrator.py",
    "migration_crosscheck.py",
    "legacy_residue_scanner.py",
}

PATTERNS = {
    # ~/.claude/CLAUDE.md (and its Windows form) is the current canonical
    # global instruction file under the two-layer structure, not legacy —
    # excluded here rather than matched-then-allowlisted.
    "legacy_path": re.compile(r"JH-SHARED|OBSIDIAN-SECOND|C:\\[^\n|`]*Obsidian Vault|G:\\[^\n|`]*Obsidian Vault|CLAUDE_MASTER", re.IGNORECASE),
    "authority_phrase": re.compile(r"source of truth|원본입니다|실제 운영 파일|먼저 읽는다|기준 정보|active root|current source", re.IGNORECASE),
    "write_or_sync": re.compile(r"git push|git pull|push\.sh|pull\.sh|동기화|sync", re.IGNORECASE),
}

ALLOW_CONTEXT = (
    "archive/reference-only",
    "reference-only",
    "reference only",
    "legacy reference",
    "legacy 참조",
    "참조로만",
    "superseded",
    "not the source of truth",
    "not current operating authority",
    "not active",
    "not the active",
    "not the instruction source",
    "do not use",
    "do not read",
    "do not hardcode",
    "do not create",
    "generated target",
    "current source",
    "current rule",
    "replaces the old",
    "retained only",
    "no longer",
    "not from this file",
    "not from",
    "archive-only",
    "direct-run prohibited",
    "approval required",
    "conditional",
    "09_archive",
    "legacy archive",
    "migrated_from",
    "promoted",
    "already covered",
    "patched",
    "legacy source",
    "old ",
    "as the default",
    "migration",
    "migrated",
    "canonical",
    "replacement",
    "instead",
    "scanner",
    "scan report",
    "agent-room-messages.jsonl",
    "레거시",
    "이관",
    "금지",
    "기본 실행 금지",
    "우선 참조",
)


@dataclass(frozen=True)
class Finding:
    severity: str
    pattern: str
    path: Path
    line_no: int
    line: str
    reason: str


def _is_excluded(path: Path) -> bool:
    rel_parts = set(path.relative_to(ROOT).parts)
    return bool(rel_parts & EXCLUDED_PARTS) or path.name in EXCLUDED_NAMES


def _iter_files() -> list[Path]:
    files: set[Path] = set()
    for root in SCAN_ROOTS:
        if not root.exists():
            continue
        if root.is_file():
            files.add(root)
            continue
        for path in root.rglob("*"):
            if not path.is_file() or _is_excluded(path):
                continue
            if path.suffix in FILE_SUFFIXES:
                files.add(path)
    for name in ROOT_FILES:
        path = ROOT / name
        if path.exists():
            files.add(path)
    return sorted(files)


def _allowed(line: str) -> bool:
    lowered = line.lower()
    return any(token.lower() in lowered for token in ALLOW_CONTEXT)


def _classify(pattern_name: str, line: str) -> tuple[str, str]:
    allowed = _allowed(line)
    has_legacy_path = bool(PATTERNS["legacy_path"].search(line))
    if pattern_name == "authority_phrase" and not has_legacy_path:
        return "ok", "current authority phrase without legacy path"
    if pattern_name == "authority_phrase" and not allowed:
        return "review", "authority phrase outside explicit superseded/archive context"
    if pattern_name == "legacy_path" and not allowed:
        return "review", "legacy path mention outside explicit archive/reference-only context"
    if pattern_name == "write_or_sync" and "JH-SHARED" in line and not allowed:
        return "review", "write/sync text may still point at legacy shared folder"
    return "ok", "explicitly marked as archived, superseded, or prohibited"


def scan() -> list[Finding]:
    findings: list[Finding] = []
    for path in _iter_files():
        try:
            text = path.read_text(encoding="utf-8-sig", errors="replace")
        except OSError:
            continue
        for idx, line in enumerate(text.splitlines(), start=1):
            stripped = line.strip()
            if not stripped:
                continue
            for pattern_name, regex in PATTERNS.items():
                if not regex.search(stripped):
                    continue
                severity, reason = _classify(pattern_name, stripped)
                findings.append(
                    Finding(
                        severity=severity,
                        pattern=pattern_name,
                        path=path,
                        line_no=idx,
                        line=stripped[:240],
                        reason=reason,
                    )
                )
    return findings


def write_report(findings: list[Finding], report_path: Path) -> None:
    review = [f for f in findings if f.severity == "review"]
    ok = [f for f in findings if f.severity == "ok"]
    lines = [
        "---",
        "type: legacy-residue-scan",
        f"created: {datetime.now().isoformat(timespec='seconds')}",
        "status: active",
        "---",
        "",
        "# Legacy Residue Scan",
        "",
        "Scope: current operating docs and runtime scripts only. Archive, historical reports, AgentBus archives, and daily-plus content are excluded.",
        "",
        f"- Review findings: {len(review)}",
        f"- Allowed archive/superseded mentions: {len(ok)}",
        "",
        "## Review Findings",
        "",
    ]
    if review:
        lines.extend(["| Severity | Pattern | File | Line | Reason | Text |", "|---|---|---|---:|---|---|"])
        for item in review:
            rel = item.path.relative_to(ROOT).as_posix()
            text = item.line.replace("|", "\\|")
            lines.append(f"| {item.severity} | {item.pattern} | `{rel}` | {item.line_no} | {item.reason} | {text} |")
    else:
        lines.append("No review findings in current operating scope.")

    lines.extend(["", "## Allowed Mentions", ""])
    if ok:
        lines.extend(["| Pattern | File | Line | Text |", "|---|---|---:|---|"])
        for item in ok[:120]:
            rel = item.path.relative_to(ROOT).as_posix()
            text = item.line.replace("|", "\\|")
            lines.append(f"| {item.pattern} | `{rel}` | {item.line_no} | {text} |")
        if len(ok) > 120:
            lines.append(f"| ... | ... | ... | {len(ok) - 120} additional allowed mentions omitted |")
    else:
        lines.append("No allowed legacy mentions found.")

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Scan current docs/scripts for legacy instruction residue.")
    parser.add_argument("--report", default=str(DEFAULT_REPORT), help="Markdown report path.")
    parser.add_argument("--fail-on-review", action="store_true", help="Exit 2 if review findings remain.")
    args = parser.parse_args()

    findings = scan()
    report_path = Path(args.report)
    write_report(findings, report_path)
    review_count = sum(1 for item in findings if item.severity == "review")
    ok_count = sum(1 for item in findings if item.severity == "ok")
    print(f"report={report_path}")
    print(f"review={review_count}")
    print(f"allowed={ok_count}")
    return 2 if args.fail_on_review and review_count else 0


if __name__ == "__main__":
    raise SystemExit(main())
