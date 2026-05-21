#!/usr/bin/env python3
"""
Generate a Graphify Context Pack from a built graph.
Reads GRAPH_REPORT.md from the graph output directory and produces
a structured Markdown context pack for agent consumption.

Usage:
    python scripts/graphify_context_pack.py \\
        --project PROJECT_NAME \\
        --graph external_data/graphify_selected/PROJECT/ \\
        --output ObsidianVault/06_Context_Packs/Graphify/PROJECT_graphify_pack.md

    Optional: --query "question" to include a query result section.
"""

import argparse
import os
import sys
from datetime import datetime
from pathlib import Path


def read_graph_report(graph_dir: Path) -> str:
    report_path = graph_dir / "GRAPH_REPORT.md"
    if not report_path.exists():
        sys.exit(f"ERROR: GRAPH_REPORT.md not found in {graph_dir}")
    return report_path.read_text(encoding="utf-8")


def parse_stats(report_text: str) -> dict:
    """Extract basic stats from GRAPH_REPORT.md via simple line scanning."""
    stats = {
        "nodes": "N/A",
        "edges": "N/A",
        "clusters": "N/A",
        "isolated": "N/A",
        "hubs": "N/A",
    }
    for line in report_text.splitlines():
        lower = line.lower()
        if "node" in lower and ":" in line:
            stats["nodes"] = line.split(":")[-1].strip()
        elif "edge" in lower and ":" in line:
            stats["edges"] = line.split(":")[-1].strip()
        elif "cluster" in lower and ":" in line:
            stats["clusters"] = line.split(":")[-1].strip()
        elif "isolated" in lower and ":" in line:
            stats["isolated"] = line.split(":")[-1].strip()
        elif "hub" in lower and ":" in line:
            stats["hubs"] = line.split(":")[-1].strip()
    return stats


def check_graph_size(graph_dir: Path) -> tuple[float, str]:
    total = sum(f.stat().st_size for f in graph_dir.rglob("*") if f.is_file())
    mb = total / (1024 * 1024)
    warning = " ⚠️ >500MB — review before committing" if mb > 500 else ""
    return mb, warning


def build_context_pack(project: str, graph_dir: Path, report_text: str,
                       query_result: str | None) -> str:
    stats = parse_stats(report_text)
    size_mb, size_warning = check_graph_size(graph_dir)
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    query_section = ""
    if query_result:
        query_section = f"\n## 6. 쿼리 결과 요약\n\n{query_result}\n"

    return f"""# Graphify Context Pack — {project}
> Generated: {now} | Source: {graph_dir}

---

## 1. 프로젝트 정보

| 항목 | 값 |
|------|-----|
| 프로젝트 이름 | {project} |
| 그래프 경로 | {graph_dir} |
| 그래프 크기 | {size_mb:.1f} MB{size_warning} |
| 빌드 날짜 | {now} |

---

## 2. 그래프 통계

| 항목 | 값 |
|------|-----|
| 노드 수 | {stats['nodes']} |
| 엣지 수 | {stats['edges']} |
| 클러스터 수 | {stats['clusters']} |
| 고립 노드 수 | {stats['isolated']} |
| 허브 노드 수 | {stats['hubs']} |

---

## 3. GRAPH_REPORT 요약

{report_text[:2000]}{"..." if len(report_text) > 2000 else ""}

---
{query_section}
## 소스 참조

- GRAPH_REPORT: `{graph_dir}/GRAPH_REPORT.md`
- 쿼리 패턴: `ObsidianVault/05_Frameworks/Graphify/graphify_query_patterns.md`
- 생성 스크립트: `scripts/graphify_context_pack.py`

---

> **참고**: graph.json 원본은 이 Context Pack에 포함되지 않습니다.
"""


def main():
    parser = argparse.ArgumentParser(description="Generate Graphify Context Pack")
    parser.add_argument("--project", required=True, help="Project name")
    parser.add_argument("--graph", required=True, help="Path to graph output directory")
    parser.add_argument("--output", required=True, help="Output .md file path")
    parser.add_argument("--query", default=None, help="Optional query result to include")
    args = parser.parse_args()

    graph_dir = Path(args.graph)
    if not graph_dir.exists():
        sys.exit(f"ERROR: Graph directory not found: {graph_dir}")

    report_text = read_graph_report(graph_dir)
    content = build_context_pack(args.project, graph_dir, report_text, args.query)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding="utf-8")
    print(f"Context Pack written to: {output_path}")


if __name__ == "__main__":
    main()
