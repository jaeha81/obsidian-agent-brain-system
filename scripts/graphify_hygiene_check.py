#!/usr/bin/env python3
"""Fail when Graphify output contains vault-noise source paths."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path


DEFAULT_FORBIDDEN_PREFIXES = (
    ".obsidian/",
    "01_RAW/",
    "09_Archive/",
    "10_AgentBus/",
    "00_UPGRADE/",
    "graphify-out/",
    "00_Inbox/DiscordCaptures/",
)


def _normalise(path: str) -> str:
    return path.replace("\\", "/").lstrip("./")


def check_graph(graph_path: Path, forbidden_prefixes: tuple[str, ...]) -> tuple[int, Counter[str]]:
    with graph_path.open(encoding="utf-8") as f:
        graph = json.load(f)

    offenders: Counter[str] = Counter()
    for node in graph.get("nodes", []):
        source_file = _normalise(str(node.get("source_file") or ""))
        for prefix in forbidden_prefixes:
            if source_file.startswith(prefix):
                offenders[prefix] += 1
                break

    return len(graph.get("nodes", [])), offenders


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "graph",
        nargs="?",
        default="ObsidianVault/graphify-out/graph.json",
        help="Path to graph.json",
    )
    parser.add_argument(
        "--forbid",
        action="append",
        default=[],
        help="Additional forbidden source_file prefix. Repeatable.",
    )
    args = parser.parse_args()

    graph_path = Path(args.graph)
    if not graph_path.is_file():
        print(f"ERROR: graph not found: {graph_path}", file=sys.stderr)
        return 2

    extra_prefixes = tuple(_normalise(p).rstrip("/") + "/" for p in args.forbid)
    prefixes = DEFAULT_FORBIDDEN_PREFIXES + extra_prefixes
    total_nodes, offenders = check_graph(graph_path, prefixes)

    if offenders:
        print(f"FAIL: {graph_path} contains forbidden Graphify source paths.")
        print(f"Total nodes: {total_nodes}")
        for prefix, count in offenders.most_common():
            print(f"- {prefix}: {count} nodes")
        return 1

    print(f"PASS: {graph_path} has no forbidden Graphify source paths. Nodes: {total_nodes}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
