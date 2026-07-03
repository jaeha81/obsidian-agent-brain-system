#!/usr/bin/env python3
"""
AgentBus Graphify Bridge — converts graphify output to AgentBus context_request message.

Reads GRAPH_REPORT.md (or derives stats from graphify-out/) and writes a structured
AgentBus message to ObsidianVault/10_AgentBus/context_requests/graphify/.

Optionally generates a Graphify Context Pack via graphify_context_pack.py.

Usage:
    python scripts/agentbus_graphify_bridge.py \\
        --project ObsidianVault \\
        --graph graphify-out \\
        --context-pack ObsidianVault/06_Context_Packs/Graphify/ObsidianVault_graphify_pack.md

NOTE: graph.json is never read or included in messages.
"""

import argparse
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent.parent
AGENTBUS_DIR = ROOT / "ObsidianVault" / "10_AgentBus"
ALLOWED_CONTEXT_PACK_ROOT = ROOT / "ObsidianVault" / "06_Context_Packs"


def _safe_resolve(candidate: Path, allowed_root: Path) -> Path | None:
    try:
        resolved = candidate.resolve()
        if resolved.is_relative_to(allowed_root.resolve()):
            return resolved
    except (OSError, ValueError):
        pass
    return None


def parse_graph_stats(graph_dir: Path) -> dict:
    stats = {"nodes": "N/A", "edges": "N/A", "clusters": "N/A", "isolated": "N/A"}
    report = graph_dir / "GRAPH_REPORT.md"
    if not report.exists():
        return stats
    for line in report.read_text(encoding="utf-8", errors="ignore").splitlines():
        lower = line.lower()
        if "isolated" in lower and ":" in line:
            stats["isolated"] = line.split(":")[-1].strip()
        elif "node" in lower and ":" in line:
            stats["nodes"] = line.split(":")[-1].strip()
        elif "edge" in lower and ":" in line:
            stats["edges"] = line.split(":")[-1].strip()
        elif "cluster" in lower and ":" in line:
            stats["clusters"] = line.split(":")[-1].strip()
    return stats


def write_request_message(project: str, graph_dir: Path, context_pack_path: str, stats: dict) -> Path:
    now = datetime.now()
    ts = now.strftime("%Y%m%d_%H%M%S")
    iso = now.isoformat(timespec="seconds")

    out_dir = AGENTBUS_DIR / "context_requests" / "graphify"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{ts}_graphify_request.md"

    try:
        graph_dir_display = graph_dir.relative_to(ROOT)
    except ValueError:
        graph_dir_display = graph_dir.name

    content = f"""---
type: context_request
source: graphify
project: {project}
graph_dir: {graph_dir_display}
context_pack: {context_pack_path}
status: pending
created: {iso}
---

## Request

Graphify build completed for project **{project}**.

| 항목 | 값 |
|------|----|
| 노드 수 | {stats['nodes']} |
| 엣지 수 | {stats['edges']} |
| 클러스터 수 | {stats['clusters']} |
| 고립 노드 수 | {stats['isolated']} |

## Context Pack Path

`{context_pack_path}`

## Notes

- graph.json 원본 포함 금지 — Context Pack만 참조
- 분석 요청 시 `scripts/graphify_query.sh` 사용
"""
    out_path.write_text(content, encoding="utf-8")
    return out_path


def ensure_context_pack(project: str, graph_dir: Path, context_pack: str) -> bool:
    pack_path = ROOT / context_pack
    if pack_path.exists():
        return True

    script = ROOT / "scripts" / "graphify_context_pack.py"
    if not script.exists():
        print(f"WARNING: {script} not found — skipping context pack generation", file=sys.stderr)
        return False

    cmd = [
        sys.executable, str(script),
        "--project", project,
        "--graph", str(graph_dir),
        "--output", context_pack,
    ]
    try:
        result = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, timeout=30)
    except (subprocess.TimeoutExpired, OSError) as e:
        print(f"WARNING: graphify_context_pack.py failed: {e}", file=sys.stderr)
        return False
    if result.returncode != 0:
        print(f"WARNING: graphify_context_pack.py failed:\n{result.stderr}", file=sys.stderr)
        return False
    print(result.stdout.strip())
    return True


def main():
    parser = argparse.ArgumentParser(description="AgentBus Graphify Bridge")
    parser.add_argument("--project", required=True, help="Project name (e.g. ObsidianVault)")
    parser.add_argument("--graph", required=True,
                        help="Path to graphify output dir containing GRAPH_REPORT.md")
    parser.add_argument("--context-pack", default=None,
                        help="Context pack output path (relative to project root). "
                             "Defaults to ObsidianVault/06_Context_Packs/Graphify/{project}_graphify_pack.md")
    args = parser.parse_args()

    if not re.match(r'^[A-Za-z0-9_-]{1,64}$', args.project):
        print(f"ERROR: --project must match [A-Za-z0-9_-]{{1,64}}: {args.project!r}", file=sys.stderr)
        sys.exit(1)

    graph_dir = ROOT / args.graph if not Path(args.graph).is_absolute() else Path(args.graph)
    if _safe_resolve(graph_dir, ROOT) is None:
        print(f"ERROR: --graph must be within project root: {args.graph}", file=sys.stderr)
        sys.exit(1)
    if not graph_dir.exists():
        print(f"ERROR: graph dir not found: {graph_dir}", file=sys.stderr)
        sys.exit(1)

    context_pack = args.context_pack or f"ObsidianVault/06_Context_Packs/Graphify/{args.project}_graphify_pack.md"

    context_pack_candidate = Path(context_pack)
    if not context_pack_candidate.is_absolute():
        context_pack_candidate = ROOT / context_pack_candidate
    if _safe_resolve(context_pack_candidate, ALLOWED_CONTEXT_PACK_ROOT) is None:
        print(f"ERROR: --context-pack must be within ObsidianVault/06_Context_Packs/: {context_pack}", file=sys.stderr)
        sys.exit(1)

    if not ensure_context_pack(args.project, graph_dir, context_pack):
        print("WARNING: Context pack generation failed — proceeding without context pack", file=sys.stderr)

    stats = parse_graph_stats(graph_dir)
    msg_path = write_request_message(args.project, graph_dir, context_pack, stats)
    print(f"AgentBus message written: {msg_path}")


if __name__ == "__main__":
    main()
