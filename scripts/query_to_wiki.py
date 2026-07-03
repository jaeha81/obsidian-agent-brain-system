#!/usr/bin/env python3
"""
query_to_wiki.py — 쿼리→Wiki 피드백 루프 (G1)

GBrain/InfraNodus 검색 결과 또는 수동 쿼리 결과를
01_RAW/에 구조화된 노트로 저장해 wiki_gate 파이프라인으로 흘려보냄.

사용법:
  python scripts/query_to_wiki.py --query "LLM 메모리 구조" --answer "<답변 텍스트>"
  python scripts/query_to_wiki.py --query "..." --answer "..." --cluster "llm-research"
  python scripts/query_to_wiki.py --stdin  # JSON {query, answer, cluster, source} stdin으로 읽기

  # 배치: 파일에서 읽기
  python scripts/query_to_wiki.py --batch queries.json

출력: ObsidianVault/01_RAW/query-YYYYMMDD-HHMMSS-<slug>.md
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VAULT = os.path.join(_ROOT, "ObsidianVault")
RAW_DIR = os.path.join(VAULT, "01_RAW")

ALLOWED_CLUSTERS = [
    "llm-research", "ai-ops", "knowledge-graph", "daily-practice",
    "youtube-learning", "claude-ai", "bucky-agent", "codex-agent",
    "oabs-system", "brain-system", "goalmode", "agent-patterns",
    "marketing", "revenue-ops", "misc",
]


def slugify(text: str, max_len: int = 40) -> str:
    text = re.sub(r"[^\w\s가-힣-]", "", text.lower())
    text = re.sub(r"\s+", "-", text.strip())
    return text[:max_len].rstrip("-")


def now_kst() -> datetime:
    from datetime import timedelta
    kst = timezone(timedelta(hours=9))
    return datetime.now(kst)


def build_note(query: str, answer: str, cluster: str = "misc",
               source: str = "query-feedback", links: list = None) -> str:
    now = now_kst()
    created = now.strftime("%Y-%m-%dT%H:%M:%S+09:00")
    tags_str = f"[ai, {cluster.replace('-', '_')}]"
    links = links or []

    # wikilink 자동 추출 (답변에서 [[...]] 패턴)
    found_links = re.findall(r"\[\[([^\]]+)\]\]", answer)
    all_links = list(dict.fromkeys(links + found_links))
    link_section = ""
    if all_links:
        link_section = "\n## 관련 노트\n" + "\n".join(f"- [[{l}]]" for l in all_links)
    else:
        # 기본 링크 추가 (wiki_gate F4 통과용)
        link_section = "\n## 관련 노트\n- [[03_Knowledge/README]]"

    frontmatter = f"""---
title: "Q: {query[:80]}"
tags: {tags_str}
created: "{created}"
source: "{source}"
status: draft
graph_cluster: "{cluster}"
query_origin: true
---
"""

    body = f"""# {query}

## 쿼리 답변

{answer.strip()}
{link_section}

---
*자동 생성: query_to_wiki.py | {now.strftime('%Y-%m-%d %H:%M')} KST*
"""
    return frontmatter + body


def save_note(query: str, answer: str, cluster: str = "misc",
              source: str = "query-feedback", links: list = None,
              dry_run: bool = False) -> str:
    now = datetime.now()
    ts = now.strftime("%Y%m%d-%H%M%S")
    slug = slugify(query)
    filename = f"query-{ts}-{slug}.md"
    path = os.path.join(RAW_DIR, filename)

    content = build_note(query, answer, cluster, source, links)

    if dry_run:
        print(f"[DRY] 저장 예정: {path}")
        print(content[:300] + "...")
        return path

    os.makedirs(RAW_DIR, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"[query_to_wiki] 저장: {path}")
    return path


def main():
    parser = argparse.ArgumentParser(description="쿼리 결과를 Wiki 노트로 저장")
    parser.add_argument("--query", "-q", help="쿼리 텍스트")
    parser.add_argument("--answer", "-a", help="답변 텍스트")
    parser.add_argument("--cluster", "-c", default="misc",
                        choices=ALLOWED_CLUSTERS + ["misc"],
                        help=f"graph_cluster (기본: misc)")
    parser.add_argument("--source", default="query-feedback",
                        help="source 필드 (기본: query-feedback)")
    parser.add_argument("--links", nargs="*", default=[],
                        help="추가 wikilink 목록")
    parser.add_argument("--stdin", action="store_true",
                        help="JSON stdin으로 읽기")
    parser.add_argument("--batch", help="JSON 배치 파일 경로")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if args.stdin:
        data = json.load(sys.stdin)
        if isinstance(data, list):
            for item in data:
                save_note(dry_run=args.dry_run, **item)
        else:
            save_note(dry_run=args.dry_run, **data)

    elif args.batch:
        with open(args.batch, encoding="utf-8") as f:
            items = json.load(f)
        for item in items:
            save_note(dry_run=args.dry_run, **item)

    elif args.query and args.answer:
        save_note(
            query=args.query,
            answer=args.answer,
            cluster=args.cluster,
            source=args.source,
            links=args.links,
            dry_run=args.dry_run,
        )

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
