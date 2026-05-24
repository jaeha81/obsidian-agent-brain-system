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
import re
import sys
from collections import defaultdict
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




_AUTO_START = "<!-- graphify-auto-start -->"
_AUTO_END = "<!-- graphify-auto-end -->"


def _inject_related_section(md_file: Path, related_files: list[Path], vault_root: Path) -> bool:
    """md_file 하단의 graphify 자동 생성 마커 블록만 갱신한다. 수동 작성 내용 보존."""
    content = md_file.read_text(encoding="utf-8", errors="ignore")
    links_text = "\n".join(
        f"- [[{f.stem}]]" for f in sorted(related_files, key=lambda x: x.stem)
    )
    new_block = f"{_AUTO_START}\n## Related (auto)\n\n{links_text}\n{_AUTO_END}"

    if _AUTO_START in content and _AUTO_END in content:
        content = re.sub(
            re.escape(_AUTO_START) + r"[\s\S]*?" + re.escape(_AUTO_END),
            new_block,
            content,
        )
    else:
        content = content.rstrip() + "\n\n" + new_block + "\n"

    md_file.write_text(content, encoding="utf-8")
    return True


def _tag_orphan(md_file: Path) -> None:
    """고립 노드 .md 파일의 frontmatter에 orphan 태그를 추가한다."""
    content = md_file.read_text(encoding="utf-8", errors="ignore")
    if "orphan" in content[:500]:
        return
    # YAML frontmatter에 태그 삽입
    if content.startswith("---"):
        end = content.find("\n---", 3)
        if end != -1:
            fm_block = content[:end + 4]
            rest = content[end + 4:]
            if "tags:" in fm_block:
                fm_block = re.sub(r"(tags:.*)", r"\1\n  - orphan", fm_block, count=1)
            else:
                fm_block = fm_block.rstrip("\n") + "\ntags:\n  - orphan\n"
            md_file.write_text(fm_block + rest, encoding="utf-8")
    else:
        md_file.write_text(f"---\ntags:\n  - orphan\n---\n\n{content}", encoding="utf-8")


_WIKILINK_RE = re.compile(r"\[\[([^\]|#]+?)(?:\|[^\]]*)?\]\]")
_SKIP_DIRS = {"graphify-out", ".obsidian", ".git", "00_UPGRADE"}


def _build_wikilink_adjacency(vault_root: Path) -> tuple[dict[Path, set[Path]], dict[str, Path]]:
    """Vault의 [[wikilink]]를 파싱해 역링크 맵과 stem→Path 인덱스를 반환한다."""
    # stem → Path 인덱스 (대소문자 무시)
    stem_index: dict[str, Path] = {}
    all_md = [
        p for p in vault_root.rglob("*.md")
        if not any(d in p.parts for d in _SKIP_DIRS)
    ]
    for p in all_md:
        stem_index[p.stem.lower()] = p

    # 정방향 링크 맵
    forward: dict[Path, set[Path]] = defaultdict(set)
    for md_file in all_md:
        try:
            content = md_file.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for m in _WIKILINK_RE.finditer(content):
            target_stem = Path(m.group(1).strip()).stem.lower()
            target_path = stem_index.get(target_stem)
            if target_path and target_path != md_file:
                forward[md_file].add(target_path)

    # 역방향 링크 맵 (backlinks)
    backward: dict[Path, set[Path]] = defaultdict(set)
    for src, targets in forward.items():
        for tgt in targets:
            backward[tgt].add(src)

    return backward, stem_index


def inject_obsidian_backlinks(graph_dir: Path, vault_root: Path,
                               top_k: int = 8, min_backlinks: int = 2) -> dict:
    """[[wikilink]] 역파싱으로 .md 파일에 Backlinks 섹션과 orphan 태그를 삽입한다.

    graphify 코드 그래프는 코드 심볼 레벨 분석이라 .md 간 직접 엣지가 없다.
    대신 Vault 내 [[wikilink]] 를 직접 파싱해 역링크를 계산한다.
    """
    backward, stem_index = _build_wikilink_adjacency(vault_root)
    all_md = [
        p for p in vault_root.rglob("*.md")
        if not any(d in p.parts for d in _SKIP_DIRS)
    ]

    injected = 0
    orphans_tagged = 0

    for md_file in all_md:
        backlinkers = backward.get(md_file, set())
        top_bl = sorted(backlinkers, key=lambda f: len(backward.get(f, set())), reverse=True)[:top_k]

        if len(top_bl) >= min_backlinks:
            try:
                _inject_related_section(md_file, top_bl, vault_root)
                injected += 1
            except Exception as e:
                print(f"  [PostBuild] 역링크 삽입 실패 {md_file.name}: {e}")
        elif not backlinkers and md_file not in {p for srcs in backward.values() for p in srcs}:
            # 아무도 링크하지 않고 자신도 아무것도 링크하지 않는 고립 파일
            try:
                _tag_orphan(md_file)
                orphans_tagged += 1
            except Exception as e:
                print(f"  [PostBuild] orphan 태깅 실패 {md_file.name}: {e}")

    return {"injected": injected, "orphans_tagged": orphans_tagged}


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/graphify_post_build.py <graphify-out-dir> [--backlinks]")
        sys.exit(1)

    graph_dir = Path(sys.argv[1])
    inject_backlinks = "--backlinks" in sys.argv
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

    if inject_backlinks:
        vault_root = graph_dir.parent
        print("Injecting Obsidian backlinks...")
        result = inject_obsidian_backlinks(graph_dir, vault_root)
        if "skipped" in result:
            print(f"  [PostBuild] 역링크 스킵: {result['skipped']}")
        else:
            print(f"  [PostBuild] 역링크 삽입: {result['injected']}개 파일, orphan 태깅: {result['orphans_tagged']}개")


if __name__ == "__main__":
    main()
