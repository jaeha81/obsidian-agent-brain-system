#!/usr/bin/env python3
"""Harness Framework router for development requests.

The router mirrors the JH Harness Dashboard knowledge base:
- Superpowers: execution quality, TDD, subagent workflow
- GSD: long-running phased projects and context stabilization
- gstack: product direction, role governance, UX/security review

It keeps the Obsidian Vault as the readable knowledge source while providing a
deterministic local classifier for AgentBus prompts.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


ROOT = Path(__file__).parent.parent
load_dotenv(ROOT / ".env", encoding="utf-8-sig", override=True)

VAULT = Path(os.getenv("VAULT_PATH", str(ROOT / "ObsidianVault")))
HARNESS_DIR = VAULT / "05_Frameworks" / "Harness"


@dataclass(frozen=True)
class FrameworkProfile:
    key: str
    name: str
    tagline: str
    install: str
    workflow: list[str]
    agents: list[str]
    use_when: list[str]
    avoid_when: list[str]
    codex_focus: list[str]
    doc_name: str


FRAMEWORKS: dict[str, FrameworkProfile] = {
    "superpowers": FrameworkProfile(
        key="superpowers",
        name="Superpowers",
        tagline="Execution quality, TDD, and subagent-driven implementation",
        install="/plugin install superpowers@claude-plugins-official",
        workflow=[
            "brainstorming",
            "using-git-worktrees",
            "writing-plans",
            "subagent-driven-development",
            "test-driven-development",
            "requesting-code-review",
            "finishing-a-development-branch",
        ],
        agents=["subagent-driven-development", "test-driven-development"],
        use_when=[
            "Implementation quality matters more than speed",
            "Tests, refactors, or multi-file code changes are required",
            "The request is already directionally clear and ready to execute",
        ],
        avoid_when=[
            "The task is a tiny wording or CSS change",
            "The product direction is still unclear",
            "The environment cannot support subagent-style execution",
        ],
        codex_focus=[
            "Verify plan-to-code alignment",
            "Verify tests were created or updated before production behavior is trusted",
            "Check edge cases and regression risk",
        ],
        doc_name="Superpowers.md",
    ),
    "gsd": FrameworkProfile(
        key="gsd",
        name="GSD",
        tagline="Context-stable phased delivery for larger work",
        install="npx get-shit-done-cc@latest",
        workflow=[
            "/gsd-new-project",
            "/gsd-discuss-phase N",
            "/gsd-plan-phase N",
            "/gsd-execute-phase N",
            "/gsd-verify-work N",
            "/gsd-ship N",
        ],
        agents=["gsd-planner", "gsd-executor", "gsd-verifier"],
        use_when=[
            "The project is long-running or has several milestones",
            "The request contains many requirements or a large instruction document",
            "State must survive across sessions in a .planning directory",
        ],
        avoid_when=[
            "The task is a one-file quick fix",
            "The idea direction has not been decided yet",
            "The work is temporary and does not need persistent planning state",
        ],
        codex_focus=[
            "Verify .planning state and phase boundaries",
            "Check that implementation matches the agreed phase plan",
            "Confirm verification and ship criteria are explicit",
        ],
        doc_name="GSD.md",
    ),
    "gstack": FrameworkProfile(
        key="gstack",
        name="gstack",
        tagline="Product direction, role governance, and review gates",
        install=(
            "git clone --single-branch --depth 1 "
            "https://github.com/garrytan/gstack.git ~/.claude/skills/gstack "
            "&& cd ~/.claude/skills/gstack && ./setup"
        ),
        workflow=[
            "/office-hours",
            "/plan-ceo-review",
            "/plan-eng-review",
            "/plan-design-review",
            "implementation",
            "/review",
            "/qa",
            "/ship",
        ],
        agents=["gstack-ceo", "plan-eng-review", "plan-design-review", "qa"],
        use_when=[
            "The request needs product direction before implementation",
            "UX, security, architecture, or governance decisions are important",
            "The system should ask whether the feature should be built at all",
        ],
        avoid_when=[
            "The feature is already fully specified and only needs execution",
            "The task is a quick bug fix",
            "Only test reinforcement is needed",
        ],
        codex_focus=[
            "Verify architecture, data flow, UX, and security assumptions",
            "Check destructive commands and deployment risk",
            "Look for LLM trust boundary and SQL/auth issues where relevant",
        ],
        doc_name="gstack.md",
    ),
}


TEST_KW = (
    "test", "tdd", "jest", "vitest", "cypress", "e2e", "spec",
    "테스트", "검증", "리팩터", "리팩토링", "버그", "회귀",
)
LONGTERM_KW = (
    "phase", "milestone", "sprint", "roadmap", "migration", "refactor",
    "장기", "단계", "마일스톤", "로드맵", "이관", "마이그레이션",
)
UX_KW = (
    "ux", "ui", "design", "responsive", "mobile", "layout", "figma",
    "디자인", "화면", "모바일", "반응형", "접근성", "사용자경험",
)
SECURITY_KW = (
    "security", "auth", "oauth", "jwt", "permission", "encrypt",
    "sql injection", "xss", "csrf", "보안", "인증", "권한", "암호화", "토큰",
)


def is_harness_router_enabled() -> bool:
    value = os.getenv("HARNESS_ROUTER_ENABLED", "1").strip().lower()
    return value not in {"0", "false", "no", "off"}


def _has_any(text: str, keywords: tuple[str, ...]) -> bool:
    return any(keyword in text for keyword in keywords)


def _task_lines(text: str) -> list[str]:
    tasks: list[str] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if re.match(r"^(\d+[\.)]\s+|[-*]\s+|#{1,3}\s+|>\s+)", line):
            item = re.sub(r"^(\d+[\.)]\s+|[-*]\s+|#{1,3}\s+|>\s+)", "", line).strip()
            if 4 <= len(item) <= 220:
                tasks.append(item)
    return tasks


def analyze_request(text: str) -> dict:
    lowered = text.lower()
    tasks = _task_lines(text)
    scope_size = len(text)
    complexity = "high" if scope_size > 2000 or len(tasks) > 10 else "medium" if scope_size > 500 or len(tasks) > 4 else "low"
    signals = {
        "has_test": _has_any(lowered, TEST_KW),
        "has_longterm": _has_any(lowered, LONGTERM_KW),
        "has_ux": _has_any(lowered, UX_KW),
        "has_security": _has_any(lowered, SECURITY_KW),
        "complexity": complexity,
        "task_lines": tasks[:12],
        "scope_size": scope_size,
    }
    return signals


def route_framework(text: str) -> dict:
    signals = analyze_request(text)
    scores = {"superpowers": 1, "gsd": 0, "gstack": 0}

    if signals["has_test"]:
        scores["superpowers"] += 3
    if signals["has_longterm"]:
        scores["gsd"] += 3
    if signals["has_ux"]:
        scores["gstack"] += 2
    if signals["has_security"]:
        scores["gstack"] += 2
    if signals["complexity"] == "high":
        scores["gsd"] += 2
    elif signals["complexity"] == "medium":
        scores["gsd"] += 1
    if len(signals["task_lines"]) > 6:
        scores["gsd"] += 1

    ordered = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    top_key, top_score = ordered[0]
    close_keys = [key for key, score in ordered if top_score - score <= 1 and score > 0]

    if len(close_keys) > 1:
        if {"gstack", "gsd", "superpowers"}.issubset(close_keys):
            selected_keys = ["gstack", "gsd", "superpowers"]
        elif "gstack" in close_keys and "gsd" in close_keys:
            selected_keys = ["gstack", "gsd"]
        elif "gsd" in close_keys and "superpowers" in close_keys:
            selected_keys = ["gsd", "superpowers"]
        else:
            selected_keys = close_keys
    else:
        selected_keys = [top_key]

    if (signals["has_security"] or signals["has_ux"]) and "gstack" not in selected_keys and scores["gstack"] >= 2:
        selected_keys.append("gstack")
    selected_keys = [key for key in ("gstack", "gsd", "superpowers") if key in selected_keys]

    names = [FRAMEWORKS[key].name for key in selected_keys]
    if len(names) == 1:
        label = names[0]
    else:
        label = "+".join(names)

    reason_bits = []
    if signals["has_security"] or signals["has_ux"]:
        reason_bits.append("direction, UX, security, or governance signals point to gstack")
    if signals["has_longterm"] or signals["complexity"] in {"medium", "high"}:
        reason_bits.append("larger scope or phase/state needs point to GSD")
    if signals["has_test"] or "superpowers" in selected_keys:
        reason_bits.append("execution quality and test discipline point to Superpowers")
    reason = "; ".join(reason_bits) or "default implementation request is ready for Superpowers-style execution"

    return {
        "selected_keys": selected_keys,
        "selected_label": label,
        "scores": scores,
        "signals": signals,
        "reason": reason,
    }


def _read_doc(path: Path, max_chars: int = 3500) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace").strip()[:max_chars]


def load_harness_knowledge(selected_keys: list[str]) -> str:
    parts = []
    readme = _read_doc(HARNESS_DIR / "README.md", 2500)
    if readme:
        parts.append(f"### Harness/README.md\n{readme}")
    router = _read_doc(HARNESS_DIR / "framework_router.md", 2500)
    if router:
        parts.append(f"### Harness/framework_router.md\n{router}")
    for key in selected_keys:
        doc = _read_doc(HARNESS_DIR / FRAMEWORKS[key].doc_name, 3000)
        if doc:
            parts.append(f"### Harness/{FRAMEWORKS[key].doc_name}\n{doc}")
    return "\n\n---\n\n".join(parts)


def _format_bool(value: bool) -> str:
    return "yes" if value else "no"


def build_development_brief(request_text: str, *, source_name: str = "") -> str:
    routed = route_framework(request_text)
    selected_keys = routed["selected_keys"]
    signals = routed["signals"]
    profiles = [FRAMEWORKS[key] for key in selected_keys]
    workflow = []
    agents = []
    codex_items = []
    for profile in profiles:
        workflow.extend(profile.workflow)
        agents.extend(profile.agents)
        codex_items.extend(profile.codex_focus)

    unique_workflow = list(dict.fromkeys(workflow))
    unique_agents = list(dict.fromkeys(agents))
    unique_codex = list(dict.fromkeys(codex_items))
    knowledge = load_harness_knowledge(selected_keys)
    task_lines = signals["task_lines"] or ["No explicit checklist lines detected; extract tasks from the user request first."]

    return (
        "## Harness Framework Routing\n"
        f"- Source: {source_name or 'AgentBus request'}\n"
        f"- Selected framework: {routed['selected_label']}\n"
        f"- Reason: {routed['reason']}\n"
        f"- Scores: {routed['scores']}\n"
        f"- Signals: tests={_format_bool(signals['has_test'])}, "
        f"longterm={_format_bool(signals['has_longterm'])}, "
        f"ux={_format_bool(signals['has_ux'])}, "
        f"security={_format_bool(signals['has_security'])}, "
        f"complexity={signals['complexity']}, scope_chars={signals['scope_size']}\n\n"
        "### Claude Code Development Direction\n"
        "- Treat this as a framework-routed implementation request.\n"
        "- Use the selected Harness workflow before writing code.\n"
        "- If a framework command/plugin is not installed, apply the methodology from the Obsidian knowledge base first; ask or report before network installs.\n"
        "- Produce a concise implementation plan, then execute within the JH role boundary.\n"
        "- Report changed files, verification commands, residual risks, and the selected framework.\n\n"
        "### Selected Workflow\n"
        + "\n".join(f"- {item}" for item in unique_workflow)
        + "\n\n### Agent Team Hints\n"
        + "\n".join(f"- {item}" for item in unique_agents)
        + "\n\n### Extracted Development Tasks\n"
        + "\n".join(f"- {item}" for item in task_lines)
        + "\n\n### Codex Review Checklist\n"
        + "\n".join(f"- {item}" for item in unique_codex)
        + "\n\n### Harness Knowledge Base Excerpts\n"
        + (knowledge or "Harness knowledge base files are not present; use built-in router profiles.")
    )


def build_codex_review_context(request_text: str) -> str:
    routed = route_framework(request_text)
    profiles = [FRAMEWORKS[key] for key in routed["selected_keys"]]
    codex_items = []
    for profile in profiles:
        codex_items.extend(profile.codex_focus)
    codex_items = list(dict.fromkeys(codex_items))
    return (
        "## Harness Framework Review Context\n"
        f"- Expected framework: {routed['selected_label']}\n"
        f"- Routing reason: {routed['reason']}\n"
        f"- Signals: {routed['signals']}\n\n"
        "### Codex should verify\n"
        + "\n".join(f"- {item}" for item in codex_items)
    )
