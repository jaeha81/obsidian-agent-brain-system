#!/usr/bin/env python3
"""
wiki_lint.py — Wiki 품질 검사 (03_Knowledge Lint)

03_Knowledge 내 기존 노트의 품질 문제를 감지하고 리포트를 출력.
이동이나 삭제 없이 read-only 분석만 수행.

Lint 규칙:
  L001 — YAML frontmatter 없음
  L002 — graph_cluster 필드 없음
  L003 — status=draft 이고 90일 이상 미갱신
  L004 — wikilink 0개 (고립 노트)
  L005 — 허용 도메인 외 태그만 사용

사용법:
  python scripts/wiki_lint.py              # 전체 검사 + 콘솔 출력
  python scripts/wiki_lint.py --report     # 07_Daily/ 에 MD 리포트 저장
  python scripts/wiki_lint.py --rule L004  # 특정 규칙만 검사
  python scripts/wiki_lint.py --fix-hints  # 수정 방법 힌트 포함
"""

import argparse
import os
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import yaml

_ROOT = Path(__file__).parent.parent
VAULT = Path(os.getenv("VAULT_PATH", str(_ROOT / "ObsidianVault")))
KNOWLEDGE_DIR = VAULT / "03_Knowledge"
REPORT_DIR = VAULT / "07_Daily"

ALLOWED_DOMAINS = {
    "interior", "consulting", "ai", "system", "business",
    "learning", "ai_ops", "project", "framework", "template",
}
DRAFT_STALE_DAYS = 90


# ──────────────────────────────────────────
# 데이터 클래스
# ──────────────────────────────────────────

@dataclass
class LintIssue:
    rule: str        # L001 ~ L005
    path: Path
    message: str
    hint: str = ""   # 수정 방법 힌트


@dataclass
class LintReport:
    issues: list[LintIssue] = field(default_factory=list)
    total_checked: int = 0

    def by_rule(self) -> dict[str, list[LintIssue]]:
        result: dict[str, list[LintIssue]] = {}
        for issue in self.issues:
            result.setdefault(issue.rule, []).append(issue)
        return result

    def summary(self) -> str:
        br = self.by_rule()
        parts = [f"{rule}: {len(issues)}건" for rule, issues in sorted(br.items())]
        return f"총 {len(self.issues)}건 ({', '.join(parts)})"


# ──────────────────────────────────────────
# 유틸리티
# ──────────────────────────────────────────

def _parse_frontmatter(text: str) -> Optional[dict]:
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    if end == -1:
        return None
    try:
        return yaml.safe_load(text[3:end]) or {}
    except yaml.YAMLError:
        return None


def _get_file_mtime(path: Path) -> datetime:
    return datetime.fromtimestamp(path.stat().st_mtime)


# ──────────────────────────────────────────
# Lint 규칙
# ──────────────────────────────────────────

def lint_l001(path: Path, text: str, fm: Optional[dict]) -> Optional[LintIssue]:
    """L001: YAML frontmatter 없음."""
    if fm is None:
        return LintIssue(
            rule="L001",
            path=path,
            message="YAML frontmatter 없음",
            hint="파일 상단에 ---로 감싼 YAML 블록 추가 (title, tags, created, source, status 필수)",
        )
    return None


def lint_l002(path: Path, text: str, fm: Optional[dict]) -> Optional[LintIssue]:
    """L002: graph_cluster 필드 없음."""
    if fm is None:
        return None  # L001이 먼저 잡음
    if "graph_cluster" not in fm:
        return LintIssue(
            rule="L002",
            path=path,
            message="graph_cluster 필드 없음",
            hint="frontmatter에 graph_cluster: interior|consulting|ai_ops|system|business 중 하나 추가",
        )
    return None


def lint_l003(path: Path, text: str, fm: Optional[dict]) -> Optional[LintIssue]:
    """L003: status=draft 이고 90일 이상 미갱신."""
    if fm is None:
        return None
    status = str(fm.get("status", "")).strip().lower()
    if status != "draft":
        return None

    # updated 또는 파일 수정 시각 기준
    updated_raw = fm.get("updated") or fm.get("created")
    if updated_raw:
        try:
            updated = datetime.strptime(str(updated_raw), "%Y-%m-%d")
        except ValueError:
            updated = _get_file_mtime(path)
    else:
        updated = _get_file_mtime(path)

    age = datetime.now() - updated
    if age > timedelta(days=DRAFT_STALE_DAYS):
        return LintIssue(
            rule="L003",
            path=path,
            message=f"status=draft, {age.days}일 미갱신",
            hint="status를 active 또는 archived로 변경하거나, 내용을 실제로 업데이트",
        )
    return None


def lint_l004(path: Path, text: str, fm: Optional[dict]) -> Optional[LintIssue]:
    """L004: wikilink 0개 (고립 노트)."""
    wikilinks = re.findall(r"\[\[.+?\]\]", text)
    if not wikilinks:
        return LintIssue(
            rule="L004",
            path=path,
            message="wikilink 없는 고립 노트",
            hint="관련 노트를 [[노트명]] 형태로 연결하여 그래프 연결성 확보",
        )
    return None


def lint_l005(path: Path, text: str, fm: Optional[dict]) -> Optional[LintIssue]:
    """L005: 허용 도메인 외 태그만 사용."""
    if fm is None:
        return None
    tags = fm.get("tags", []) or []
    if isinstance(tags, str):
        tags = [tags]
    normalized = {str(t).lower().split("/")[0].split(":")[0] for t in tags if t is not None}
    if tags and not (normalized & ALLOWED_DOMAINS):
        return LintIssue(
            rule="L005",
            path=path,
            message=f"허용 도메인 외 태그만 사용: {list(tags)[:3]}",
            hint=f"허용 도메인: {sorted(ALLOWED_DOMAINS)} 중 하나 이상 추가",
        )
    return None


LINT_RULES = {
    "L001": lint_l001,
    "L002": lint_l002,
    "L003": lint_l003,
    "L004": lint_l004,
    "L005": lint_l005,
}


# ──────────────────────────────────────────
# 메인 검사 로직
# ──────────────────────────────────────────

def run_lint(rules: Optional[list[str]] = None) -> LintReport:
    active_rules = {k: v for k, v in LINT_RULES.items() if not rules or k in rules}
    report = LintReport()

    if not KNOWLEDGE_DIR.exists():
        print(f"[wiki_lint] 03_Knowledge 폴더 없음: {KNOWLEDGE_DIR}", file=sys.stderr)
        return report

    md_files = sorted(KNOWLEDGE_DIR.rglob("*.md"))
    report.total_checked = len(md_files)

    for path in md_files:
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        fm = _parse_frontmatter(text)

        for rule_fn in active_rules.values():
            issue = rule_fn(path, text, fm)
            if issue:
                report.issues.append(issue)

    return report


# ──────────────────────────────────────────
# 출력
# ──────────────────────────────────────────

def print_report(report: LintReport, fix_hints: bool = False):
    print(f"\n[wiki_lint] {report.total_checked}개 파일 검사 완료")
    print(f"[wiki_lint] {report.summary()}\n")

    for rule, issues in sorted(report.by_rule().items()):
        print(f"── {rule} ({len(issues)}건) ──")
        for issue in issues:
            rel = issue.path.relative_to(KNOWLEDGE_DIR)
            print(f"  {rel}: {issue.message}")
            if fix_hints and issue.hint:
                print(f"    → {issue.hint}")
        print()


def save_report(report: LintReport, fix_hints: bool = False):
    today = datetime.now().strftime("%Y-%m-%d")
    report_path = REPORT_DIR / f"{today}-wiki-lint.md"
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    lines = [
        f"# Wiki Lint Report — {today}",
        f"> 실행 시각: {datetime.now().strftime('%H:%M:%S')}",
        f"> {report.total_checked}개 파일 검사, {report.summary()}",
        "",
    ]

    for rule, issues in sorted(report.by_rule().items()):
        rule_descs = {
            "L001": "YAML frontmatter 없음",
            "L002": "graph_cluster 필드 없음",
            "L003": "status=draft 90일 이상 미갱신",
            "L004": "고립 노트 (wikilink 없음)",
            "L005": "허용 도메인 외 태그만 사용",
        }
        lines.append(f"## {rule} — {rule_descs.get(rule, '')} ({len(issues)}건)")
        lines.append("")
        for issue in issues:
            rel = issue.path.relative_to(KNOWLEDGE_DIR)
            lines.append(f"- `{rel}` — {issue.message}")
            if fix_hints and issue.hint:
                lines.append(f"  - 힌트: {issue.hint}")
        lines.append("")

    if not report.issues:
        lines.append("✅ 모든 규칙 통과 — 이슈 없음")

    report_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"[wiki_lint] 리포트 저장: {report_path}")
    return report_path


# ──────────────────────────────────────────
# 메인
# ──────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Wiki Lint — 03_Knowledge 품질 검사")
    parser.add_argument("--report", action="store_true", help="07_Daily/ 에 MD 리포트 저장")
    parser.add_argument("--rule", type=str, help="특정 규칙만 검사 (예: L004 또는 L001,L004)")
    parser.add_argument("--fix-hints", action="store_true", help="수정 방법 힌트 포함")
    parser.add_argument("--exit-code", action="store_true", help="이슈 있으면 exit code 1")
    args = parser.parse_args()

    rules = None
    if args.rule:
        rules = [r.strip().upper() for r in args.rule.split(",")]
        invalid = [r for r in rules if r not in LINT_RULES]
        if invalid:
            print(f"[wiki_lint] 알 수 없는 규칙: {invalid}. 유효: {sorted(LINT_RULES)}", file=sys.stderr)
            sys.exit(2)

    report = run_lint(rules=rules)
    print_report(report, fix_hints=args.fix_hints)

    if args.report:
        save_report(report, fix_hints=args.fix_hints)

    if args.exit_code and report.issues:
        sys.exit(1)


if __name__ == "__main__":
    main()
