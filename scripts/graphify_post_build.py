#!/usr/bin/env python3
"""
Graphify Post-Build — generates GRAPH_REPORT.md from graphify output files.

Reads graph.json and .graphify_analysis.json to extract stats, then writes
a human-readable GRAPH_REPORT.md. Called automatically by graphify_build.sh.

Usage:
    python scripts/graphify_post_build.py <graphify-out-dir>

Example:
    python scripts/graphify_post_build.py ObsidianVault/graphify-out
"""

import json
import sys
from datetime import datetime
from pathlib import Path


def count_isolated(nodes: list, links: list) -> int:
    """Return count of nodes that appear in no edge."""
    connected = set()
    for link in links:
        connected.add(link.get("source"))
        connected.add(link.get("target"))
    node_ids = {n["id"] for n in nodes if "id" in n}
    return len(node_ids - connected)


def load_graph_stats(graph_dir: Path) -> dict:
    graph_file = graph_dir / "graph.json"
    analysis_file = graph_dir / ".graphify_analysis.json"

    stats = {"nodes": 0, "edges": 0, "clusters": 0, "isolated": 0, "error": None}

    if not graph_file.exists():
        stats["error"] = f"graph.json not found in {graph_dir}"
        return stats

    with graph_file.open(encoding="utf-8") as f:
        graph = json.load(f)

    nodes = graph.get("nodes", [])
    # networkx JSON uses "links"; fallback to "edges"
    links = graph.get("links", graph.get("edges", []))

    stats["nodes"] = len(nodes)
    stats["edges"] = len(links)
    stats["isolated"] = count_isolated(nodes, links)

    if analysis_file.exists():
        with analysis_file.open(encoding="utf-8") as f:
            analysis = json.load(f)
        stats["clusters"] = len(analysis.get("communities", {}))

    return stats


def write_report(graph_dir: Path, source_path: str, stats: dict) -> Path:
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    report_path = graph_dir / "GRAPH_REPORT.md"

    lines = [
        "# Graphify Graph Report",
        f"> Generated: {now} | Source: {source_path}",
        "",
        "## Stats",
        "",
        f"- Nodes: {stats['nodes']}",
        f"- Edges: {stats['edges']}",
        f"- Clusters: {stats['clusters']}",
        f"- Isolated: {stats['isolated']}",
        "",
        "## Build Info",
        "",
        "| 항목 | 값 |",
        "|------|-----|",
        f"| 빌드 일시 | {now} |",
        f"| 입력 경로 | {source_path} |",
        f"| 출력 경로 | {graph_dir} |",
        "",
        "## Communities",
        "",
        f"{stats['clusters']}개 커뮤니티 감지됨. 상세 내용은 graph.json 참조 (LLM 프롬프트 포함 금지).",
    ]

    if stats.get("error"):
        lines.append("")
        lines.append(f"> ERROR: {stats['error']}")

    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report_path


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/graphify_post_build.py <graphify-out-dir>")
        sys.exit(1)

    graph_dir = Path(sys.argv[1])
    # derive source path label from parent of graphify-out dir
    source_path = graph_dir.parent.name + "/"

    if not graph_dir.is_dir():
        print(f"Error: {graph_dir} is not a directory")
        sys.exit(1)

    stats = load_graph_stats(graph_dir)

    if stats.get("error"):
        print(f"Warning: {stats['error']} — writing partial report")

    report_path = write_report(graph_dir, source_path, stats)
    print(f"GRAPH_REPORT.md written: {report_path}")
    print(f"  Nodes: {stats['nodes']}, Edges: {stats['edges']}, Clusters: {stats['clusters']}, Isolated: {stats['isolated']}")


if __name__ == "__main__":
    main()
