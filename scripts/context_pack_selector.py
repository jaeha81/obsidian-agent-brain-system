#!/usr/bin/env python3
"""Select compact Bucky Context Packs and optional instruction packets."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

# Repo root is the parent of the scripts/ directory.
# Pack paths like "ObsidianVault/..." are relative to this root.
_REPO_ROOT: Path = Path(__file__).parent.parent

# Allowed top-level roots under _REPO_ROOT that inject_context_packs may read.
_ALLOWED_ROOTS: frozenset[str] = frozenset(
    {
        "ObsidianVault",
        "CLAUDE.md",
    }
)

# Default character budget for inject_context_packs — generous enough for
# several context packs while keeping injected context below LLM limits.
_DEFAULT_MAX_CHARS: int = 200_000


@dataclass(frozen=True)
class PackRule:
    key: str
    primary_worker: str
    role: str
    packs: tuple[str, ...]
    notes: tuple[str, ...]
    triggers: tuple[str, ...]


CORE_PACKS = (
    "ObsidianVault/06_Context_Packs/bucky-agent-os-legacy-rules.md",
    "ObsidianVault/06_Context_Packs/bucky-context-efficiency-goal-mode.md",
    "ObsidianVault/06_Context_Packs/bucky-user-communication-output-policy.md",
)

RUNBOOK_PACK = "ObsidianVault/00_System/BUCKY_OS_RUNBOOK.md"


RULES: tuple[PackRule, ...] = (
    PackRule(
        key="review",
        primary_worker="Codex Reviewer",
        role="independent review / verification",
        packs=CORE_PACKS + ("ObsidianVault/03_Projects/agents/codex-instructions.md",),
        notes=("Use for independent review, verification, regression checks, and AI-slop checks.",),
        triggers=("review", "verify", "검수", "리뷰", "검증", "codex", "bug", "regression", "회귀"),
    ),
    PackRule(
        key="implementation",
        primary_worker="Claude Code Builder",
        role="implementation / operation",
        packs=CORE_PACKS
        + (
            "ObsidianVault/06_Context_Packs/bucky-development-workflow-policy.md",
            RUNBOOK_PACK,
            "CLAUDE.md",
            "ObsidianVault/03_Projects/agents/bucky.md",
        ),
        notes=("Use for code/file implementation after Bucky defines scope and done_when.",),
        triggers=("implementation", "implement", "build", "수정", "구현", "개발", "claude", "code"),
    ),
    PackRule(
        key="legacy_migration",
        primary_worker="Bucky Knowledge Curator",
        role="legacy absorption / migration",
        packs=CORE_PACKS
        + (
            "ObsidianVault/06_Context_Packs/bucky-migration-build-charter.md",
            "ObsidianVault/06_Context_Packs/bucky-vault-ingestion-record-policy.md",
            "ObsidianVault/06_Context_Packs/bucky-security-runtime-governance.md",
            RUNBOOK_PACK,
            "ObsidianVault/00_System/LEGACY_INSTRUCTION_CANDIDATE_AUDIT_2026-05-30.md",
            "ObsidianVault/00_System/LEGACY_INSTRUCTION_INVENTORY_2026-05-30.md",
            "ObsidianVault/00_System/LEGACY_RESIDUE_SCAN_2026-05-30.md",
            "ObsidianVault/00_System/LEGACY_SECRET_REVIEW_POLICY_2026-05-30.md",
            "ObsidianVault/00_System/LEGACY_SECRET_MANIFEST_2026-05-30.md",
            "ObsidianVault/00_System/LEGACY_SECRET_DECISION_REGISTER_2026-05-30.md",
        ),
        notes=("Use for absorbing old shared folders, raw memories, templates, and migration leftovers.",),
        triggers=("legacy", "migration", "archive", "이전", "레거시", "이관", "마이그레이션", "잔재", "흡수"),
    ),
    PackRule(
        key="ai_api",
        primary_worker="Bucky API Architect",
        role="AI/API architecture",
        packs=CORE_PACKS
        + (
            "ObsidianVault/06_Context_Packs/bucky-ai-api-routing-policy.md",
            "ObsidianVault/06_Context_Packs/bucky-security-runtime-governance.md",
        ),
        notes=("Use for LLM/API/RAG/OCR/image/audio AI provider choices, keys, logging, fallback, and cost controls.",),
        triggers=("api", "llm", "rag", "ocr", "embedding", "model", "gemini", "openai", "ai api", "키", "비용"),
    ),
    PackRule(
        key="security_runtime",
        primary_worker="Bucky Risk Controller",
        role="security / runtime governance",
        packs=CORE_PACKS
        + (
            "ObsidianVault/06_Context_Packs/bucky-security-runtime-governance.md",
            "ObsidianVault/00_System/LEGACY_SECRET_REVIEW_POLICY_2026-05-30.md",
        ),
        notes=("Use for auth, secrets, payments, deployment, customer data, public release, and runtime control.",),
        triggers=("security", "secret", "auth", "payment", "deploy", "release", "보안", "인증", "결제", "배포", "고객", "개인정보"),
    ),
    PackRule(
        key="vault_record",
        primary_worker="Bucky Archivist",
        role="record / evidence management",
        packs=CORE_PACKS + ("ObsidianVault/06_Context_Packs/bucky-vault-ingestion-record-policy.md",),
        notes=("Use for source ingest, session summaries, decision logs, daily retrospectives, and durable evidence.",),
        triggers=("ingest", "record", "summary", "decision", "handoff", "기록", "요약", "결정", "보고", "인계", "저장"),
    ),
    PackRule(
        key="project_terrain",
        primary_worker="Bucky Product Mapper",
        role="project orientation",
        packs=CORE_PACKS + ("ObsidianVault/06_Context_Packs/bucky-user-project-terrain.md",),
        notes=("Use for orienting new projects to the user's domain and JH project terrain. Verify stale facts before use.",),
        triggers=("project", "product", "estimate", "interior", "construction", "jh", "프로젝트", "상품", "견적", "인테리어", "건축", "브랜드"),
    ),
    PackRule(
        key="graph_legal",
        primary_worker="Bucky Framework Router",
        role="graph/legal framework work",
        packs=CORE_PACKS
        + (
            "ObsidianVault/06_Context_Packs/bucky-migration-build-charter.md",
            "ObsidianVault/05_Frameworks/LegalizeKR/legalize_update_policy.md",
            "ObsidianVault/05_Frameworks/Graphify/README.md",
        ),
        notes=("Use for Graphify, LegalizeKR, legal context packs, and scope-limited graph/legal work.",),
        triggers=("graph", "graphify", "legal", "law", "법", "법령", "그래프", "legalize"),
    ),
    PackRule(
        key="sync_agentbus",
        primary_worker="Bucky Operator",
        role="sync / AgentBus operation",
        packs=CORE_PACKS
        + (
            "ObsidianVault/00_System/ROUTING_RULES.md",
            "ObsidianVault/05_Frameworks/guides/sync-protocol.md",
            "ObsidianVault/05_Frameworks/AgentBus/agentbus_protocol.md",
        ),
        notes=("Use for AgentBus, sync, multi-PC handoff, queue routing, and Discord operational flow.",),
        triggers=("sync", "agentbus", "discord", "queue", "handoff", "동기화", "에이전트버스", "디스코드", "큐"),
    ),
    PackRule(
        key="design",
        primary_worker="Bucky Design Director",
        role="design improvement / quality elevation",
        packs=CORE_PACKS
        + (
            "ObsidianVault/06_Context_Packs/bucky-design-improvement-policy.md",
            "ObsidianVault/06_Context_Packs/web-delivery-pack.md",
        ),
        notes=(
            "Use for design improvement, redesign, UI/UX quality elevation, and from-scratch premium builds.",
            "Apply AI-Slop prohibition: no emoji-as-icon, no generic Hero+Cards+CTA, premium SaaS reference level.",
            "Link skills: redesign-skill, taste-skill, design:design-critique, jh-variant, Pencil MCP.",
        ),
        triggers=(
            "design", "redesign", "ui", "ux", "디자인", "개선", "퀄리티", "quality",
            "예쁘게", "스타일", "레이아웃", "layout", "figma", "pencil", "variant",
            "리디자인", "비주얼", "visual", "테마", "theme",
        ),
    ),
    PackRule(
        key="development_workflow",
        primary_worker="Bucky Delivery Planner",
        role="development workflow / QA planning",
        packs=CORE_PACKS
        + (
            "ObsidianVault/06_Context_Packs/bucky-development-workflow-policy.md",
            "ObsidianVault/06_Context_Packs/bucky-security-runtime-governance.md",
        ),
        notes=("Use for task sizing, plan-first decisions, implementation loops, QA gates, and handoff evidence.",),
        triggers=("workflow", "plan", "qa", "test", "build", "refactor", "release", "워크플로우", "계획", "테스트", "검증", "리팩터", "릴리즈"),
    ),
)


def _resolve_safe_path(pack_path: str, vault_root: Path) -> Path | None:
    """Return an absolute Path for *pack_path* under *vault_root*, or None if unsafe.

    Blocked:
    - Absolute paths (security: the caller should not be able to read arbitrary FS paths).
    - Any path component equal to '..', including obfuscated forms after resolution.
    - Paths that resolve outside *vault_root* after normalization.
    - Paths whose first component is not in _ALLOWED_ROOTS.
    """
    raw = Path(pack_path)
    if raw.is_absolute():
        return None
    if ".." in raw.parts:
        return None
    # First component must be an allowed root (or the exact allowed file)
    first = raw.parts[0] if raw.parts else ""
    # Allow exact filename matches (e.g. "CLAUDE.md") as well as directory roots
    if first not in _ALLOWED_ROOTS and pack_path not in _ALLOWED_ROOTS:
        return None
    resolved = (vault_root / raw).resolve()
    # Final guard: resolved path must still be inside vault_root
    try:
        resolved.relative_to(vault_root.resolve())
    except ValueError:
        return None
    return resolved


def inject_context_packs(
    packs: list[str],
    *,
    vault_root: Path | None = None,
    max_chars: int | None = None,
) -> dict[str, str]:
    """Read pack files from *vault_root* and return ``{pack_path: content}``.

    *vault_root*: directory against which relative pack paths are resolved.
    Default is the repository root (parent of ``scripts/``), correct when pack
    paths start with ``ObsidianVault/``.

    *max_chars*: total character budget shared across all packs.
    Default: ``_DEFAULT_MAX_CHARS`` (200 000).  Packs are processed in list
    order; each consumes from the shared budget.  Each file is read with a
    streaming limit of ``remaining + 1`` chars — the full file is never loaded
    into memory when it would exceed the remaining budget.

    Markers embedded in the returned string values:

    - ``[BLOCKED: ...]`` — path failed security validation; not read.
    - ``[NOT FOUND: ...]`` — file does not exist.
    - ``[BINARY: ...]`` — file is not valid UTF-8; byte size from stat reported.
    - ``content + \\n[TRUNCATED: ...]`` — file was cut to fit remaining budget.
    - ``[BUDGET_EXHAUSTED: ...]`` — budget already spent; file skipped entirely.

    Security guarantees (see _resolve_safe_path):
    - Absolute paths are blocked.
    - ``..`` path components are blocked.
    - Paths that resolve outside *vault_root* are blocked.
    - Only paths whose first component is in ``_ALLOWED_ROOTS`` are permitted.
    """
    root = vault_root if vault_root is not None else _REPO_ROOT
    budget = max_chars if max_chars is not None else _DEFAULT_MAX_CHARS
    used = 0
    result: dict[str, str] = {}

    for pack in packs:
        safe = _resolve_safe_path(pack, root)
        if safe is None:
            result[pack] = f"[BLOCKED: unsafe path '{pack}']"
            continue

        if used >= budget:
            result[pack] = (
                f"[BUDGET_EXHAUSTED: {used:,}/{budget:,} chars used, '{pack}' skipped]"
            )
            continue

        # stat() first: fast existence check + byte size for BINARY marker.
        try:
            file_bytes = safe.stat().st_size
        except FileNotFoundError:
            result[pack] = f"[NOT FOUND: '{pack}']"
            continue
        except OSError as exc:
            result[pack] = f"[ERROR: {exc}]"
            continue

        # Streaming read: load at most (remaining + 1) chars — never the full file.
        # One extra char lets us detect truncation without a separate seek.
        remaining = budget - used
        try:
            with safe.open("r", encoding="utf-8", errors="strict") as fh:
                chunk = fh.read(remaining + 1)
        except UnicodeDecodeError:
            result[pack] = (
                f"[BINARY: '{pack}' is not valid UTF-8; {file_bytes:,} bytes]"
            )
            continue
        except OSError as exc:
            result[pack] = f"[ERROR: {exc}]"
            continue

        if len(chunk) > remaining:
            result[pack] = (
                chunk[:remaining]
                + f"\n[TRUNCATED: first {remaining:,} chars read;"
                f" budget {budget:,} chars total]"
            )
            used = budget  # budget fully consumed after truncation
        else:
            result[pack] = chunk
            used += len(chunk)

    return result


def _score(rule: PackRule, text: str, task_type: str) -> int:
    haystack = f"{task_type}\n{text}".lower()
    return sum(1 for trigger in rule.triggers if trigger.lower() in haystack)


def _find_rule(key: str) -> PackRule:
    return next(rule for rule in RULES if rule.key == key)


def select_context_pack(*, task_type: str, body: str) -> dict:
    scored = sorted(
        ((_score(rule, body or "", task_type or ""), rule) for rule in RULES),
        key=lambda item: (-item[0], item[1].key),
    )
    score, rule = scored[0]
    if score == 0:
        rule = _find_rule("implementation")
    return {
        "key": rule.key,
        "primary_worker": rule.primary_worker,
        "role": rule.role,
        "packs": list(rule.packs),
        "notes": list(rule.notes),
    }


def build_instruction_packet(*, task_type: str, body: str, project: str = "") -> dict:
    selection = select_context_pack(task_type=task_type, body=body)
    project_value = project or str(Path.cwd())
    return {
        "project": project_value,
        "agent": selection["primary_worker"],
        "role": selection["role"],
        "goal": body or "Handle the requested task inside the current project scope.",
        "scope": "Use only the current project and Bucky-selected references unless the user expands scope.",
        "constraints": [
            "Do not reuse another repo/folder instruction packet automatically.",
            "Do not commit, push, delete, move, reset, or run non-dry-run legacy migration without explicit user approval.",
            "Preserve user changes and report blockers with evidence.",
            "Keep context compact; use referenced files instead of pasting long source material.",
            "Do not open, quote, or promote secret-like legacy archive material before targeted redaction review.",
        ],
        "context_packs": selection["packs"],
        "references": selection["packs"],
        "verification": [
            "Run the narrow command or inspection that proves this task's done_when.",
            "For review tasks, inspect recent/uncommitted changes and recurring error patterns.",
            "For migration tasks, update or check the legacy residue scan.",
        ],
        "done_when": "The requested outcome is verified with current files, command output, or saved evidence.",
        "fallback": "If Bucky is unavailable or the packet is too broad, apply minimum safety rules and request a narrower packet.",
    }


def format_text(selection: dict) -> str:
    lines = [
        "[Context Pack Selector]",
        f"Key: {selection['key']}",
        f"Primary worker: {selection['primary_worker']}",
        f"Role: {selection['role']}",
        "Packs:",
    ]
    lines.extend(f"- {pack}" for pack in selection["packs"])
    lines.append("Notes:")
    lines.extend(f"- {note}" for note in selection["notes"])
    if "injected_context" in selection:
        lines.append("")
        lines.append("Injected Context:")
        for path, content in selection["injected_context"].items():
            lines.append(f"=== {path} ===")
            lines.append(content)
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Select Bucky Context Packs or produce a compact instruction packet.")
    parser.add_argument("--task-type", default="general")
    parser.add_argument("--project", default="")
    parser.add_argument("--format", choices=("json", "text"), default="json")
    parser.add_argument("--packet", action="store_true", help="emit a compact Bucky instruction packet")
    parser.add_argument(
        "--inject",
        action="store_true",
        help=(
            "read selected pack files and embed their contents in the output. "
            "When combined with --packet the injected content appears under the "
            "'injected_context' key inside the packet JSON."
        ),
    )
    parser.add_argument(
        "--vault-root",
        default="",
        help=(
            "root directory for resolving pack paths (default: repo root, i.e. "
            "parent of scripts/). Pack paths like 'ObsidianVault/...' are "
            "relative to this root."
        ),
    )
    parser.add_argument(
        "--max-chars",
        type=int,
        default=None,
        metavar="N",
        help=(
            f"character budget for --inject across all packs "
            f"(default: {_DEFAULT_MAX_CHARS:,}). "
            "Excess content is marked [TRUNCATED] or [BUDGET_EXHAUSTED]."
        ),
    )
    parser.add_argument("body", nargs="*", help="Task body text.")
    args = parser.parse_args()

    body = " ".join(args.body)
    vault_root = Path(args.vault_root) if args.vault_root else None

    if args.packet:
        payload = build_instruction_packet(task_type=args.task_type, body=body, project=args.project)
        if args.inject:
            # --packet + --inject: injected file contents go into 'injected_context'.
            payload["injected_context"] = inject_context_packs(
                payload["context_packs"],
                vault_root=vault_root,
                max_chars=args.max_chars,
            )
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        payload = select_context_pack(task_type=args.task_type, body=body)
        if args.inject:
            payload["injected_context"] = inject_context_packs(
                payload["packs"],
                vault_root=vault_root,
                max_chars=args.max_chars,
            )
        if args.format == "text":
            print(format_text(payload))
        else:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
