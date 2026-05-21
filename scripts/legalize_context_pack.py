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
import re
import shlex
import sys
from datetime import datetime
from pathlib import Path

DISCLAIMER = """법률 정보는 참고용이며, 실제 법적 판단은 전문 변호사 상담이 필요합니다.
This is for reference only. Actual legal decisions require qualified legal counsel."""

ROOT = Path(__file__).parent.parent
DATA_ROOT = ROOT / "external_data" / "legalize-kr" / "kr"
ALLOWED_OUTPUT_ROOT = ROOT / "ObsidianVault" / "06_Context_Packs"
ALLOWED_DATA_ROOT = ROOT / "external_data"


def _safe_resolve(candidate: Path, allowed_root: Path) -> Path | None:
    """Return resolved path if within allowed_root, else None."""
    try:
        resolved = candidate.resolve()
        if resolved.is_relative_to(allowed_root.resolve()):
            return resolved
    except (OSError, ValueError):
        pass
    return None


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


def find_law_files(law_name: str, data_root: Path) -> list[Path]:
    safe = _safe_resolve(data_root / law_name, data_root)
    law_dir = Path(safe) if safe else None
    if law_dir is None or not law_dir.exists():
        matches = [d for d in data_root.iterdir() if d.is_dir() and law_name in d.name]
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
        law_files.extend(find_law_files(name, data_root))

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

    source_refs = "\n".join(f"- `{f.parent.name}/{f.name}`" for f in law_files[:5]) or "- (없음 — legalize_sync.sh 실행 후 재시도)"
    search_term = shlex.quote(" ".join(law_names or keywords))

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
bash scripts/legalize_search.sh {search_term}
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
    parser.add_argument("--data-root", default=str(DATA_ROOT),
                        help="Path to legalize-kr/kr directory")
    args = parser.parse_args()

    if not re.match(r'^[\w\s가-힣_\-\.]{1,80}$', args.topic):
        print(f"ERROR: --topic contains invalid characters: {args.topic!r}", file=sys.stderr)
        sys.exit(1)

    data_root_candidate = Path(args.data_root)
    if not data_root_candidate.is_absolute():
        data_root_candidate = ROOT / data_root_candidate
    if _safe_resolve(data_root_candidate, ALLOWED_DATA_ROOT) is None:
        print(f"ERROR: --data-root must be within external_data/: {args.data_root}", file=sys.stderr)
        sys.exit(1)
    data_root = data_root_candidate.resolve()
    if not data_root.exists():
        print(f"WARNING: {data_root} not found. Run scripts/legalize_sync.sh first.",
              file=sys.stderr)

    output_candidate = Path(args.output)
    if not output_candidate.is_absolute():
        output_candidate = ROOT / output_candidate
    if _safe_resolve(output_candidate, ALLOWED_OUTPUT_ROOT) is None:
        print(f"ERROR: --output must be within ObsidianVault/06_Context_Packs/: {args.output}", file=sys.stderr)
        sys.exit(1)
    output_path = output_candidate

    law_names = [l.strip() for l in args.laws.split(",") if l.strip()]
    keywords = [k.strip() for k in args.keywords.split(",") if k.strip()]

    content = build_context_pack(args.topic, law_names, keywords, data_root)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding="utf-8")
    print(f"Legal Context Pack written to: {output_path}")


if __name__ == "__main__":
    main()
