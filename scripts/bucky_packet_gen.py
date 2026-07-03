#!/usr/bin/env python3
"""
bucky_packet_gen.py — Bucky 지침 패킷 빠른 생성 CLI

사용법:
    python scripts/bucky_packet_gen.py --project wishket-automation --goal "Wishket 에이전트 E2E 테스트" --agent ClaudeCode
    python scripts/bucky_packet_gen.py --interactive
    python scripts/bucky_packet_gen.py --from-context-pack "Claude Code new project implementation"
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VAULT = ROOT / "ObsidianVault"
TEMPLATE = VAULT / "_templates" / "bucky-packet.md"
PACKETS_DIR = VAULT / "06_Context_Packs" / "packets"

# context_pack_selector가 있으면 팩 선택에 활용
try:
    sys.path.insert(0, str(ROOT / "scripts"))
    import context_pack_selector
    _SELECTOR_AVAILABLE = True
except ImportError:
    _SELECTOR_AVAILABLE = False


def _date() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def _iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _ask(prompt: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    val = input(f"{prompt}{suffix}: ").strip()
    return val or default


def build_packet(
    project: str,
    goal: str,
    agent: str = "ClaudeCode",
    baseline: str = "현재 상태 미확인",
    target_state: str = "목표 상태 미지정",
    scope: str = "현재 프로젝트 파일만",
    role: str = "구현/운영",
    constraints: list[str] | None = None,
    context_packs: list[str] | None = None,
    references: list[str] | None = None,
    user_context: list[str] | None = None,
    latent_asset: dict[str, str] | None = None,
    source_trace: list[str] | None = None,
    verification: str = "python -X utf8 scripts/preflight_check.py",
    done_when: str = "검증 명령 통과 + 사용자 확인",
    record_path: str = "ObsidianVault/10_AgentBus/completed/",
    next_action: str = "다음 단계 기입",
) -> str:
    constraints = constraints or ["커밋·푸시는 사용자 명시 승인 후", "파일 삭제·이동은 dry-run 먼저"]
    context_packs = context_packs or ["ObsidianVault/00_System/BUCKY_OS_RUNBOOK.md"]
    references = references or ["ObsidianVault/00_System/BUCKY_CONTEXT.md"]

    if "ObsidianVault/06_Context_Packs/oabs-llm-wiki-upgrade-pack.md" in context_packs:
        user_context = user_context or [
            "Preserve user intent and accumulated project history before optimizing dispatch speed.",
            "Use ObsidianVault, LLM Wiki notes, Graphify, and Context Packs as source-backed memory.",
            "Treat older GitHub repositories as latent-project assets unless evidence says otherwise.",
        ]
        latent_asset = latent_asset or {
            "asset_type": "unknown",
            "growth_stage": "unknown",
            "current_status": "unknown",
            "latent_value": "unknown",
            "next_possible_use": "classify from exact repo, note, or graph evidence before judging",
        }
        source_trace = source_trace or [
            "ObsidianVault/00_System/oabs-second-brain-charter.md",
            "ObsidianVault/00_System/user-evolution-model.md",
            "ObsidianVault/00_System/bucky-user-understanding-agent.md",
            "ObsidianVault/06_Context_Packs/oabs-llm-wiki-upgrade-pack.md",
        ]

    c_lines = "\n".join(f"- {c}" for c in constraints)
    cp_lines = "\n".join(f"- {c}" for c in context_packs)
    ref_lines = "\n".join(f"- {r}" for r in references)
    user_context_section = ""
    if user_context:
        user_context_section = "\n## user_context\n" + "\n".join(f"- {item}" for item in user_context) + "\n"
    latent_asset_section = ""
    if latent_asset:
        latent_asset_section = "\n## latent_asset\n" + "\n".join(f"{key}: {value}" for key, value in latent_asset.items()) + "\n"
    source_trace_section = ""
    if source_trace:
        source_trace_section = "\n## source_trace\n" + "\n".join(f"- {item}" for item in source_trace) + "\n"

    return f"""---
type: bucky-packet
project: "{project}"
agent: "{agent}"
created: "{_date()}"
status: draft
---

# Bucky 지침 패킷 — {project}

생성: {_iso()}

---

## goal
{goal}

## baseline
{baseline}

## target_state
{target_state}

## scope
{scope}

## role
{role}

## constraints
{c_lines}

## context_packs
{cp_lines}

## references
{ref_lines}
{user_context_section}{latent_asset_section}{source_trace_section}
## verification
```
{verification}
```

## done_when
{done_when}

## record_path
{record_path}

## next_action
{next_action}
"""


def interactive_mode() -> dict:
    print("\n=== Bucky 패킷 생성 (대화형) ===\n")
    return {
        "project": _ask("프로젝트/레포 이름"),
        "goal": _ask("목표 (1~2줄)"),
        "agent": _ask("에이전트", "ClaudeCode"),
        "baseline": _ask("현재 상태", "현재 상태 미확인"),
        "target_state": _ask("목표 상태", "목표 상태 미지정"),
        "scope": _ask("허용 범위", "현재 프로젝트 파일만"),
        "role": _ask("역할", "구현/운영"),
        "verification": _ask("검증 명령", "python -X utf8 scripts/preflight_check.py"),
        "done_when": _ask("완료 조건", "검증 명령 통과 + 사용자 확인"),
        "next_action": _ask("즉각 첫 행동"),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Bucky 지침 패킷 생성")
    ap.add_argument("--project", "-p", help="프로젝트/레포 이름")
    ap.add_argument("--goal", "-g", help="목표 설명")
    ap.add_argument("--agent", "-a", default="ClaudeCode", help="대상 에이전트")
    ap.add_argument("--baseline", default="현재 상태 미확인")
    ap.add_argument("--target-state", default="목표 상태 미지정")
    ap.add_argument("--scope", default="현재 프로젝트 파일만")
    ap.add_argument("--role", default="구현/운영")
    ap.add_argument("--verification", default="python -X utf8 scripts/preflight_check.py")
    ap.add_argument("--done-when", default="검증 명령 통과 + 사용자 확인")
    ap.add_argument("--next-action", default="다음 단계 기입")
    ap.add_argument("--interactive", "-i", action="store_true", help="대화형 입력")
    ap.add_argument("--from-context-pack", metavar="TASK", help="context_pack_selector로 팩 자동 선택")
    ap.add_argument("--output", "-o", help="저장 경로 (기본: 화면 출력)")
    args = ap.parse_args()

    if args.interactive:
        params = interactive_mode()
    else:
        if not args.project or not args.goal:
            ap.print_help()
            print("\n오류: --project 와 --goal 은 필수입니다.")
            return 1
        params = {
            "project": args.project,
            "goal": args.goal,
            "agent": args.agent,
            "baseline": args.baseline,
            "target_state": args.target_state,
            "scope": args.scope,
            "role": args.role,
            "verification": args.verification,
            "done_when": args.done_when,
            "next_action": args.next_action,
        }

    # context_pack_selector 연동
    if args.from_context_pack and _SELECTOR_AVAILABLE:
        selected = context_pack_selector.select_context_pack(task_type="gate", body=args.from_context_pack)
        params["context_packs"] = selected.get("packs", [])

    content = build_packet(**params)

    if args.output:
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(content, encoding="utf-8")
        print(f"✅ 패킷 저장: {out}")
    else:
        print(content)

    return 0


if __name__ == "__main__":
    sys.exit(main())

