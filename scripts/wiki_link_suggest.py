#!/usr/bin/env python3
"""
wiki_link_suggest.py — L007: 지식 노드 자동 링크 추천

03_Knowledge/ 내 wikilink가 적은 노트를 찾아 연결 후보 Top-3를 추천.
토큰 Jaccard 유사도 기반. 추천 결과는 콘솔 출력 + MD 리포트.

사용법:
  python scripts/wiki_link_suggest.py              # 전체 스캔
  python scripts/wiki_link_suggest.py --min-links 0  # wikilink 없는 노트만
  python scripts/wiki_link_suggest.py --top 5     # 후보 Top-5 출력
  python scripts/wiki_link_suggest.py --report    # 07_Daily/에 MD 저장
  python scripts/wiki_link_suggest.py --apply     # 추천 링크를 노트 하단에 자동 추가
"""

import argparse
import os
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

_ROOT = Path(__file__).parent.parent
VAULT = Path(os.getenv("VAULT_PATH", str(_ROOT / "ObsidianVault")))
KNOWLEDGE_DIR = VAULT / "03_Knowledge"
REPORT_DIR = VAULT / "07_Daily"

MAX_LINK_THRESHOLD = 2   # 이 이하이면 "링크 부족" 대상
TOP_N_DEFAULT = 3
MIN_SIMILARITY = 0.05    # 유사도 최소 임계값 (너무 관련 없는 후보 제외)


# ──────────────────────────────────────────
# 데이터 클래스
# ──────────────────────────────────────────

@dataclass
class NoteSuggestion:
    path: Path
    link_count: int
    candidates: list[tuple[Path, float]] = field(default_factory=list)  # (path, similarity)


# ──────────────────────────────────────────
# 유틸리티
# ──────────────────────────────────────────

def _token_set(text: str) -> set[str]:
    return set(re.findall(r"\b\w{4,}\b", text.lower()))


def _jaccard(a: set, b: set) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _strip_frontmatter(text: str) -> str:
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            return text[end + 4:]
    return text


def _count_wikilinks(text: str) -> int:
    return len(re.findall(r"\[\[.+?\]\]", text))


def _existing_wikilink_targets(text: str) -> set[str]:
    return {m.lower().split("|")[0].strip() for m in re.findall(r"\[\[(.+?)\]\]", text)}


# ──────────────────────────────────────────
# 핵심 로직
# ──────────────────────────────────────────

def load_notes() -> list[tuple[Path, str, set[str]]]:
    """모든 노트 로드 → (path, text, token_set) 리스트."""
    result = []
    for p in sorted(KNOWLEDGE_DIR.rglob("*.md")):
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
            body = _strip_frontmatter(text)
            tokens = _token_set(body)
            result.append((p, text, tokens))
        except OSError:
            continue
    return result


def find_suggestions(
    notes: list[tuple[Path, str, set[str]]],
    min_links: int = MAX_LINK_THRESHOLD,
    top_n: int = TOP_N_DEFAULT,
) -> list[NoteSuggestion]:
    suggestions = []
    for i, (path, text, tokens) in enumerate(notes):
        link_count = _count_wikilinks(text)
        if link_count > min_links:
            continue

        existing_targets = _existing_wikilink_targets(text)
        stem_lower = path.stem.lower()

        # 다른 모든 노트와 유사도 계산
        scores: list[tuple[Path, float]] = []
        for j, (other_path, _, other_tokens) in enumerate(notes):
            if i == j:
                continue
            # 이미 링크된 노트 제외
            if other_path.stem.lower() in existing_targets:
                continue
            sim = _jaccard(tokens, other_tokens)
            if sim >= MIN_SIMILARITY:
                scores.append((other_path, sim))

        scores.sort(key=lambda x: x[1], reverse=True)
        candidates = scores[:top_n]

        if candidates:
            suggestions.append(NoteSuggestion(
                path=path,
                link_count=link_count,
                candidates=candidates,
            ))

    return suggestions


# ──────────────────────────────────────────
# 출력
# ──────────────────────────────────────────

def print_suggestions(suggestions: list[NoteSuggestion]):
    if not suggestions:
        print("[wiki_link_suggest] 링크 부족 노트 없음 — 모든 노트가 충분히 연결됨")
        return

    print(f"\n[wiki_link_suggest] 링크 부족 노트 {len(suggestions)}건\n")
    for s in suggestions:
        rel = s.path.relative_to(KNOWLEDGE_DIR)
        print(f"  📄 {rel} (현재 wikilink: {s.link_count}개)")
        for cpath, sim in s.candidates:
            crel = cpath.relative_to(KNOWLEDGE_DIR)
            print(f"     → [[{cpath.stem}]] ({sim:.0%} 유사)")
        print()


def save_report(suggestions: list[NoteSuggestion]) -> Path:
    today = datetime.now().strftime("%Y-%m-%d")
    report_path = REPORT_DIR / f"{today}-wiki-link-suggest.md"
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    lines = [
        f"# Wiki Link Suggestion — {today}",
        f"> 실행 시각: {datetime.now().strftime('%H:%M:%S')}",
        f"> 링크 부족 노트 {len(suggestions)}건 | 연결 후보 추천",
        "",
    ]

    if not suggestions:
        lines.append("✅ 링크 부족 노트 없음")
    else:
        for s in suggestions:
            rel = s.path.relative_to(KNOWLEDGE_DIR)
            lines.append(f"## {s.path.stem}")
            lines.append(f"> 파일: `{rel}` | 현재 wikilink: {s.link_count}개")
            lines.append("")
            lines.append("추천 연결 후보:")
            for cpath, sim in s.candidates:
                lines.append(f"- `[[{cpath.stem}]]` — 유사도 {sim:.0%}")
            lines.append("")

    report_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"[wiki_link_suggest] 리포트 저장: {report_path}")
    return report_path


def apply_suggestions(suggestions: list[NoteSuggestion]):
    """추천 링크를 노트 하단 '## 관련 노트' 섹션에 자동 추가."""
    applied = 0
    for s in suggestions:
        try:
            text = s.path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue

        # 이미 '관련 노트' 섹션이 있으면 건너뜀
        if "## 관련 노트" in text or "## Related" in text:
            continue

        links = " | ".join(f"[[{c.stem}]]" for c, _ in s.candidates)
        addition = f"\n\n## 관련 노트\n\n{links}\n"
        s.path.write_text(text.rstrip() + addition, encoding="utf-8")
        rel = s.path.relative_to(KNOWLEDGE_DIR)
        print(f"  [apply] {rel} → {links}")
        applied += 1

    print(f"[wiki_link_suggest] {applied}개 노트에 관련 노트 섹션 추가")


# ──────────────────────────────────────────
# 메인
# ──────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="L007: 지식 노드 자동 링크 추천")
    parser.add_argument("--min-links", type=int, default=MAX_LINK_THRESHOLD,
                        help=f"wikilink 이 개수 이하인 노트만 대상 (기본: {MAX_LINK_THRESHOLD})")
    parser.add_argument("--top", type=int, default=TOP_N_DEFAULT,
                        help=f"후보 최대 개수 (기본: {TOP_N_DEFAULT})")
    parser.add_argument("--report", action="store_true", help="07_Daily/에 MD 리포트 저장")
    parser.add_argument("--apply", action="store_true",
                        help="추천 링크를 노트 하단 '관련 노트' 섹션에 자동 추가")
    args = parser.parse_args()

    print(f"[wiki_link_suggest] 03_Knowledge 노트 로딩...")
    notes = load_notes()
    print(f"[wiki_link_suggest] {len(notes)}개 노트 로드됨")

    suggestions = find_suggestions(notes, min_links=args.min_links, top_n=args.top)
    print_suggestions(suggestions)

    if args.report:
        save_report(suggestions)

    if args.apply:
        print("\n[wiki_link_suggest] 자동 적용 시작...")
        apply_suggestions(suggestions)


if __name__ == "__main__":
    main()
