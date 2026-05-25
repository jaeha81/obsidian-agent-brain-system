#!/usr/bin/env python3
"""
Knowledge Gap Analyzer — ObsidianVault 지식 그래프 갭 감지기

목적:
  ObsidianVault 전체 .md 파일을 스캔하여 wikilink([[...]]) 기반 연결 그래프를 구축하고,
  지식 갭(고립 노드, 유령 노드, 약한 브릿지)을 감지한 뒤
  ObsidianVault/00_System/knowledge-gaps.md 에 저장하고
  JH-SHARED/00_SYSTEM/agent-room-messages.jsonl 에 태스크를 등록합니다.

Usage:
  python scripts/knowledge_gap_analyzer.py
  python scripts/knowledge_gap_analyzer.py --top 5
  python scripts/knowledge_gap_analyzer.py --dry-run
  python scripts/knowledge_gap_analyzer.py --no-queue

Requirements:
  pip install networkx
  (optional) pip install matplotlib
"""

from __future__ import annotations

import argparse
import io
import json
import os
import re
import sys
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# ── 윈도우 콘솔 UTF-8 ────────────────────────────────────────────────────────
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# ── 경로 설정 ────────────────────────────────────────────────────────────────
_ROOT = Path(__file__).parent.parent
VAULT = Path(os.getenv("VAULT_PATH", str(_ROOT / "ObsidianVault")))
GAPS_OUTPUT = VAULT / "00_System" / "knowledge-gaps.md"
AGENTBUS_QUEUE = Path(
    os.getenv(
        "AGENTBUS_QUEUE",
        r"G:\내 드라이브\JH-SHARED\00_SYSTEM\agent-room-messages.jsonl",
    )
)

# ── 갭 감지 임계값 ────────────────────────────────────────────────────────────
# betweenness centrality 가 이 값 이하인 노드를 "약한 브릿지" 후보로 봄
BRIDGE_CENTRALITY_THRESHOLD = 0.001
# 약한 브릿지는 최소 이 이상의 in+out degree 를 가져야 의미 있는 노드로 간주
BRIDGE_MIN_DEGREE = 2
# 스캔에서 제외할 폴더 접두사 (VAULT 기준 상대경로)
EXCLUDE_DIRS = {
    "graphify-out",
    ".obsidian",
    "00_UPGRADE",
}

# wikilink 정규식: [[대상]] 또는 [[대상|별칭]] 또는 [[대상#헤딩]]
_WIKILINK_RE = re.compile(r"\[\[([^\]|#\n]+?)(?:[|#][^\]]*?)?\]\]")


# ─────────────────────────────────────────────────────────────────────────────
# 1. 스캔 & 그래프 구축
# ─────────────────────────────────────────────────────────────────────────────

def _stem(path: Path) -> str:
    """노트 식별자: 파일명 (확장자 제거, 소문자)."""
    return path.stem.strip()


def scan_vault(vault: Path) -> tuple[dict[str, Path], dict[str, list[str]]]:
    """
    Returns:
        note_paths: {stem -> absolute Path}
        outlinks:   {stem -> [linked_stem, ...]}
    """
    note_paths: dict[str, Path] = {}
    outlinks: dict[str, list[str]] = defaultdict(list)

    for md_file in vault.rglob("*.md"):
        # 제외 폴더 필터
        rel = md_file.relative_to(vault)
        if any(str(rel).startswith(ex) for ex in EXCLUDE_DIRS):
            continue

        stem = _stem(md_file)
        note_paths[stem] = md_file

        try:
            content = md_file.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue

        for m in _WIKILINK_RE.finditer(content):
            target_raw = m.group(1).strip()
            # 경로 형식([[folder/note]]) → 마지막 세그먼트만 사용
            target_stem = Path(target_raw).stem.strip()
            if target_stem and target_stem != stem:
                outlinks[stem].append(target_stem)

    return note_paths, dict(outlinks)


# ─────────────────────────────────────────────────────────────────────────────
# 2. NetworkX 그래프 구축 + 갭 감지
# ─────────────────────────────────────────────────────────────────────────────

def build_graph(note_paths: dict[str, Path], outlinks: dict[str, list[str]]):
    """DiGraph 반환."""
    try:
        import networkx as nx
    except ImportError:
        print("[ERROR] networkx 미설치. pip install networkx 를 실행하세요.", file=sys.stderr)
        sys.exit(1)

    G = nx.DiGraph()

    # 실존 노드 추가
    for stem in note_paths:
        G.add_node(stem, exists=True, path=str(note_paths[stem]))

    # 엣지 추가 (유령 노드 포함)
    for src, targets in outlinks.items():
        for tgt in targets:
            if tgt not in G:
                G.add_node(tgt, exists=False, path=None)
            G.add_edge(src, tgt)

    return G


def detect_gaps(
    G,
    note_paths: dict[str, Path],
    top_n: int,
) -> dict:
    """
    Returns {
        'isolated':  [{'name': ..., 'path': ...}, ...],
        'ghost':     [{'name': ..., 'referenced_by': [...]}, ...],
        'weak_bridge': [{'name': ..., 'centrality': ..., 'degree': ..., 'path': ...}, ...],
    }
    """
    import networkx as nx

    isolated = []
    ghost = []
    weak_bridge_candidates = []

    in_deg = dict(G.in_degree())
    out_deg = dict(G.out_degree())

    # 고립 노드: 실존하고 in=0, out=0
    for stem, data in G.nodes(data=True):
        if data.get("exists", False):
            if in_deg.get(stem, 0) == 0 and out_deg.get(stem, 0) == 0:
                isolated.append({"name": stem, "path": data.get("path", "")})

    # 유령 노드: 실존하지 않지만 인링크가 1개 이상
    for stem, data in G.nodes(data=True):
        if not data.get("exists", True):
            refs = list(G.predecessors(stem))
            if refs:
                ghost.append({"name": stem, "referenced_by": refs[:5]})

    # 약한 브릿지: betweenness centrality 가 낮고 degree 가 최소치 이상인 실존 노드
    # 대규모 그래프에서 성능을 위해 undirected 로 변환 후 계산
    UG = G.to_undirected()
    if len(UG.nodes) > 0:
        try:
            centrality = nx.betweenness_centrality(UG, normalized=True)
        except Exception:
            centrality = {}

        for stem, c in centrality.items():
            node_data = G.nodes.get(stem, {})
            if not node_data.get("exists", False):
                continue
            total_deg = UG.degree(stem)
            if total_deg >= BRIDGE_MIN_DEGREE and c <= BRIDGE_CENTRALITY_THRESHOLD:
                weak_bridge_candidates.append(
                    {
                        "name": stem,
                        "centrality": round(c, 6),
                        "degree": total_deg,
                        "path": node_data.get("path", ""),
                    }
                )
        # centrality 오름차순 (가장 약한 브릿지 우선)
        weak_bridge_candidates.sort(key=lambda x: x["centrality"])

    # top_n 제한 (유령·고립·브릿지 각각)
    return {
        "isolated": isolated[:top_n],
        "ghost": ghost[:top_n],
        "weak_bridge": weak_bridge_candidates[:top_n],
    }


# ─────────────────────────────────────────────────────────────────────────────
# 3. knowledge-gaps.md 저장
# ─────────────────────────────────────────────────────────────────────────────

def _rel_path(abs_path: str, vault: Path) -> str:
    try:
        return str(Path(abs_path).relative_to(vault))
    except ValueError:
        return abs_path


def save_gaps_report(
    gaps: dict,
    note_paths: dict,
    outlinks: dict,
    G,
    vault: Path,
    output_path: Path,
    dry_run: bool,
) -> str:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    total_notes = sum(1 for _, d in G.nodes(data=True) if d.get("exists", False))
    total_links = G.number_of_edges()
    ghost_count = len(gaps["ghost"])
    isolated_count = len(gaps["isolated"])
    bridge_count = len(gaps["weak_bridge"])
    total_gaps = ghost_count + isolated_count + bridge_count

    lines = [
        "---",
        "tags:",
        "  - system",
        "  - knowledge-gap",
        f"generated: {ts}",
        "---",
        "",
        "# Knowledge Gap Report",
        "",
        f"> 생성: {ts}",
        "",
        "## 요약 통계",
        "",
        f"| 항목 | 값 |",
        f"|------|-----|",
        f"| 총 노트 수 | {total_notes} |",
        f"| 총 링크 수 | {total_links} |",
        f"| 고립 노드 (완전 고립) | {isolated_count} |",
        f"| 유령 노드 (언급만, 미문서화) | {ghost_count} |",
        f"| 약한 브릿지 노드 | {bridge_count} |",
        f"| **총 갭 수** | **{total_gaps}** |",
        "",
    ]

    # 고립 노드
    lines += [
        "## 고립 노드 (Isolated Notes)",
        "",
        "인링크도 아웃링크도 없는 완전히 단절된 노트입니다.",
        "",
    ]
    if gaps["isolated"]:
        lines += ["| 노트 | 경로 |", "|------|------|"]
        for item in gaps["isolated"]:
            rel = _rel_path(item["path"], vault) if item["path"] else "—"
            lines.append(f"| `{item['name']}` | `{rel}` |")
    else:
        lines.append("_고립 노드 없음_")
    lines.append("")

    # 유령 노드
    lines += [
        "## 유령 노드 (Ghost Notes)",
        "",
        "다른 노트에서 언급(wikilink)되지만 실제 파일이 존재하지 않는 개념입니다.",
        "",
    ]
    if gaps["ghost"]:
        lines += ["| 미문서화 개념 | 참조 노트 (최대 5개) |", "|--------------|----------------------|"]
        for item in gaps["ghost"]:
            refs = ", ".join(f"`{r}`" for r in item["referenced_by"])
            lines.append(f"| `{item['name']}` | {refs} |")
    else:
        lines.append("_유령 노드 없음_")
    lines.append("")

    # 약한 브릿지
    lines += [
        "## 약한 브릿지 노드 (Weak Bridge Notes)",
        "",
        f"클러스터 간 연결을 담당하지만 betweenness centrality ≤ {BRIDGE_CENTRALITY_THRESHOLD} 인 노드입니다.",
        "강화가 필요한 연결 고리 후보입니다.",
        "",
    ]
    if gaps["weak_bridge"]:
        lines += ["| 노트 | centrality | degree | 경로 |", "|------|-----------|--------|------|"]
        for item in gaps["weak_bridge"]:
            rel = _rel_path(item["path"], vault) if item["path"] else "—"
            lines.append(
                f"| `{item['name']}` | {item['centrality']:.6f} | {item['degree']} | `{rel}` |"
            )
    else:
        lines.append("_약한 브릿지 노드 없음_")
    lines.append("")

    content = "\n".join(lines)

    if not dry_run:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(content, encoding="utf-8")
        print(f"[OK] 갭 리포트 저장: {output_path}")
    else:
        print(f"[DRY-RUN] 저장 생략: {output_path}")

    return content


# ─────────────────────────────────────────────────────────────────────────────
# 4. AgentBus JSONL 큐 등록
# ─────────────────────────────────────────────────────────────────────────────

def _make_task(gap_type: str, name: str, meta: dict, top_n: int) -> dict:
    return {
        "id": str(uuid.uuid4()),
        "type": "knowledge_gap_fill",
        "created": datetime.now(timezone.utc).isoformat(),
        "source": "knowledge_gap_analyzer",
        "gap_type": gap_type,
        "note_name": name,
        "meta": meta,
        "priority": "P2",
        "status": "pending",
    }


def enqueue_tasks(gaps: dict, queue_path: Path, top_n: int, dry_run: bool) -> int:
    """갭 항목을 JSONL 큐에 추가. 등록된 태스크 수 반환."""
    tasks = []

    for item in gaps["isolated"]:
        tasks.append(
            _make_task(
                "isolated",
                item["name"],
                {"path": item["path"], "description": "고립 노드: 다른 노트와 연결 없음"},
                top_n,
            )
        )

    for item in gaps["ghost"]:
        tasks.append(
            _make_task(
                "ghost",
                item["name"],
                {
                    "referenced_by": item["referenced_by"],
                    "description": "유령 노드: 언급되지만 파일 미존재",
                },
                top_n,
            )
        )

    for item in gaps["weak_bridge"]:
        tasks.append(
            _make_task(
                "weak_bridge",
                item["name"],
                {
                    "path": item["path"],
                    "centrality": item["centrality"],
                    "degree": item["degree"],
                    "description": "약한 브릿지: 클러스터 간 연결이 취약함",
                },
                top_n,
            )
        )

    # top_n 전체 제한 (3개 유형 합산)
    tasks = tasks[:top_n]

    if not dry_run:
        queue_path.parent.mkdir(parents=True, exist_ok=True)
        with queue_path.open("a", encoding="utf-8") as f:
            for task in tasks:
                f.write(json.dumps(task, ensure_ascii=False) + "\n")
        print(f"[OK] AgentBus 큐 등록: {len(tasks)}개 → {queue_path}")
    else:
        print(f"[DRY-RUN] 큐 등록 생략: {len(tasks)}개 태스크")
        for t in tasks:
            print(f"  - [{t['gap_type']}] {t['note_name']}")

    return len(tasks)


# ─────────────────────────────────────────────────────────────────────────────
# 5. 요약 출력
# ─────────────────────────────────────────────────────────────────────────────

def print_summary(gaps: dict, note_paths: dict, G, enqueued: int) -> None:
    total_notes = sum(1 for _, d in G.nodes(data=True) if d.get("exists", False))
    total_ghost_in_graph = sum(
        1 for _, d in G.nodes(data=True) if not d.get("exists", True)
    )
    total_isolated = len(gaps["isolated"])
    total_weak = len(gaps["weak_bridge"])

    print()
    print("=" * 55)
    print("  Knowledge Gap Analyzer — 분석 완료")
    print("=" * 55)
    print(f"  총 노트 수          : {total_notes}")
    print(f"  총 유령 노드 (전체) : {total_ghost_in_graph}")
    print(f"  고립 노드 (감지)    : {total_isolated}")
    print(f"  유령 노드 (감지)    : {len(gaps['ghost'])}")
    print(f"  약한 브릿지 (감지)  : {total_weak}")
    print(f"  AgentBus 등록 태스크: {enqueued}")
    print("=" * 55)


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="ObsidianVault 지식 갭 감지 + AgentBus 등록"
    )
    parser.add_argument(
        "--top",
        type=int,
        default=10,
        metavar="N",
        help="상위 N개 갭만 AgentBus에 등록 (기본: 10)",
    )
    parser.add_argument(
        "--vault",
        type=str,
        default=None,
        help="Vault 경로 오버라이드 (기본: 환경변수 VAULT_PATH 또는 ObsidianVault/)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="갭 리포트 출력 경로 오버라이드",
    )
    parser.add_argument(
        "--queue",
        type=str,
        default=None,
        help="AgentBus JSONL 큐 경로 오버라이드",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="파일 저장/큐 등록 없이 결과만 출력",
    )
    parser.add_argument(
        "--no-queue",
        action="store_true",
        help="AgentBus 큐 등록 생략",
    )
    parser.add_argument(
        "--bridge-threshold",
        type=float,
        default=BRIDGE_CENTRALITY_THRESHOLD,
        metavar="T",
        help=f"betweenness centrality 임계값 (기본: {BRIDGE_CENTRALITY_THRESHOLD})",
    )
    return parser.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> None:
    args = parse_args(argv)

    vault = Path(args.vault) if args.vault else VAULT
    output_path = Path(args.output) if args.output else GAPS_OUTPUT
    queue_path = Path(args.queue) if args.queue else AGENTBUS_QUEUE
    top_n = args.top

    global BRIDGE_CENTRALITY_THRESHOLD
    BRIDGE_CENTRALITY_THRESHOLD = args.bridge_threshold

    print(f"[INFO] Vault: {vault}")
    print(f"[INFO] 출력:  {output_path}")
    print(f"[INFO] 큐:    {queue_path}")
    print(f"[INFO] --top: {top_n}")
    if args.dry_run:
        print("[INFO] DRY-RUN 모드 — 파일 저장/큐 등록 생략")
    print()

    # 1. 스캔
    print("[1/4] .md 파일 스캔 중...")
    note_paths, outlinks = scan_vault(vault)
    print(f"      → {len(note_paths)}개 노트 발견, {sum(len(v) for v in outlinks.values())}개 링크")

    # 2. 그래프 구축
    print("[2/4] 지식 그래프 구축 중...")
    G = build_graph(note_paths, outlinks)
    print(f"      → 노드 {G.number_of_nodes()}, 엣지 {G.number_of_edges()}")

    # 3. 갭 감지
    print("[3/4] 갭 감지 중 (betweenness centrality 계산 포함)...")
    gaps = detect_gaps(G, note_paths, top_n)
    print(
        f"      → 고립 {len(gaps['isolated'])}, 유령 {len(gaps['ghost'])}, "
        f"약한브릿지 {len(gaps['weak_bridge'])}"
    )

    # 4. 저장
    print("[4/4] 리포트 저장 및 큐 등록...")
    save_gaps_report(gaps, note_paths, outlinks, G, vault, output_path, args.dry_run)

    enqueued = 0
    if not args.no_queue:
        enqueued = enqueue_tasks(gaps, queue_path, top_n, args.dry_run)
    else:
        print("[INFO] --no-queue: AgentBus 등록 생략")

    # 요약
    print_summary(gaps, note_paths, G, enqueued)


if __name__ == "__main__":
    main()
