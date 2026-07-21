#!/usr/bin/env python3
"""
Vault Node Deduplicator — Bucky 서브에이전트
Obsidian Vault 내 중복/유사 노드를 감지하고 병합 후보를 제안한다.

주요 기능:
1. 제목 중복 감지 (완전 동일 + 유사도 80% 이상)
2. 법률/legal 키워드 클러스터 집중 분석
3. 고아 노드 (wikilink 참조 없는 노드) 감지
4. 병합 후보 리포트 → ObsidianVault/00_System/dedup-report-YYYY-MM-DD.md

사용법:
  python vault_node_deduplicator.py              # 전체 분석
  python vault_node_deduplicator.py --cluster 법률  # 특정 클러스터만
  python vault_node_deduplicator.py --auto-merge    # 완전 동일 제목만 자동 병합
  python vault_node_deduplicator.py --dry-run       # 리포트만 (파일 수정 없음)
"""

import argparse
import difflib
import os
import re
import sys
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# 환경 설정
# ---------------------------------------------------------------------------

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv 미설치 시 무시

DEFAULT_VAULT_PATH = os.environ.get(
    "VAULT_PATH",
    "D:/ai프로젝트/obsidian-agent-brain-system/ObsidianVault",
)

LEGAL_PATTERN = re.compile(
    r"법률|법규|규정|조항|법령|계약|소송|판례|법원|변호|legal|law",
    re.IGNORECASE,
)

WIKILINK_PATTERN = re.compile(r"\[\[([^\[\]|#]+?)(?:[|#][^\[\]]*?)?\]\]")
FRONTMATTER_TITLE_PATTERN = re.compile(r"^title\s*:\s*(.+)$", re.MULTILINE)
SIMILARITY_THRESHOLD = 0.80


# ---------------------------------------------------------------------------
# 유틸
# ---------------------------------------------------------------------------


def normalize_title(title: str) -> str:
    """비교용 정규화: 소문자, 공백·특수문자 제거."""
    return re.sub(r"[\s\-_.,;:!?()'\"/\\]+", "", title).lower()


def extract_title(md_path: Path) -> str:
    """frontmatter title → 없으면 파일명(확장자 제거)."""
    try:
        text = md_path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return md_path.stem

    # frontmatter 블록 내 title 필드만 검색
    frontmatter_match = re.match(r"^---\s*\n(.*?)\n---", text, re.DOTALL)
    if frontmatter_match:
        fm_body = frontmatter_match.group(1)
        title_match = FRONTMATTER_TITLE_PATTERN.search(fm_body)
        if title_match:
            return title_match.group(1).strip().strip('"\'')

    return md_path.stem


def extract_wikilinks(md_path: Path) -> set[str]:
    """파일 내 [[wikilink]] 타겟 집합 반환."""
    try:
        text = md_path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return set()
    return {m.strip() for m in WIKILINK_PATTERN.findall(text)}


def is_legal_node(title: str, path: Path) -> bool:
    """제목 또는 경로에 법률 키워드 포함 여부."""
    return bool(LEGAL_PATTERN.search(title) or LEGAL_PATTERN.search(str(path)))


def read_content(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def common_content_snippet(a: Path, b: Path, max_chars: int = 120) -> str:
    """두 파일의 공통 문장 조각(최대 max_chars자)을 반환."""
    text_a = read_content(a).splitlines()
    text_b = set(read_content(b).splitlines())
    common = [line.strip() for line in text_a if line.strip() and line.strip() in text_b]
    snippet = " / ".join(common[:3])
    return snippet[:max_chars] + ("…" if len(snippet) > max_chars else "")


# ---------------------------------------------------------------------------
# 핵심 분석
# ---------------------------------------------------------------------------


def scan_vault(vault_path: Path, cluster_keyword: str | None = None) -> list[dict]:
    """Vault 내 모든 .md 파일을 스캔하여 노드 정보 목록 반환."""
    nodes: list[dict] = []
    for md_file in vault_path.rglob("*.md"):
        title = extract_title(md_file)
        if cluster_keyword and cluster_keyword not in title and cluster_keyword not in str(md_file):
            continue
        stat = md_file.stat()
        nodes.append(
            {
                "path": md_file,
                "title": title,
                "norm_title": normalize_title(title),
                "mtime": stat.st_mtime,
                "wikilinks_out": set(),  # 이 파일이 가리키는 링크
            }
        )
    return nodes


def build_wikilink_index(nodes: list[dict]) -> dict[str, list[Path]]:
    """
    title(norm) → 해당 타이틀을 참조하는 파일 목록.
    즉, inbound 링크 카운트를 위해 역인덱스를 구축한다.
    """
    # 노드 title 정규화 맵
    norm_to_paths: dict[str, list[Path]] = {}
    for node in nodes:
        norm_to_paths.setdefault(node["norm_title"], []).append(node["path"])

    # 각 노드에서 outbound wikilink 수집
    inbound: dict[str, list[Path]] = {}  # norm_title → 이 노드를 가리키는 파일들
    for node in nodes:
        links = extract_wikilinks(node["path"])
        node["wikilinks_out"] = links
        for link in links:
            norm_link = normalize_title(link)
            inbound.setdefault(norm_link, []).append(node["path"])

    return inbound


def find_exact_duplicates(nodes: list[dict]) -> list[tuple[dict, dict]]:
    """정규화 제목이 완전히 동일한 쌍 반환."""
    seen: dict[str, list[dict]] = {}
    for node in nodes:
        seen.setdefault(node["norm_title"], []).append(node)

    pairs: list[tuple[dict, dict]] = []
    for group in seen.values():
        if len(group) >= 2:
            # 가장 오래된 것 vs 최신 것 쌍으로 묶기 (최신 기준 정렬)
            sorted_group = sorted(group, key=lambda n: n["mtime"])
            for i in range(len(sorted_group) - 1):
                pairs.append((sorted_group[i], sorted_group[-1]))
    return pairs


def find_similar_duplicates(
    nodes: list[dict],
    threshold: float = SIMILARITY_THRESHOLD,
) -> list[tuple[dict, dict, float]]:
    """유사도 threshold 이상인 쌍 반환 (완전 동일 제외)."""
    results: list[tuple[dict, dict, float]] = []
    norm_titles = [n["norm_title"] for n in nodes]

    for i, node_a in enumerate(nodes):
        for j in range(i + 1, len(nodes)):
            node_b = nodes[j]
            if node_a["norm_title"] == node_b["norm_title"]:
                continue  # 완전 중복은 exact 그룹에서 처리
            ratio = difflib.SequenceMatcher(
                None, node_a["norm_title"], node_b["norm_title"]
            ).ratio()
            if ratio >= threshold:
                results.append((node_a, node_b, ratio))

    return sorted(results, key=lambda x: x[2], reverse=True)


def find_orphan_nodes(nodes: list[dict], inbound: dict[str, list[Path]]) -> list[dict]:
    """inbound wikilink가 없는 고아 노드 반환."""
    orphans = []
    for node in nodes:
        if not inbound.get(node["norm_title"]):
            orphans.append(node)
    return orphans


# ---------------------------------------------------------------------------
# 자동 병합
# ---------------------------------------------------------------------------


def auto_merge_exact(
    exact_pairs: list[tuple[dict, dict]],
    dry_run: bool = False,
) -> list[str]:
    """
    완전 중복 쌍에서 오래된 파일 내용을 최신 파일에 append 후 오래된 파일 삭제.
    dry_run=True 이면 실제 파일 수정 없이 액션 로그만 반환.
    """
    log: list[str] = []
    for old_node, new_node in exact_pairs:
        old_path: Path = old_node["path"]
        new_path: Path = new_node["path"]

        old_content = read_content(old_path).strip()
        new_content = read_content(new_path)

        merged_section = (
            f"\n\n---\n<!-- merged from: {old_path.name} -->\n\n{old_content}\n"
        )

        if dry_run:
            log.append(f"[DRY-RUN] MERGE {old_path} → {new_path} (삭제 예정: {old_path.name})")
        else:
            try:
                with open(new_path, "a", encoding="utf-8") as f:
                    f.write(merged_section)
                old_path.unlink()
                log.append(f"[MERGED] {old_path.name} → {new_path.name}, 원본 삭제 완료")
            except OSError as e:
                log.append(f"[ERROR] 병합 실패 ({old_path.name}): {e}")

    return log


# ---------------------------------------------------------------------------
# 리포트 생성
# ---------------------------------------------------------------------------


def build_report(
    nodes: list[dict],
    exact_pairs: list[tuple[dict, dict]],
    similar_pairs: list[tuple[dict, dict, float]],
    legal_nodes: list[dict],
    orphan_nodes: list[dict],
    inbound: dict[str, list[Path]],
    merge_log: list[str],
    vault_path: Path,
) -> str:
    today = datetime.now().strftime("%Y-%m-%d")

    lines: list[str] = []
    lines.append(f"# Vault 중복 노드 리포트 — {today}")
    lines.append("")
    lines.append("## 요약")
    lines.append(f"- 전체 노드: {len(nodes)}개")
    lines.append(f"- 법률 클러스터: {len(legal_nodes)}개")
    lines.append(f"- 완전 중복: {len(exact_pairs)}쌍")
    lines.append(f"- 유사 중복: {len(similar_pairs)}쌍")
    lines.append(f"- 고아 노드: {len(orphan_nodes)}개")
    lines.append("")

    # 병합 로그
    if merge_log:
        lines.append("## 자동 병합 로그")
        for entry in merge_log:
            lines.append(f"- {entry}")
        lines.append("")

    # 완전 중복
    lines.append("## 완전 중복 (즉시 병합 권장)")
    lines.append("")
    lines.append("| 파일 A (구버전) | 파일 B (최신) | 액션 |")
    lines.append("|----------------|--------------|------|")
    if exact_pairs:
        for old_node, new_node in exact_pairs:
            rel_a = old_node["path"].relative_to(vault_path)
            rel_b = new_node["path"].relative_to(vault_path)
            lines.append(f"| `{rel_a}` | `{rel_b}` | 병합 후 A 삭제 |")
    else:
        lines.append("| — | — | 없음 |")
    lines.append("")

    # 유사 중복
    lines.append("## 유사 중복 (검토 권장)")
    lines.append("")
    lines.append("| 파일 A | 파일 B | 유사도 | 공통 내용 |")
    lines.append("|--------|--------|--------|----------|")
    if similar_pairs:
        for node_a, node_b, ratio in similar_pairs[:50]:  # 최대 50건
            rel_a = node_a["path"].relative_to(vault_path)
            rel_b = node_b["path"].relative_to(vault_path)
            snippet = common_content_snippet(node_a["path"], node_b["path"])
            lines.append(f"| `{rel_a}` | `{rel_b}` | {ratio:.0%} | {snippet} |")
    else:
        lines.append("| — | — | — | 없음 |")
    lines.append("")

    # 법률 클러스터
    lines.append("## 법률 클러스터 현황")
    lines.append("")
    lines.append("| 제목 | 경로 | 최종 수정 | wikilink 수 |")
    lines.append("|------|------|----------|------------|")
    for node in sorted(legal_nodes, key=lambda n: n["mtime"], reverse=True):
        rel = node["path"].relative_to(vault_path)
        mtime_str = datetime.fromtimestamp(node["mtime"]).strftime("%Y-%m-%d")
        inbound_count = len(inbound.get(node["norm_title"], []))
        lines.append(f"| {node['title']} | `{rel}` | {mtime_str} | {inbound_count} |")
    lines.append("")

    # 고아 노드
    lines.append("## 고아 노드 (링크 없음)")
    lines.append("")
    lines.append("| 제목 | 경로 | 최종 수정 |")
    lines.append("|------|------|----------|")
    if orphan_nodes:
        for node in sorted(orphan_nodes, key=lambda n: n["mtime"])[:100]:  # 최대 100건
            rel = node["path"].relative_to(vault_path)
            mtime_str = datetime.fromtimestamp(node["mtime"]).strftime("%Y-%m-%d")
            lines.append(f"| {node['title']} | `{rel}` | {mtime_str} |")
    else:
        lines.append("| — | — | — |")
    lines.append("")

    lines.append("---")
    lines.append(f"*생성: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} by vault_node_deduplicator.py*")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 메인
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Obsidian Vault 중복 노드 감지 및 병합 도구"
    )
    parser.add_argument(
        "--vault",
        default=DEFAULT_VAULT_PATH,
        help="Vault 루트 경로 (기본값: VAULT_PATH 환경변수 또는 DEFAULT_VAULT_PATH)",
    )
    parser.add_argument(
        "--cluster",
        default=None,
        metavar="KEYWORD",
        help="특정 키워드 클러스터만 스캔 (예: 법률)",
    )
    parser.add_argument(
        "--auto-merge",
        action="store_true",
        help="완전 동일 제목 쌍을 자동 병합 (오래된 파일 내용 → 최신 파일 append, 오래된 파일 삭제)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="실제 파일 수정 없이 리포트만 생성",
    )
    parser.add_argument(
        "--similarity",
        type=float,
        default=SIMILARITY_THRESHOLD,
        metavar="RATIO",
        help=f"유사도 임계값 0.0~1.0 (기본값: {SIMILARITY_THRESHOLD})",
    )
    args = parser.parse_args()

    vault_path = Path(args.vault)
    if not vault_path.exists():
        print(f"[ERROR] Vault 경로를 찾을 수 없습니다: {vault_path}", file=sys.stderr)
        sys.exit(1)

    print(f"[INFO] Vault 스캔 중: {vault_path}")
    nodes = scan_vault(vault_path, cluster_keyword=args.cluster)
    print(f"[INFO] 노드 {len(nodes)}개 발견")

    print("[INFO] wikilink 인덱스 구축 중...")
    inbound = build_wikilink_index(nodes)

    print("[INFO] 완전 중복 감지 중...")
    exact_pairs = find_exact_duplicates(nodes)
    print(f"       → 완전 중복 {len(exact_pairs)}쌍")

    print("[INFO] 유사 중복 감지 중 (시간이 걸릴 수 있습니다)...")
    similar_pairs = find_similar_duplicates(nodes, threshold=args.similarity)
    print(f"       → 유사 중복 {len(similar_pairs)}쌍")

    print("[INFO] 법률 클러스터 필터링 중...")
    legal_nodes = [n for n in nodes if is_legal_node(n["title"], n["path"])]
    print(f"       → 법률 노드 {len(legal_nodes)}개")

    print("[INFO] 고아 노드 감지 중...")
    orphan_nodes = find_orphan_nodes(nodes, inbound)
    print(f"       → 고아 노드 {len(orphan_nodes)}개")

    # 자동 병합
    merge_log: list[str] = []
    if args.auto_merge:
        if args.dry_run:
            print("[INFO] --dry-run 모드: 자동 병합 시뮬레이션")
        else:
            print(f"[INFO] 자동 병합 실행 ({len(exact_pairs)}쌍)...")
        merge_log = auto_merge_exact(exact_pairs, dry_run=args.dry_run)
        for entry in merge_log:
            print(f"       {entry}")

    # 리포트 생성
    report_content = build_report(
        nodes=nodes,
        exact_pairs=exact_pairs,
        similar_pairs=similar_pairs,
        legal_nodes=legal_nodes,
        orphan_nodes=orphan_nodes,
        inbound=inbound,
        merge_log=merge_log,
        vault_path=vault_path,
    )

    today = datetime.now().strftime("%Y-%m-%d")
    report_path = vault_path / "00_System" / f"dedup-report-{today}.md"

    if args.dry_run:
        print(f"[DRY-RUN] 리포트 출력 (파일 저장 생략: {report_path})")
        print("-" * 60)
        print(report_content)
    else:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(report_content, encoding="utf-8")
        print(f"[OK] 리포트 저장 완료: {report_path}")


if __name__ == "__main__":
    main()
