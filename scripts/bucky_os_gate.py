#!/usr/bin/env python3
"""Verify that Bucky is the active instruction operating layer."""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
VAULT = ROOT / "ObsidianVault"
DEFAULT_REPORT = VAULT / "00_System" / "BUCKY_OS_GATE_2026-05-30.md"

sys.path.insert(0, str(ROOT / "scripts"))

import context_pack_selector  # noqa: E402
import legacy_instruction_inventory  # noqa: E402
import legacy_residue_scanner  # noqa: E402
import legacy_secret_decision_register  # noqa: E402
import legacy_secret_manifest  # noqa: E402


REQUIRED_FILES = (
    ROOT / "AGENTS.md",
    ROOT / "CLAUDE.md",
    VAULT / "03_Projects" / "agents" / "bucky.md",
    VAULT / "00_System" / "ROUTING_RULES.md",
    VAULT / "00_System" / "BUCKY_OS_RUNBOOK.md",
    VAULT / "00_System" / "BUCKY_OS_COMPLETION_AUDIT_2026-05-30.md",
    VAULT / "00_System" / "BUCKY_OS_MIGRATION_NEXT_ACTIONS_2026-05-30.md",
    VAULT / "00_System" / "LEGACY_INSTRUCTION_CANDIDATE_AUDIT_2026-05-30.md",
    VAULT / "00_System" / "LEGACY_INSTRUCTION_INVENTORY_2026-05-30.md",
    VAULT / "00_System" / "LEGACY_RESIDUE_SCAN_2026-05-30.md",
    VAULT / "00_System" / "LEGACY_SECRET_REVIEW_POLICY_2026-05-30.md",
    VAULT / "00_System" / "LEGACY_SECRET_MANIFEST_2026-05-30.md",
    VAULT / "00_System" / "LEGACY_SECRET_DECISION_REGISTER_2026-05-30.md",
    VAULT / "06_Context_Packs" / "bucky-agent-os-legacy-rules.md",
    VAULT / "06_Context_Packs" / "bucky-context-efficiency-goal-mode.md",
    VAULT / "06_Context_Packs" / "bucky-user-communication-output-policy.md",
    VAULT / "06_Context_Packs" / "bucky-development-workflow-policy.md",
    VAULT / "06_Context_Packs" / "bucky-security-runtime-governance.md",
    VAULT / "06_Context_Packs" / "bucky-vault-ingestion-record-policy.md",
)

REQUIRED_TEXT = {
    ROOT / "AGENTS.md": (
        "Obsidian Agent Brain System is the instruction operating system",
        "context_pack_selector.py",
        "Use only Bucky-provided or Bucky-confirmed instructions",
    ),
    ROOT / "CLAUDE.md": (
        "Bucky is the orchestrator and instruction manager",
        "context_pack_selector.py --packet",
        "Do not reuse packets from another repo or folder",
    ),
    VAULT / "00_System" / "BUCKY_OS_RUNBOOK.md": (
        "bucky_os_gate: ok 19 checks",
        "New projects start with no project-specific instructions",
        "Archive material remains reference-only",
    ),
    VAULT / "00_System" / "BUCKY_OS_COMPLETION_AUDIT_2026-05-30.md": (
        "Claude Code can recognize the same operating model",
        "context_pack_selector.py is the activation switch",
        "Secret-like archive files remain quarantined",
    ),
    VAULT / "06_Context_Packs" / "bucky-user-communication-output-policy.md": (
        "single copyable block",
        "facts, risks, next actions",
        "targeted redaction pass",
    ),
    VAULT / "00_System" / "session-state.md": (
        "BUCKY_OS_RUNBOOK.md",
        "bucky_os_gate.py --fail-on-error",
        "new project packet rollout",
    ),
    VAULT / "00_System" / "AGENT_STATE.md": (
        "BUCKY_OS_RUNBOOK.md",
        "bucky_os_gate.py --fail-on-error",
        "new-project packet contract",
    ),
    VAULT / "00_System" / "BUCKY_CONTEXT.md": (
        "BUCKY_OS_RUNBOOK.md",
        "bucky_os_gate.py --fail-on-error",
        "bucky_os_gate: ok 19 checks",
    ),
}

SECRET_MANIFEST = VAULT / "00_System" / "LEGACY_SECRET_MANIFEST_2026-05-30.md"
SECRET_DECISION_REGISTER = VAULT / "00_System" / "LEGACY_SECRET_DECISION_REGISTER_2026-05-30.md"
MANIFEST_FORBIDDEN_PATTERNS = {
    "openai_key_shape": re.compile(r"sk-[A-Za-z0-9_-]{12,}", re.IGNORECASE),
    "webhook_url": re.compile(r"https?://[^\s|`]*(webhook|hooks)[^\s|`]*", re.IGNORECASE),
    "excerpt_column": re.compile(r"\|\s*(Excerpt|Text|Matched text|Line text)\s*\|", re.IGNORECASE),
}

ACTIVE_LEGACY_REFERENCE_ONLY = (
    VAULT / "03_Projects" / "agents" / "COMMON-PHILOSOPHY.md",
    VAULT / "03_Projects" / "agents" / "mneme.md",
    VAULT / "03_Projects" / "agents" / "rank-system.md",
    VAULT / "03_Projects" / "agents" / "evolution.md",
)


@dataclass(frozen=True)
class Check:
    name: str
    passed: bool
    detail: str


def _status_counts() -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in legacy_instruction_inventory.inventory():
        status = legacy_instruction_inventory._status(item)  # intentional gate use
        counts[status] = counts.get(status, 0) + 1
    return counts


def _selector_has(task: str, required: tuple[str, ...]) -> Check:
    selected = context_pack_selector.select_context_pack(task_type="gate", body=task)
    packs = set(selected["packs"])
    missing = [pack for pack in required if pack not in packs]
    return Check(
        name=f"selector:{selected['key']}",
        passed=not missing,
        detail="missing=" + ",".join(missing) if missing else "packs ok",
    )


def _manifest_value_free() -> Check:
    if not SECRET_MANIFEST.exists():
        return Check("secret-manifest-value-free", False, "manifest missing")
    text = SECRET_MANIFEST.read_text(encoding="utf-8-sig", errors="replace")
    findings = [name for name, regex in MANIFEST_FORBIDDEN_PATTERNS.items() if regex.search(text)]
    return Check(
        "secret-manifest-value-free",
        not findings,
        "no forbidden value/text patterns" if not findings else "found=" + ",".join(findings),
    )


def _secret_decision_register() -> Check:
    if not SECRET_DECISION_REGISTER.exists():
        return Check("secret-decision-register", False, "register missing")
    decisions = legacy_secret_decision_register.build_register()
    manifest_entries = legacy_secret_manifest.build_manifest()
    text = SECRET_DECISION_REGISTER.read_text(encoding="utf-8-sig", errors="replace")
    findings = [name for name, regex in MANIFEST_FORBIDDEN_PATTERNS.items() if regex.search(text)]
    pending = sum(1 for item in decisions if item.decision == "pending-targeted-redaction")
    accounted = len(decisions) == len(manifest_entries)
    passed = accounted and not findings and pending == 0
    detail = (
        f"candidates={len(decisions)}, manifest={len(manifest_entries)}, "
        f"pending_targeted_redaction={pending}, "
        f"value_free={'yes' if not findings else 'no:' + ','.join(findings)}"
    )
    return Check("secret-decision-register", passed, detail)


def _packet_contract() -> Check:
    project = r"D:\ai프로젝트\new-project"
    packet = context_pack_selector.build_instruction_packet(
        task_type="gate",
        body="Claude Code new project implementation",
        project=project,
    )
    constraints = "\n".join(packet.get("constraints", []))
    verification = "\n".join(packet.get("verification", []))
    missing: list[str] = []
    if packet.get("project") != project:
        missing.append("project")
    if "Use only the current project" not in packet.get("scope", ""):
        missing.append("scope")
    if "Do not reuse another repo/folder" not in constraints:
        missing.append("no-reuse")
    if "Do not open, quote, or promote secret-like legacy archive material" not in constraints:
        missing.append("secret-constraint")
    if "Run the narrow command or inspection" not in verification:
        missing.append("verification")
    if not packet.get("context_packs"):
        missing.append("context-packs")
    if "ObsidianVault/00_System/BUCKY_OS_RUNBOOK.md" not in packet.get("context_packs", []):
        missing.append("runbook")
    return Check(
        "new-project-packet-contract",
        not missing,
        "packet contract ok" if not missing else "missing=" + ",".join(missing),
    )


def _active_legacy_reference_only() -> Check:
    missing: list[str] = []
    for path in ACTIVE_LEGACY_REFERENCE_ONLY:
        text = path.read_text(encoding="utf-8-sig", errors="replace") if path.exists() else ""
        if "Superseded reference-only" not in text or "not current instruction authority" not in text:
            missing.append(path.relative_to(ROOT).as_posix())
    return Check(
        "active-legacy-reference-only",
        not missing,
        "legacy active-folder docs marked reference-only" if not missing else "missing=" + ",".join(missing),
    )


def run_checks() -> list[Check]:
    checks: list[Check] = []

    missing_files = [path.relative_to(ROOT).as_posix() for path in REQUIRED_FILES if not path.exists()]
    checks.append(Check("required-files", not missing_files, "missing=" + ",".join(missing_files) if missing_files else "all present"))

    for path, snippets in REQUIRED_TEXT.items():
        text = path.read_text(encoding="utf-8-sig", errors="replace") if path.exists() else ""
        missing = [snippet for snippet in snippets if snippet not in text]
        checks.append(Check(f"text:{path.name}", not missing, "missing=" + " | ".join(missing) if missing else "required text present"))

    counts = _status_counts()
    bad_statuses = {
        key: counts.get(key, 0)
        for key in ("candidate-review", "high-priority-review", "secret-review-before-read")
        if counts.get(key, 0)
    }
    detail = ", ".join(f"{key}={value}" for key, value in sorted(counts.items()))
    checks.append(Check("legacy-inventory", not bad_statuses, detail))

    residue_findings = legacy_residue_scanner.scan()
    review_count = sum(1 for item in residue_findings if item.severity == "review")
    ok_count = sum(1 for item in residue_findings if item.severity == "ok")
    checks.append(Check("legacy-residue", review_count == 0, f"review={review_count}, allowed={ok_count}"))

    secret_entries = legacy_secret_manifest.build_manifest()
    untracked_secret = sum(1 for item in secret_entries if item.status == "secret-review-before-read")
    tracked_secret = sum(1 for item in secret_entries if item.status == "secret-audit-mentioned")
    checks.append(
        Check(
            "legacy-secret-manifest",
            untracked_secret == 0,
            f"secret_candidates={len(secret_entries)}, secret_review_before_read={untracked_secret}, secret_audit_mentioned={tracked_secret}",
        )
    )
    checks.append(_manifest_value_free())
    checks.append(_secret_decision_register())

    checks.append(
        _selector_has(
            "legacy instruction migration",
            (
                "ObsidianVault/00_System/LEGACY_INSTRUCTION_CANDIDATE_AUDIT_2026-05-30.md",
                "ObsidianVault/00_System/LEGACY_INSTRUCTION_INVENTORY_2026-05-30.md",
                "ObsidianVault/00_System/LEGACY_RESIDUE_SCAN_2026-05-30.md",
                "ObsidianVault/00_System/LEGACY_SECRET_REVIEW_POLICY_2026-05-30.md",
                "ObsidianVault/00_System/LEGACY_SECRET_MANIFEST_2026-05-30.md",
                "ObsidianVault/00_System/LEGACY_SECRET_DECISION_REGISTER_2026-05-30.md",
                "ObsidianVault/00_System/BUCKY_OS_RUNBOOK.md",
            ),
        )
    )
    checks.append(
        _selector_has(
            "Claude Code new project implementation",
            (
                "CLAUDE.md",
                "ObsidianVault/06_Context_Packs/bucky-development-workflow-policy.md",
                "ObsidianVault/03_Projects/agents/bucky.md",
                "ObsidianVault/00_System/BUCKY_OS_RUNBOOK.md",
            ),
        )
    )
    checks.append(
        _selector_has(
            "mid-size refactor plan QA verification",
            (
                "ObsidianVault/06_Context_Packs/bucky-development-workflow-policy.md",
                "ObsidianVault/06_Context_Packs/bucky-security-runtime-governance.md",
            ),
        )
    )
    checks.append(_active_legacy_reference_only())
    checks.append(_packet_contract())
    return checks


def write_report(checks: list[Check], report_path: Path) -> None:
    passed = all(check.passed for check in checks)
    lines = [
        "---",
        "type: bucky-os-gate",
        f"created: {datetime.now().isoformat(timespec='seconds')}",
        "status: pass" if passed else "status: fail",
        "owner: Bucky",
        "---",
        "",
        "# Bucky OS Gate",
        "",
        "Purpose: verify that Obsidian Agent Brain System is the active instruction operating layer for JH agent work.",
        "",
        f"- Result: {'PASS' if passed else 'FAIL'}",
        "",
        "## Checks",
        "",
        "| Check | Status | Detail |",
        "|---|---|---|",
    ]
    for check in checks:
        detail = check.detail.replace("|", "\\|")
        lines.append(f"| {check.name} | {'PASS' if check.passed else 'FAIL'} | {detail} |")
    lines.extend(
        [
            "",
            "## Completion Boundary",
            "",
            "- This gate proves current instruction authority, legacy instruction inventory coverage, and selector routing.",
            "- It does not prove that every archived data file has been semantically redacted or re-authored.",
            "- Secret-like archive entries remain quarantined until targeted redaction review.",
        ]
    )
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the Bucky OS instruction authority gate.")
    parser.add_argument("--report", default=str(DEFAULT_REPORT))
    parser.add_argument("--fail-on-error", action="store_true")
    args = parser.parse_args()

    checks = run_checks()
    write_report(checks, Path(args.report))
    passed = all(check.passed for check in checks)
    print(f"report={args.report}")
    print(f"result={'PASS' if passed else 'FAIL'}")
    for check in checks:
        print(f"{check.name}={'PASS' if check.passed else 'FAIL'} {check.detail}")
    return 2 if args.fail_on_error and not passed else 0


if __name__ == "__main__":
    raise SystemExit(main())
