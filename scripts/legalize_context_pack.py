#!/usr/bin/env python3
"""
Generate a Legal Context Pack from LegalizeKR source files.
Searches external_data/legalize-kr/ for relevant laws, extracts YAML frontmatter
and key clauses, then produces a structured Markdown context pack.

Usage:
    python scripts/legalize_context_pack.py \\
        --topic "인테리어_계약" \\
        --laws "건축법,주택법" \\
        --output "ObsidianVault/06_Context_Packs/Legal/인테리어_계약_legal_pack.md"

    Optional: --keywords "임차인,보증금" for grep-based discovery.
"""

import argparse
import os
import re
import sys
from datetime import datetime
from pathlib import Path

DISCLAIMER = """법률 정보는 참고용이며, 실제 법적 판단은 전문 변호사 상담이 필요합니다.
This is for reference only. Actual legal decisions require qualified legal counsel."""

DATA_ROOT = Path("external_data/legalize-kr/kr")


def parse_frontmatter(text: str) -> dict:
    meta = {}
    if not text.startswith("---"):
        return meta
    end = text.find("---", 3)
    if end == -1:
        return meta
    for line in text[3:end].splitlines():
        if ":" in line:
            k, _, v = line.partition(":")
            meta[k.strip()] = v.strip()
    return meta


def find_law_files(law_name: str) -> list[Path]:
    law_dir = DATA_ROOT / law_name
    if not law_dir.exists():
        # Try partial match
        matches = [d for d in DATA_ROOT.iterdir() if d.is_dir() and law_name in d.name]
        if not matches:
            return []
        law_dir = matches[0]
    return sorted(law_dir.glob("*.md"))


def extract_key_clauses(text: str, max_chars: int = 800) -> str:
    # Remove frontmatter
    if text.startswith("---"):
        end = text.find("---", 3)
        if end != -1:
            text = text[end + 3:].strip()
    # Truncate
    if len(text) > max_chars:
        text = text[:max_chars] + "\n...(이하 생략)"
    return text


def grep_laws(keywords: list[str], data_root: Path) -> list[Path]:
    found = set()
    for md_file in data_root.rglob("*.md"):
        try:
            content = md_file.read_text(encoding="utf-8", errors="ignore")
            if any(kw in content for kw in keywords):
                found.add(md_file)
        except OSError:
            continue
    return sorted(found)[:10]  # cap at 10 results


def build_law_table(law_files: list[Path]) -> str:
    rows = []
    for f in law_files:
        try:
            text = f.read_text(encoding="utf-8", errors="ignore")
            meta = parse_frontmatter(text)
            law_name = meta.get("법령명", f.parent.name)
            division = meta.get("법령구분", f.stem)
            enacted = meta.get("시행일", "미상")
            rows.append(f"| {law_name} | {division} | 시행: {enacted} |")
        except OSError:
            continue
    if not rows:
        return "| (검색 결과 없음) | — | — |"
    return "\n".join(rows)


def build_context_pack(topic: str, law_names: list[str],
                       keywords: list[str], data_root: Path) -> str:
    now = datetime.now().strftime("%Y-%m-%d")

    # Collect law files
    law_files = []
    for name in law_names:
        law_files.extend(find_law_files(name))

    # Grep-based discovery if keywords provided
    if keywords and not law_files:
        law_files = grep_laws(keywords, data_root)

    law_table = build_law_table(law_files)

    # Build clause excerpts (first 2 files only to stay concise)
    clause_sections = []
    for f in law_files[:2]:
        try:
            text = f.read_text(encoding="utf-8", errors="ignore")
            excerpt = extract_key_clauses(text)
            clause_sections.append(f"### {f.parent.name} / {f.stem}\n\n```\n{excerpt}\n```")
        except OSError:
            continue
    clauses_text = "\n\n".join(clause_sections) if clause_sections else "_관련 조문을 직접 검색하세요._"

    source_refs = "\n".join(f"- `{f}`" for f in law_files[:5]) or "- (없음 — legalize_sync.sh 실행 후 재시도)"

    return f"""# Legal Context Pack — {topic}
> Generated: {now} | Researcher: ClaudeCode

---

## 1. 법적 질문

{topic} 관련 법령 조사

---

## 2. 관련 법률

| 법률명 | 법령구분 | 비고 |
|--------|--------|------|
{law_table}

---

## 3. 핵심 조문 발췌

{clauses_text}

---

## 4. 적용 시나리오

> 이 섹션은 수동으로 작성하세요. 구체적 상황에 따라 적용 법령이 달라집니다.

---

## 5. 리스크 포인트

> 위반 시 처벌/과태료 조항을 직접 확인 후 작성하세요.

---

## 6. 소스 참조

{source_refs}

검색 커맨드:
```bash
bash scripts/legalize_search.sh "{' '.join(law_names or keywords)}"
```

---

> **면책 조항**
>
> {DISCLAIMER}
"""


def main():
    parser = argparse.ArgumentParser(description="Generate Legal Context Pack")
    parser.add_argument("--topic", required=True, help="Topic name (used in filename)")
    parser.add_argument("--laws", default="", help="Comma-separated law names")
    parser.add_argument("--keywords", default="", help="Comma-separated search keywords")
    parser.add_argument("--output", required=True, help="Output .md file path")
    parser.add_argument("--data-root", default="external_data/legalize-kr/kr",
                        help="Path to legalize-kr/kr directory")
    args = parser.parse_args()

    data_root = Path(args.data_root)
    if not data_root.exists():
        print(f"WARNING: {data_root} not found. Run scripts/legalize_sync.sh first.",
              file=sys.stderr)

    law_names = [l.strip() for l in args.laws.split(",") if l.strip()]
    keywords = [k.strip() for k in args.keywords.split(",") if k.strip()]

    content = build_context_pack(args.topic, law_names, keywords, data_root)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding="utf-8")
    print(f"Legal Context Pack written to: {output_path}")


if __name__ == "__main__":
    main()
