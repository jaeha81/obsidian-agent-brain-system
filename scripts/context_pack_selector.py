#!/usr/bin/env python3
"""Select minimal Obsidian context packs for agent routing."""

from __future__ import annotations

import argparse
import json


PACKS = {
    "review": {
        "primary_worker": "Codex Reviewer",
        "packs": ["Review Pack"],
        "notes": [
            "ObsidianVault/03_Projects/agents/codex-instructions.md",
            "ObsidianVault/03_Projects/agents/agent-house-role-map.md",
        ],
    },
    "implementation": {
        "primary_worker": "ClaudeCode Builder",
        "packs": ["Implementation Pack"],
        "notes": [
            "ObsidianVault/03_Projects/agents/agent-house-role-map.md",
            "ObsidianVault/05_Frameworks/guides/context-pack-index.md",
        ],
    },
    "discord": {
        "primary_worker": "Bucky Operator",
        "packs": ["Discord Pipeline Pack"],
        "notes": [
            "ObsidianVault/05_Frameworks/guides/discord-fallback-pipeline.md",
            "ObsidianVault/05_Frameworks/AgentBus/agentbus_protocol.md",
        ],
    },
    "sync": {
        "primary_worker": "Sync Sentinel",
        "packs": ["PC Sync Pack"],
        "notes": [
            "ObsidianVault/05_Frameworks/guides/multi-pc-sync-sentinel.md",
            "ObsidianVault/05_Frameworks/guides/pc-detection.md",
        ],
    },
    "graph": {
        "primary_worker": "Knowledge Curator",
        "packs": ["Graph Cleanup Pack"],
        "notes": [
            "ObsidianVault/00_UPGRADE/graph-operating-principle.md",
            "ObsidianVault/03_Projects/agents/agent-house-role-map.md",
        ],
    },
    "legacy": {
        "primary_worker": "Knowledge Curator",
        "packs": ["Legacy Absorption Pack"],
        "notes": [
            "ObsidianVault/00_UPGRADE/obsidian-brain-stabilization-and-agent-house-master-plan-2026-05-27.md",
            "ObsidianVault/05_Frameworks/guides/context-pack-index.md",
        ],
    },
}


def _infer_key(task_type: str, body: str) -> str:
    task = (task_type or "").lower()
    text = f"{task}\n{body or ''}".lower()
    if "review" in task or "검수" in text or "review" in text or "verify" in text:
        return "review"
    if "implementation" in task or "구현" in text or "수정" in text or "build" in text:
        return "implementation"
    if "discord" in text or "디스코드" in text or "fallback" in text:
        return "discord"
    if "pc" in text or "사무실" in text or "노트북" in text or "github" in text or "동기화" in text:
        return "sync"
    if "graph" in text or "graphify" in text or "그래프" in text:
        return "graph"
    if "legacy" in text or "이전 시스템" in text or "흡수" in text or "archive" in text:
        return "legacy"
    return "implementation"


def select_context_pack(*, task_type: str, body: str) -> dict:
    key = _infer_key(task_type, body)
    selection = dict(PACKS[key])
    selection["key"] = key
    return selection


def main() -> int:
    parser = argparse.ArgumentParser(description="Select a lightweight context pack for a task.")
    parser.add_argument("--task-type", default="general")
    parser.add_argument("body", nargs="*", help="Task body text.")
    args = parser.parse_args()

    selection = select_context_pack(task_type=args.task_type, body=" ".join(args.body))
    print(json.dumps(selection, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
