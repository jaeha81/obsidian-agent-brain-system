#!/usr/bin/env python3
"""Inventory legacy instruction-like sources for Bucky migration review.

This does not make archive material authoritative. It creates a reproducible
candidate list so Bucky can promote, mark covered, or keep archive-only.
"""

from __future__ import annotations

import argparse
import fnmatch
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
VAULT = ROOT / "ObsidianVault"
DEFAULT_REPORT = VAULT / "00_System" / "LEGACY_INSTRUCTION_INVENTORY_2026-05-30.md"
AUDIT = VAULT / "00_System" / "LEGACY_INSTRUCTION_CANDIDATE_AUDIT_2026-05-30.md"

SCAN_ROOTS = (
    VAULT / "09_Archive",
    VAULT / "03_Knowledge" / "bridges",
    VAULT / "03_Knowledge" / "hubs",
    VAULT / "03_Projects" / "github-repos",
)

EXCLUDED_PARTS = {
    ".git",
    ".obsidian",
    "__pycache__",
    "node_modules",
}

TEXT_SUFFIXES = {".md", ".txt", ".json", ".jsonl", ".yaml", ".yml"}
MAX_READ_CHARS = 12000

NAME_PATTERNS = {
    "agent": re.compile(r"agent|bucky|claude|codex|sub-agent|worker|dispatcher", re.IGNORECASE),
    "instruction": re.compile(r"instruction|guide|protocol|rule|policy|playbook|workflow|onboarding|role|template", re.IGNORECASE),
    "memory": re.compile(r"memory|memories|preference|pattern|error|context", re.IGNORECASE),
    "sync": re.compile(r"sync|handoff|session|daily|report|queue|agentbus", re.IGNORECASE),
}

CONTENT_PATTERNS = {
    "must_rule": re.compile(r"\bmust\b|\bmust not\b|do not|never|always|필수|금지|반드시|하지 않는다"),
    "approval": re.compile(r"approval|required|승인|commit|push|delete|move|archive|reset"),
    "role": re.compile(r"Claude|Codex|Bucky|AgentBus|agent|역할|검수|구현"),
    "context": re.compile(r"context|packet|vault|Obsidian|지침|컨텍스트|패킷"),
}

SECRET_HINTS = re.compile(
    r"(sk-[A-Za-z0-9_-]{12,}|api[_-]?key|secret|password|token|webhook)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class Candidate:
    path: Path
    score: int
    reasons: tuple[str, ...]
    secret_hint: bool
    covered_hint: bool
    excerpt: str


def _is_excluded(path: Path) -> bool:
    rel_parts = set(path.relative_to(ROOT).parts)
    return bool(rel_parts & EXCLUDED_PARTS)


def _iter_files() -> list[Path]:
    files: list[Path] = []
    for root in SCAN_ROOTS:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file() or _is_excluded(path):
                continue
            if path.suffix.lower() in TEXT_SUFFIXES:
                files.append(path)
    return sorted(files)


def _read_excerpt(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8-sig", errors="replace")[:MAX_READ_CHARS]
    except OSError:
        return ""


def _audit_text() -> str:
    if not AUDIT.exists():
        return ""
    try:
        return AUDIT.read_text(encoding="utf-8-sig", errors="replace")
    except OSError:
        return ""


def _covered_by_audit(path: Path, audit_text: str) -> bool:
    rel = path.relative_to(ROOT).as_posix()
    name = path.name
    if rel in audit_text or name in audit_text:
        return True
    for pattern in re.findall(r"`([^`]*\*[^`]*)`", audit_text):
        if fnmatch.fnmatch(rel, pattern):
            return True
    return False


def classify(path: Path, audit_text: str) -> Candidate | None:
    rel = path.relative_to(ROOT).as_posix()
    text = _read_excerpt(path)
    haystack = f"{rel}\n{text}"
    reasons: list[str] = []
    score = 0

    for key, regex in NAME_PATTERNS.items():
        if regex.search(rel):
            score += 3
            reasons.append(f"name:{key}")

    for key, regex in CONTENT_PATTERNS.items():
        if regex.search(text):
            score += 2
            reasons.append(f"content:{key}")

    if "migration-conflicts" in rel or "legacy-import" in rel:
        score += 1
        reasons.append("source:legacy-import")

    if score < 4:
        return None

    secret_hint = bool(SECRET_HINTS.search(text) or SECRET_HINTS.search(path.name))
    if secret_hint:
        reasons.append("secret-hint")

    covered = _covered_by_audit(path, audit_text)
    if covered:
        reasons.append("audit-mentioned")

    first_lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped:
            first_lines.append(stripped)
        if len(first_lines) >= 3:
            break
    excerpt = " / ".join(first_lines)[:220]

    return Candidate(
        path=path,
        score=score,
        reasons=tuple(reasons),
        secret_hint=secret_hint,
        covered_hint=covered,
        excerpt=excerpt,
    )


def inventory() -> list[Candidate]:
    audit_text = _audit_text()
    candidates = []
    for path in _iter_files():
        candidate = classify(path, audit_text)
        if candidate:
            candidates.append(candidate)
    return sorted(candidates, key=lambda c: (-c.score, str(c.path).lower()))


def _status(candidate: Candidate) -> str:
    if candidate.secret_hint:
        if candidate.covered_hint:
            return "secret-audit-mentioned"
        return "secret-review-before-read"
    if candidate.covered_hint:
        return "audit-mentioned"
    if candidate.score >= 12:
        return "high-priority-review"
    return "candidate-review"


def write_report(candidates: list[Candidate], report_path: Path) -> None:
    counts: dict[str, int] = {}
    for item in candidates:
        counts[_status(item)] = counts.get(_status(item), 0) + 1

    lines = [
        "---",
        "type: legacy-instruction-inventory",
        f"created: {datetime.now().isoformat(timespec='seconds')}",
        "status: active",
        "owner: Bucky",
        "---",
        "",
        "# Legacy Instruction Inventory",
        "",
        "Scope: archive/import and bridge/hub sources that look instruction-like. This report does not make those sources authoritative.",
        "",
        f"- Candidates: {len(candidates)}",
    ]
    for status, count in sorted(counts.items()):
        lines.append(f"- {status}: {count}")

    lines.extend(
        [
            "",
            "## Handling Rules",
            "",
            "1. Secret-review-before-read candidates must not be opened broadly or copied into Context Packs before manual redaction.",
            "2. Secret-audit-mentioned candidates are already tracked, but still require redaction discipline if reopened.",
            "3. Audit-mentioned candidates are already tracked; update the audit if their status changes.",
            "4. High-priority candidates need a promote / covered / archive-only decision.",
            "5. Archive paths remain reference-only unless a current Bucky packet promotes a compressed rule.",
            "",
            "## Candidates",
            "",
            "| Status | Score | Path | Reasons | Excerpt |",
            "|---|---:|---|---|---|",
        ]
    )

    for item in candidates:
        rel = item.path.relative_to(ROOT).as_posix()
        reasons = ", ".join(item.reasons)
        excerpt = item.excerpt.replace("|", "\\|")
        lines.append(f"| {_status(item)} | {item.score} | `{rel}` | {reasons} | {excerpt} |")

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Inventory legacy instruction-like sources.")
    parser.add_argument("--report", default=str(DEFAULT_REPORT))
    parser.add_argument("--fail-on-high-priority", action="store_true")
    args = parser.parse_args()

    candidates = inventory()
    write_report(candidates, Path(args.report))
    high = sum(1 for item in candidates if _status(item) == "high-priority-review")
    secret = sum(1 for item in candidates if _status(item) == "secret-review-before-read")
    secret_covered = sum(1 for item in candidates if _status(item) == "secret-audit-mentioned")
    print(f"report={args.report}")
    print(f"candidates={len(candidates)}")
    print(f"high_priority={high}")
    print(f"secret_review={secret}")
    print(f"secret_audit_mentioned={secret_covered}")
    if args.fail_on_high_priority and high:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
