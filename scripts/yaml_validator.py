#!/usr/bin/env python3
"""
yaml_validator.py — Obsidian 노트 YAML frontmatter 표준 검증

사용법:
    python scripts/yaml_validator.py <path>          # 파일 또는 폴더
    python scripts/yaml_validator.py --strict <path> # 경고도 오류로 처리
    python scripts/yaml_validator.py --summary       # 요약만 출력
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent

REQUIRED_FIELDS = {"type", "status", "created"}
VALID_TYPES = {
    "project", "task", "estimate", "log", "system-doc",
    "context-pack", "agent-result", "bridge-test", "bucky-context",
    "bucky-os-gate", "handoff", "legacy-script-classification",
    "raw-import", "wiki", "daily-report", "session-state",
}
VALID_STATUSES = {
    "draft", "done", "review", "active", "archive",
    "pending", "processing", "failed", "awaiting_approval",
    "rejected", "archived", "superseded", "ok",
}
FORBIDDEN_SECRET_FIELDS = {"api_key", "password", "secret", "token", "webhook_url"}
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}")
_FM_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)


@dataclass
class Finding:
    path: str
    level: str  # error | warn | ok
    field: str
    message: str


@dataclass
class ValidationResult:
    path: str
    findings: list[Finding] = field(default_factory=list)

    @property
    def errors(self) -> list[Finding]:
        return [f for f in self.findings if f.level == "error"]

    @property
    def warnings(self) -> list[Finding]:
        return [f for f in self.findings if f.level == "warn"]

    @property
    def ok(self) -> bool:
        return not self.errors


def _parse_fm(text: str) -> dict | None:
    m = _FM_RE.match(text)
    if not m:
        return None
    try:
        return yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError:
        return None


def validate_file(filepath: Path) -> ValidationResult:
    result = ValidationResult(path=str(filepath.relative_to(ROOT)))
    text = filepath.read_text(encoding="utf-8", errors="replace")

    fm = _parse_fm(text)
    if fm is None:
        result.findings.append(Finding(result.path, "warn", "frontmatter", "YAML frontmatter 없음 또는 파싱 실패"))
        return result

    # 필수 필드
    for f in REQUIRED_FIELDS:
        if f not in fm:
            result.findings.append(Finding(result.path, "error", f, f"필수 필드 누락: {f}"))

    # type 유효성
    if "type" in fm:
        t = str(fm["type"])
        if t not in VALID_TYPES:
            result.findings.append(Finding(result.path, "warn", "type", f"알 수 없는 type 값: '{t}' (허용={sorted(VALID_TYPES)[:5]}...)"))

    # status 유효성
    if "status" in fm:
        s = str(fm["status"])
        if s not in VALID_STATUSES:
            result.findings.append(Finding(result.path, "warn", "status", f"알 수 없는 status 값: '{s}'"))

    # created 날짜 형식
    if "created" in fm:
        c = str(fm["created"])
        if not DATE_RE.match(c):
            result.findings.append(Finding(result.path, "warn", "created", f"날짜 형식 오류: '{c}' (YYYY-MM-DD 권장)"))

    # 비밀 필드 실제 값 입력 여부
    for secret_field in FORBIDDEN_SECRET_FIELDS:
        if secret_field in fm:
            val = str(fm[secret_field])
            if val and val not in ("-", "null", "None", ""):
                result.findings.append(Finding(result.path, "error", secret_field, f"비밀 필드에 실제 값 입력 금지: {secret_field}"))

    # processing 상태 경고
    if fm.get("status") == "processing":
        result.findings.append(Finding(result.path, "warn", "status", "status=processing 파일은 커밋하지 않을 것"))

    return result


def validate_path(target: Path) -> list[ValidationResult]:
    if target.is_file():
        if target.suffix == ".md":
            return [validate_file(target)]
        return []
    results = []
    for md in sorted(target.rglob("*.md")):
        if any(p in md.parts for p in (".git", "node_modules")):
            continue
        results.append(validate_file(md))
    return results


def print_results(results: list[ValidationResult], summary_only: bool = False) -> int:
    total = len(results)
    errors = sum(len(r.errors) for r in results)
    warnings = sum(len(r.warnings) for r in results)
    files_with_errors = [r for r in results if r.errors]
    files_with_warnings = [r for r in results if r.warnings and not r.errors]

    if not summary_only:
        for r in results:
            if not r.findings:
                continue
            print(f"\n{r.path}")
            for f in r.findings:
                icon = "❌" if f.level == "error" else "⚠️ "
                print(f"  {icon} [{f.field}] {f.message}")

    print(f"\n{'─'*50}")
    print(f"검증 결과: {total}개 파일  |  오류 {errors}개  |  경고 {warnings}개")
    if files_with_errors:
        print(f"오류 파일 ({len(files_with_errors)}개): " + ", ".join(r.path for r in files_with_errors[:5]))
    if errors == 0 and warnings == 0:
        print("✅ 모든 파일 YAML 표준 통과")
    elif errors == 0:
        print("⚠️  경고 있음 (오류 없음)")
    else:
        print("❌ 오류 있음 — 수정 필요")
    return 1 if errors else 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Obsidian YAML 표준 검증")
    ap.add_argument("path", nargs="?", default="ObsidianVault", help="파일 또는 폴더 경로")
    ap.add_argument("--strict", action="store_true", help="경고도 오류로 처리")
    ap.add_argument("--summary", action="store_true", help="요약만 출력")
    args = ap.parse_args()

    target = Path(args.path)
    if not target.is_absolute():
        target = ROOT / target
    if not target.exists():
        print(f"경로 없음: {target}")
        return 1

    results = validate_path(target)
    code = print_results(results, summary_only=args.summary)

    if args.strict:
        total_issues = sum(len(r.findings) for r in results)
        return 1 if total_issues else 0
    return code


if __name__ == "__main__":
    sys.exit(main())
