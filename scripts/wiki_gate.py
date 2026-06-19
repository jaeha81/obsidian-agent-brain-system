#!/usr/bin/env python3
"""
wiki_gate.py — Raw → Wiki 5-Filter 게이트

01_RAW/ 노트가 03_Knowledge/로 승격될 자격이 있는지 5개 필터로 검사.
모두 통과한 경우에만 자동 이동.

사용법:
  python scripts/wiki_gate.py --scan          # 01_RAW 전체 배치 검사
  python scripts/wiki_gate.py --watch         # 실시간 감시 (파일 변경 감지)
  python scripts/wiki_gate.py --file <path>   # 단일 파일 검사
  python scripts/wiki_gate.py --dry-run       # 이동 없이 결과만 출력

필터:
  F1 Schema    — YAML frontmatter 필수 키 존재 (title, tags, created, source, status)
  F2 Duplicate — 03_Knowledge 내 80% 이상 유사 노트 없음
  F3 Relevance — tags에 허용 도메인 포함
  F4 Link      — 최소 1개 wikilink 또는 외부 URL 포함
  F5 Age       — 01_RAW 체류 48h 이상
"""

import argparse
import json
import os
import re
import shutil
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import yaml

_ROOT = Path(__file__).parent.parent
VAULT = Path(os.getenv("VAULT_PATH", str(_ROOT / "ObsidianVault")))
RAW_DIR = VAULT / "01_RAW"
KNOWLEDGE_DIR = VAULT / "03_Knowledge"
REPORT_DIR = VAULT / "07_Daily"

ALLOWED_DOMAINS = {
    "interior", "consulting", "ai", "system", "business",
    "learning", "ai_ops", "project", "framework", "template",
}
REQUIRED_FRONTMATTER = {"title", "tags", "created", "source", "status"}
MIN_AGE_HOURS = 48
SIMILARITY_THRESHOLD = 0.80


# ──────────────────────────────────────────
# 데이터 클래스
# ──────────────────────────────────────────

@dataclass
class FilterResult:
    name: str
    passed: bool
    reason: str = ""


@dataclass
class GateResult:
    path: Path
    filters: list[FilterResult] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return all(f.passed for f in self.filters)

    @property
    def failed_filters(self) -> list[FilterResult]:
        return [f for f in self.filters if not f.passed]

    def summary(self) -> str:
        status = "PASS" if self.passed else "FAIL"
        details = "; ".join(
            f"{f.name}={'✅' if f.passed else '❌'}" + (f" ({f.reason})" if not f.passed else "")
            for f in self.filters
        )
        return f"[{status}] {self.path.name} — {details}"


# ──────────────────────────────────────────
# 유틸리티
# ──────────────────────────────────────────

def _parse_frontmatter(text: str) -> Optional[dict]:
    """YAML frontmatter 파싱. 없으면 None 반환."""
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    if end == -1:
        return None
    try:
        return yaml.safe_load(text[3:end]) or {}
    except yaml.YAMLError:
        return None


def _token_set(text: str) -> set[str]:
    """간단한 토큰 집합 (유사도 계산용)."""
    return set(re.findall(r"\b\w{3,}\b", text.lower()))


def _jaccard(a: set, b: set) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _get_knowledge_texts() -> list[tuple[Path, set[str]]]:
    """03_Knowledge 전체 노트 토큰 집합 캐시 반환."""
    result = []
    for p in KNOWLEDGE_DIR.rglob("*.md"):
        try:
            tokens = _token_set(p.read_text(encoding="utf-8", errors="ignore"))
            result.append((p, tokens))
        except OSError:
            continue
    return result


# ──────────────────────────────────────────
# 5가지 필터
# ──────────────────────────────────────────

def filter_schema(text: str, fm: Optional[dict]) -> FilterResult:
    """F1: YAML frontmatter 필수 키 존재 여부."""
    if fm is None:
        return FilterResult("F1-Schema", False, "YAML frontmatter 없음")
    missing = REQUIRED_FRONTMATTER - set(fm.keys())
    if missing:
        return FilterResult("F1-Schema", False, f"누락 키: {sorted(missing)}")
    return FilterResult("F1-Schema", True)


def filter_duplicate(path: Path, text: str, knowledge_cache: list) -> FilterResult:
    """F2: 03_Knowledge 내 80% 이상 유사 노트 탐지."""
    tokens = _token_set(text)
    for kp, ktokens in knowledge_cache:
        sim = _jaccard(tokens, ktokens)
        if sim >= SIMILARITY_THRESHOLD:
            return FilterResult("F2-Duplicate", False, f"{kp.name}와 유사도 {sim:.0%}")
    return FilterResult("F2-Duplicate", True)


def filter_relevance(fm: Optional[dict]) -> FilterResult:
    """F3: tags에 허용 도메인 포함 여부."""
    if not fm:
        return FilterResult("F3-Relevance", False, "frontmatter 없음")
    tags = fm.get("tags", []) or []
    if isinstance(tags, str):
        tags = [tags]
    normalized = {t.lower().split("/")[0].split(":")[0] for t in tags}
    matched = normalized & ALLOWED_DOMAINS
    if not matched:
        return FilterResult("F3-Relevance", False, f"허용 도메인 없음 (현재 태그: {list(tags)[:3]})")
    return FilterResult("F3-Relevance", True)


def filter_links(text: str) -> FilterResult:
    """F4: 최소 1개 wikilink 또는 외부 URL 포함."""
    has_wikilink = bool(re.search(r"\[\[.+?\]\]", text))
    has_url = bool(re.search(r"https?://\S+", text))
    if not (has_wikilink or has_url):
        return FilterResult("F4-Link", False, "wikilink·URL 없음")
    return FilterResult("F4-Link", True)


def filter_age(path: Path) -> FilterResult:
    """F5: 01_RAW 체류 48h 이상."""
    try:
        mtime = path.stat().st_mtime
        age_hours = (time.time() - mtime) / 3600
        if age_hours < MIN_AGE_HOURS:
            remaining = MIN_AGE_HOURS - age_hours
            return FilterResult("F5-Age", False, f"체류 {age_hours:.1f}h — {remaining:.1f}h 더 필요")
        return FilterResult("F5-Age", True)
    except OSError as e:
        return FilterResult("F5-Age", False, str(e))


# ──────────────────────────────────────────
# 게이트 실행
# ──────────────────────────────────────────

class WikiGate:
    def __init__(self):
        self._knowledge_cache: Optional[list] = None

    def _get_cache(self) -> list:
        if self._knowledge_cache is None:
            self._knowledge_cache = _get_knowledge_texts()
        return self._knowledge_cache

    def check(self, path: Path) -> GateResult:
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError as e:
            result = GateResult(path=path)
            result.filters.append(FilterResult("F1-Schema", False, f"읽기 실패: {e}"))
            return result

        fm = _parse_frontmatter(text)
        result = GateResult(path=path)
        result.filters = [
            filter_schema(text, fm),
            filter_duplicate(path, text, self._get_cache()),
            filter_relevance(fm),
            filter_links(text),
            filter_age(path),
        ]
        return result

    def promote(self, path: Path, dry_run: bool = False) -> Path:
        dest = KNOWLEDGE_DIR / path.name
        if dry_run:
            print(f"  [DRY-RUN] {path.name} → 03_Knowledge/{path.name}")
            return dest
        shutil.move(str(path), str(dest))
        # 캐시 무효화
        self._knowledge_cache = None
        return dest

    def scan(self, dry_run: bool = False) -> list[GateResult]:
        if not RAW_DIR.exists():
            print(f"[wiki_gate] 01_RAW 폴더 없음: {RAW_DIR}", file=sys.stderr)
            return []

        md_files = sorted(RAW_DIR.rglob("*.md"))
        if not md_files:
            print("[wiki_gate] 01_RAW에 .md 파일 없음")
            return []

        print(f"[wiki_gate] {len(md_files)}개 파일 검사 중...")
        results = []
        promoted = 0

        for md in md_files:
            result = self.check(md)
            results.append(result)
            print(f"  {result.summary()}")
            if result.passed:
                dest = self.promote(md, dry_run=dry_run)
                print(f"    → 승격: {dest}")
                promoted += 1

        print(f"\n[wiki_gate] 완료 — {promoted}/{len(md_files)} 승격")
        return results


# ──────────────────────────────────────────
# 리포트 작성
# ──────────────────────────────────────────

def write_report(results: list[GateResult]):
    if not results:
        return
    today = datetime.now().strftime("%Y-%m-%d")
    report_path = REPORT_DIR / f"{today}-wiki-gate-report.md"
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    lines = [
        f"# Wiki Gate Report — {today}",
        f"> 실행 시각: {datetime.now().strftime('%H:%M:%S')}",
        f"> 총 {len(results)}개 검사, {sum(1 for r in results if r.passed)}개 승격",
        "",
        "## 승격 성공",
    ]
    passed = [r for r in results if r.passed]
    lines += [f"- {r.path.name}" for r in passed] or ["(없음)"]
    lines += ["", "## 승격 실패", ""]

    for r in results:
        if not r.passed:
            lines.append(f"### {r.path.name}")
            for f in r.failed_filters:
                lines.append(f"- ❌ {f.name}: {f.reason}")
            lines.append("")

    report_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"[wiki_gate] 리포트: {report_path}")


# ──────────────────────────────────────────
# 메인
# ──────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Raw → Wiki 5-Filter Gate")
    parser.add_argument("--scan", action="store_true", help="01_RAW 전체 배치 검사")
    parser.add_argument("--watch", action="store_true", help="실시간 감시 (10분 간격 배치)")
    parser.add_argument("--file", type=str, help="단일 파일 검사")
    parser.add_argument("--dry-run", action="store_true", help="이동 없이 결과만 출력")
    args = parser.parse_args()

    gate = WikiGate()

    if args.file:
        path = Path(args.file)
        result = gate.check(path)
        print(result.summary())
        if result.passed and not args.dry_run:
            dest = gate.promote(path)
            print(f"승격: {dest}")
        sys.exit(0 if result.passed else 1)

    elif args.scan or (not args.watch and not args.file):
        results = gate.scan(dry_run=args.dry_run)
        write_report(results)

    elif args.watch:
        print("[wiki_gate] 실시간 감시 시작 (10분 간격 배치, Ctrl+C로 종료)")
        while True:
            try:
                results = gate.scan(dry_run=args.dry_run)
                if results:
                    write_report(results)
                time.sleep(600)
            except KeyboardInterrupt:
                print("\n[wiki_gate] 감시 종료")
                break


if __name__ == "__main__":
    main()
