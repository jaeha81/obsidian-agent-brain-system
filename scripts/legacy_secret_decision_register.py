#!/usr/bin/env python3
"""Build a value-free decision register for secret-like legacy candidates."""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import legacy_secret_manifest


ROOT = Path(__file__).resolve().parent.parent
VAULT = ROOT / "ObsidianVault"
DEFAULT_REPORT = VAULT / "00_System" / "LEGACY_SECRET_DECISION_REGISTER_2026-05-30.md"

FORBIDDEN_PATTERNS = {
    "openai_key_shape": re.compile(r"sk-[A-Za-z0-9_-]{12,}", re.IGNORECASE),
    "webhook_url": re.compile(r"https?://[^\s|`]*(webhook|hooks)[^\s|`]*", re.IGNORECASE),
    "excerpt_column": re.compile(r"\|\s*(Excerpt|Text|Matched text|Line text)\s*\|", re.IGNORECASE),
}


@dataclass(frozen=True)
class Decision:
    path: Path
    pattern_classes: tuple[str, ...]
    decision: str
    promotion_target: str
    evidence: str
    next_action: str


def _decision_for(path: Path) -> tuple[str, str, str, str]:
    rel = path.relative_to(ROOT).as_posix()
    lower = rel.lower()
    if "gdrive-archive" in lower:
        return (
            "archive-only",
            "none",
            "imported from shared drive legacy system; archive-only, not current instruction authority",
            "keep quarantined as historical evidence; do not promote without targeted redaction review",
        )
    if "agentbus.md" in lower:
        return (
            "covered-quarantined",
            "ObsidianVault/05_Frameworks/AgentBus/agentbus_protocol.md",
            "webhook_word match is a WikiLink reference [[webhook-vault-write-pattern]], not an actual webhook URL; AgentBus protocol is covered",
            "only targeted redaction required if real webhook URLs are added to the file",
        )
    if "/sessions/" in lower:
        return (
            "archive-only",
            "none",
            "session logs are evidence; reusable session rules are covered by record and Goal Mode packs",
            "do not promote unless a later targeted review identifies a missing reusable rule",
        )
    if "output/codex-review-targets/" in lower:
        return (
            "archive-only",
            "none",
            "old verification outputs are evidence; current verification rules are covered by Codex and Goal Mode packs",
            "keep quarantined as historical evidence",
        )
    if "jh-infranodus-upgrade-analysis" in lower:
        return (
            "archive-only",
            "none",
            "old graph analysis is superseded by Graphify/LegalizeKR scoped policies",
            "keep as reference unless a graph task requests targeted review",
        )
    if "ai-api-routing-architect" in lower:
        return (
            "covered-quarantined",
            "ObsidianVault/06_Context_Packs/bucky-ai-api-routing-policy.md",
            "AI/API routing rules are already promoted; source remains secret-like",
            "only targeted redaction may extract additional non-secret rules",
        )
    if "06_" in lower or "tech-stack" in lower or "기술" in rel:
        return (
            "covered-quarantined",
            "ObsidianVault/06_Context_Packs/bucky-security-runtime-governance.md",
            "technical stack and development defaults are promoted as current Bucky runtime governance; source remains secret-like",
            "only targeted redaction may extract additional non-secret examples",
        )
    if "11_obsidian" in lower or "세컨드브레인" in rel or "체크포인트" in rel:
        return (
            "covered-quarantined",
            "ObsidianVault/06_Context_Packs/bucky-vault-ingestion-record-policy.md",
            "second-brain checkpoint behavior is promoted as current Vault checkpoint workflow; source remains secret-like",
            "only targeted redaction may extract additional non-secret examples",
        )
    if "12_ai_tools" in lower:
        return (
            "covered-quarantined",
            "ObsidianVault/06_Context_Packs/bucky-security-runtime-governance.md",
            "AI tool safety rules are already promoted; source remains secret-like",
            "only targeted redaction may extract additional non-secret rules",
        )
    if "05_jh_estimate_ai" in lower:
        return (
            "covered-quarantined",
            "ObsidianVault/06_Context_Packs/bucky-user-project-terrain.md",
            "EstimateAI terrain is already promoted with stale-data warning; source remains secret-like",
            "only targeted redaction may extract additional non-secret rules",
        )
    if "06_jh_harness" in lower:
        return (
            "covered-quarantined",
            "ObsidianVault/06_Context_Packs/bucky-security-runtime-governance.md",
            "agent-control/runtime governance rules are already promoted; source remains secret-like",
            "only targeted redaction may extract additional non-secret rules",
        )
    if "12_" in lower or "security" in lower or "보안" in rel:
        return (
            "covered-quarantined",
            "ObsidianVault/06_Context_Packs/bucky-security-runtime-governance.md",
            "security/legal handling is already promoted; source remains secret-like",
            "only targeted redaction may extract additional non-secret rules",
        )
    if "13_" in lower or "prompt" in lower or "템플릿" in rel:
        return (
            "covered-quarantined",
            "ObsidianVault/06_Context_Packs/bucky-vault-ingestion-record-policy.md",
            "prompt/template record behavior is already promoted; source remains secret-like",
            "only targeted redaction may extract additional non-secret rules",
        )
    if "agent-room" in lower or "jh-agent-room" in lower:
        return (
            "covered-quarantined",
            "ObsidianVault/05_Frameworks/AgentBus/agentbus_protocol.md",
            "old Agent Room behavior is covered by current AgentBus protocol; source remains secret-like",
            "only targeted redaction may extract additional non-secret rules",
        )
    if "gpt-memory" in lower or "raw/gpt" in lower:
        return (
            "partial-promoted-quarantined",
            "ObsidianVault/06_Context_Packs/bucky-user-communication-output-policy.md",
            "safe inventory excerpt already promoted user-output rules; source remains secret-like",
            "targeted redaction required before any further extraction",
        )
    return (
        "pending-targeted-redaction",
        "none",
        "no safe promotion decision without targeted redaction",
        "review only the manifest-listed lines and redact before promotion",
    )


def build_register() -> list[Decision]:
    decisions: list[Decision] = []
    for entry in legacy_secret_manifest.build_manifest():
        decision, target, evidence, next_action = _decision_for(entry.path)
        decisions.append(
            Decision(
                path=entry.path,
                pattern_classes=entry.pattern_types,
                decision=decision,
                promotion_target=target,
                evidence=evidence,
                next_action=next_action,
            )
        )
    return sorted(decisions, key=lambda item: item.path.as_posix().lower())


def write_report(decisions: list[Decision], report_path: Path) -> None:
    counts: dict[str, int] = {}
    for decision in decisions:
        counts[decision.decision] = counts.get(decision.decision, 0) + 1

    lines = [
        "---",
        "type: legacy-secret-decision-register",
        f"created: {datetime.now().isoformat(timespec='seconds')}",
        "status: active",
        "owner: Bucky",
        "---",
        "",
        "# Legacy Secret Decision Register",
        "",
        "This register is value-free. It does not include secret values, matched line text, or excerpts.",
        "",
        f"- Candidates: {len(decisions)}",
    ]
    for decision, count in sorted(counts.items()):
        lines.append(f"- {decision}: {count}")

    lines.extend(
        [
            "",
            "## Decision Rules",
            "",
            "- `archive-only`: no promotion needed unless a later targeted review proves a missing reusable rule.",
            "- `covered-quarantined`: useful rule class is already promoted, but the source remains secret-like.",
            "- `partial-promoted-quarantined`: a safe manifest/inventory signal was promoted; source still needs redaction for more.",
            "- `pending-targeted-redaction`: no further use until manifest-listed lines are reviewed and redacted.",
            "",
            "## Entries",
            "",
            "| Decision | Path | Pattern classes | Promotion target | Evidence | Next action |",
            "|---|---|---|---|---|---|",
        ]
    )
    for item in decisions:
        rel = item.path.relative_to(ROOT).as_posix()
        patterns = ", ".join(item.pattern_classes) if item.pattern_classes else "secret-hint"
        lines.append(
            f"| {item.decision} | `{rel}` | {patterns} | {item.promotion_target} | {item.evidence} | {item.next_action} |"
        )

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def report_is_value_free(report_path: Path) -> bool:
    text = report_path.read_text(encoding="utf-8-sig", errors="replace") if report_path.exists() else ""
    return not any(regex.search(text) for regex in FORBIDDEN_PATTERNS.values())


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a value-free decision register for secret-like legacy candidates.")
    parser.add_argument("--report", default=str(DEFAULT_REPORT))
    parser.add_argument("--fail-on-pending", action="store_true")
    args = parser.parse_args()

    report_path = Path(args.report)
    decisions = build_register()
    write_report(decisions, report_path)
    pending = sum(1 for item in decisions if item.decision == "pending-targeted-redaction")
    print(f"report={args.report}")
    print(f"candidates={len(decisions)}")
    print(f"pending_targeted_redaction={pending}")
    print(f"value_free={report_is_value_free(report_path)}")
    return 2 if args.fail_on_pending and pending else 0


if __name__ == "__main__":
    raise SystemExit(main())
