#!/usr/bin/env python3
"""
Auto Stage-to-Implement Pipeline with Conflict Detector.

Reads pulse-evolution reports, runs conflict detection per card,
creates knowledge notes for safe cards, holds conflict items,
and generates a user-facing report.

Usage:
    python -X utf8 scripts/auto_stage_to_implement.py           # process today
    python -X utf8 scripts/auto_stage_to_implement.py --date 2026-06-11
    python -X utf8 scripts/auto_stage_to_implement.py --all     # unprocessed dates
    python -X utf8 scripts/auto_stage_to_implement.py --dry-run # preview only
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
VAULT = ROOT / "ObsidianVault"
PULSE_REPORT_DIR = VAULT / "00_UPGRADE" / "pulse-evolution"
KNOWLEDGE_DIR = VAULT / "03_Knowledge"
HOLD_LIST_PATH = VAULT / "00_UPGRADE" / "daily-plus-hold-list.md"
REPORT_DIR = VAULT / "00_UPGRADE"

KST = timezone(timedelta(hours=9))

# ──────────────────────────────────────────────────────────────────────────────
# Conflict detection rules
# ──────────────────────────────────────────────────────────────────────────────

HOLD_CATEGORIES = {"agent-prompting", "experiment"}

SAFE_CATEGORIES = {
    "knowledge-candidate",
    "voice-pipeline",
    "verification",
    "obsidian-queue",
    "command-payload",
}

CONFLICT_FILE_PATTERNS = [
    "bucky.md",
    "routing_rules",
    "ROUTING_RULES",
    "system prompt",
    "CLAUDE.md",
    "bucky-context",
    "BUCKY_CONTEXT",
    "discord_bot.py",
    "core prompt",
    "핵심 프롬프트",
    "핵심 시스템",
    "역할 재정의",
    "역할 재설정",
    "오케스트레이터 프롬프트",
    "orchestrator prompt",
    "운영 중단",
    "시스템 중단",
    "api key",
    "API Key",
    "PII",
    "개인정보 처리방침",
]

CONFLICT_TARGET_PATTERNS = [
    "03_Projects/agents/bucky",
    "ROUTING_RULES",
    "bucky-context",
]

SAFE_OWNERS = {"distiller", "codex", "collector"}


@dataclass
class CardData:
    card_num: int
    priority: str
    title: str
    category: str
    owner: str
    target_area: str
    action: str
    evidence: str


@dataclass
class ConflictResult:
    is_conflict: bool
    reasons: list[str] = field(default_factory=list)


@dataclass
class ProcessResult:
    card: CardData
    action: str          # "implemented" | "held" | "skipped"
    output_path: Optional[Path] = None
    conflict: Optional[ConflictResult] = None
    note: str = ""


# ──────────────────────────────────────────────────────────────────────────────
# Conflict detector
# ──────────────────────────────────────────────────────────────────────────────

def detect_conflict(card: CardData) -> ConflictResult:
    """Return ConflictResult with reasons if the card is a conflict risk."""
    reasons: list[str] = []

    # Rule 1: category-based hold
    if card.category in HOLD_CATEGORIES:
        reasons.append(
            f"카테고리 '{card.category}' — "
            + ("핵심 프롬프트 수정 위험" if card.category == "agent-prompting" else "사용자 승인 필요한 실험 항목")
        )

    # Rule 2: target area references core files
    target_lower = card.target_area.lower()
    for pattern in CONFLICT_TARGET_PATTERNS:
        if pattern.lower() in target_lower:
            reasons.append(f"대상 경로에 핵심 파일 포함: '{pattern}'")
            break

    # Rule 3: title or evidence references core files/patterns
    blob = f"{card.title}\n{card.evidence}".lower()
    for pattern in CONFLICT_FILE_PATTERNS:
        if pattern.lower() in blob:
            reasons.append(f"내용에 충돌 위험 키워드 감지: '{pattern}'")
            break

    # Rule 4: owner is bucky AND not in safe categories
    if card.owner == "bucky" and card.category not in SAFE_CATEGORIES:
        reasons.append("owner=bucky + 비안전 카테고리 → Bucky 승인 필요")

    return ConflictResult(is_conflict=len(reasons) > 0, reasons=reasons)


# ──────────────────────────────────────────────────────────────────────────────
# Pulse-evolution report parser
# ──────────────────────────────────────────────────────────────────────────────

def parse_pulse_report(path: Path) -> list[CardData]:
    """Parse a pulse-evolution report and return list of CardData."""
    text = path.read_text(encoding="utf-8", errors="replace")

    # Pattern: ### P1 · Card 2: Title
    pattern = re.compile(
        r"^###\s+(P\d)\s+·\s+Card\s+(\d+):\s+(.+?)\n"
        r"(.*?)(?=^###\s+P\d\s+·\s+Card\s+\d+:|\Z)",
        re.M | re.S,
    )

    cards: list[CardData] = []
    for match in pattern.finditer(text):
        priority, card_num, title, block = match.groups()
        fields = {
            key.lower().replace(" ", "_"): value.strip()
            for key, value in re.findall(r"^-\s+([^:]+):\s*(.*)$", block, re.M)
        }
        category = fields.get("category", "knowledge-candidate").strip("`")
        owner = fields.get("owner", "distiller").strip("`")
        target = fields.get("target_area", "03_Knowledge").strip("`")
        action = fields.get("action", "").strip()
        evidence = fields.get("evidence", "").strip()

        cards.append(CardData(
            card_num=int(card_num),
            priority=priority,
            title=title.strip(),
            category=category,
            owner=owner,
            target_area=target,
            action=action,
            evidence=evidence,
        ))

    return cards


def is_already_implemented(report_date: str, card: CardData) -> bool:
    """Check if a knowledge note for this card already exists."""
    slug = _make_slug(card.title)
    # Check both same-date and next-date patterns (notes sometimes created next day)
    for date_prefix in [report_date, _next_day(report_date)]:
        note_path = KNOWLEDGE_DIR / f"{date_prefix}-dp-{slug}.md"
        if note_path.exists():
            return True
    return False


def _next_day(date_str: str) -> str:
    """Return next day as YYYY-MM-DD."""
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        return (dt + timedelta(days=1)).strftime("%Y-%m-%d")
    except ValueError:
        return date_str


# ──────────────────────────────────────────────────────────────────────────────
# Knowledge note creator
# ──────────────────────────────────────────────────────────────────────────────

def _make_slug(title: str) -> str:
    """Convert title to filesystem-safe slug."""
    slug = title.lower()
    # Korean → remove, keep alphanumeric and spaces
    slug = re.sub(r"[^\w\s-]", "", slug, flags=re.UNICODE)
    slug = re.sub(r"\s+", "-", slug.strip())
    slug = re.sub(r"-+", "-", slug)
    return slug[:60].rstrip("-") or "untitled"


def create_knowledge_note(report_date: str, card: CardData, dry_run: bool = False) -> Path:
    """Create a knowledge note for a safe card. Return the output path."""
    slug = _make_slug(card.title)
    now = datetime.now(KST)
    note_date = now.strftime("%Y-%m-%d")
    filename = f"{note_date}-dp-{slug}.md"
    out_path = KNOWLEDGE_DIR / filename

    # Build tags from category and title words
    tags = [card.category, "daily-plus", "auto-implemented"]
    # Add a few meaningful words from title as tags
    for word in re.findall(r"[a-zA-Z가-힣]{3,}", card.title)[:4]:
        tags.append(word.lower())

    evidence_body = card.evidence if card.evidence else "_증거 없음_"
    # Wrap long evidence lines
    evidence_body = re.sub(r"(.{120})", r"\1\n", evidence_body)

    content = f"""---
title: {card.title}
date: {note_date}
source: daily-plus/{report_date}.md (Card {card.card_num})
priority: {card.priority}
category: {card.category}
owner: {card.owner}
status: auto-implemented
tags:
  - {chr(10).join('  - ' + t for t in tags[1:]).lstrip()}
---

# {card.title}

> ChatGPT Pulse {report_date} Card {card.card_num} 자동 증류 ({card.priority} · {card.category})

## 목적

{_build_purpose(card)}

## 핵심 내용

{evidence_body}

## 적용 방법

{card.action or '관련 가이드 또는 지식 노트에 통합 가능.'}

## 관련 영역

- 대상: `{card.target_area}`
- 담당: {card.owner}
"""

    if not dry_run:
        out_path.write_text(content, encoding="utf-8")
    return out_path


def _build_purpose(card: CardData) -> str:
    """Build a one-line purpose from card data."""
    if len(card.evidence) > 50:
        first_sentence = re.split(r"[.。\n]", card.evidence)[0].strip()
        if len(first_sentence) > 10:
            return first_sentence[:200]
    return f"{card.title} 관련 지식을 Vault에 증류한 노트."


# ──────────────────────────────────────────────────────────────────────────────
# Hold list updater
# ──────────────────────────────────────────────────────────────────────────────

def append_to_hold_list(report_date: str, card: CardData, conflict: ConflictResult, dry_run: bool = False) -> None:
    """Append a new conflict item to the hold list."""
    if not HOLD_LIST_PATH.exists():
        return

    text = HOLD_LIST_PATH.read_text(encoding="utf-8", errors="replace")

    # Find the correct section to append to
    section_header = _conflict_section(card)
    reason_str = "; ".join(conflict.reasons)

    new_row = (
        f"| {report_date} | {card.title[:55]} | {reason_str[:80]} |\n"
    )

    # Check if already in hold list
    if card.title[:30] in text:
        return  # Already recorded

    # Find section header and append after the table
    section_idx = text.find(section_header)
    if section_idx == -1:
        # Append new section at end
        new_section = (
            f"\n---\n\n## {section_header}\n\n"
            f"| 날짜 | 카드명 | 충돌 이유 |\n"
            f"|------|--------|----------|\n"
            f"{new_row}"
        )
        new_text = text + new_section
    else:
        # Find next table end in this section
        # Insert before the next --- or end of file
        next_sep = text.find("\n---", section_idx + 1)
        if next_sep == -1:
            next_sep = len(text)
        # Find last table row in section
        section_text = text[section_idx:next_sep]
        table_match = list(re.finditer(r"^\|.+\|$", section_text, re.M))
        if table_match:
            last_row_end = section_idx + table_match[-1].end()
            new_text = text[:last_row_end] + "\n" + new_row.rstrip() + text[last_row_end:]
        else:
            # No table found, append at end of section
            new_text = text[:next_sep] + new_row + text[next_sep:]

    if not dry_run:
        HOLD_LIST_PATH.write_text(new_text, encoding="utf-8")


def _conflict_section(card: CardData) -> str:
    if card.category == "agent-prompting":
        return "A. agent-prompting 보류"
    elif card.category == "experiment":
        return "B. experiment 보류"
    else:
        return "D. 기타 충돌 보류"


# ──────────────────────────────────────────────────────────────────────────────
# Process a single date
# ──────────────────────────────────────────────────────────────────────────────

def process_date(report_date: str, dry_run: bool = False) -> list[ProcessResult]:
    report_path = PULSE_REPORT_DIR / f"{report_date}.md"
    if not report_path.exists():
        print(f"  [{report_date}] 리포트 없음 — 건너뜀")
        return []

    cards = parse_pulse_report(report_path)
    if not cards:
        print(f"  [{report_date}] 카드 0개 — 건너뜀")
        return []

    results: list[ProcessResult] = []
    implemented = 0
    held = 0
    skipped = 0

    for card in cards:
        # Skip already implemented
        if is_already_implemented(report_date, card):
            results.append(ProcessResult(card=card, action="skipped", note="이미 구현됨"))
            skipped += 1
            continue

        conflict = detect_conflict(card)

        if conflict.is_conflict:
            append_to_hold_list(report_date, card, conflict, dry_run)
            results.append(ProcessResult(
                card=card,
                action="held",
                conflict=conflict,
                note="; ".join(conflict.reasons),
            ))
            held += 1
        else:
            out_path = create_knowledge_note(report_date, card, dry_run)
            results.append(ProcessResult(
                card=card,
                action="implemented",
                output_path=out_path,
                note="지식 노트 자동 생성",
            ))
            implemented += 1

    print(
        f"  [{report_date}] 카드 {len(cards)}개 → "
        f"구현 {implemented}개 / 보류 {held}개 / 건너뜀 {skipped}개"
    )
    return results


# ──────────────────────────────────────────────────────────────────────────────
# Conflict report generator
# ──────────────────────────────────────────────────────────────────────────────

def generate_conflict_report(all_results: dict[str, list[ProcessResult]], dry_run: bool = False) -> Path:
    """Generate a user-facing conflict report."""
    now = datetime.now(KST)
    report_date = now.strftime("%Y-%m-%d")
    report_path = REPORT_DIR / f"auto-implement-report-{report_date}.md"

    held_items: list[tuple[str, ProcessResult]] = []
    implemented_items: list[tuple[str, ProcessResult]] = []
    skipped_items: list[tuple[str, ProcessResult]] = []

    for date, results in sorted(all_results.items()):
        for r in results:
            if r.action == "held":
                held_items.append((date, r))
            elif r.action == "implemented":
                implemented_items.append((date, r))
            else:
                skipped_items.append((date, r))

    lines = [
        f"---",
        f"type: auto-implement-report",
        f"date: {report_date}",
        f"created_at: {now.isoformat()}",
        f"implemented: {len(implemented_items)}",
        f"held: {len(held_items)}",
        f"skipped: {len(skipped_items)}",
        f"dry_run: {dry_run}",
        f"---",
        f"",
        f"# 자동 구현 리포트 — {report_date}",
        f"",
        f"> 원칙: 안전한 항목은 자동 구현 / 충돌 위험 항목은 면밀히 검수 후 보류 + 사용자 보고",
        f"",
        f"## 요약",
        f"",
        f"| 구분 | 건수 |",
        f"|------|------|",
        f"| ✅ 자동 구현 | {len(implemented_items)}건 |",
        f"| 🔴 충돌 보류 | {len(held_items)}건 |",
        f"| ⏭️ 이미 처리됨 | {len(skipped_items)}건 |",
        f"",
    ]

    if held_items:
        lines += [
            f"---",
            f"",
            f"## 🔴 충돌 보류 항목 — 사용자 검토 필요",
            f"",
            f"> 아래 항목은 기존 시스템과 충돌 위험이 감지되어 **구현하지 않고 보류**했습니다.",
            f"> 각 항목별 충돌 이유를 확인 후 '승인해' 또는 '보류 유지' 응답해 주세요.",
            f"",
        ]
        for date, r in held_items:
            lines += [
                f"### [{date}] {r.card.title}",
                f"",
                f"- **카테고리**: `{r.card.category}`",
                f"- **우선순위**: {r.card.priority}",
                f"- **충돌 이유**:",
            ]
            if r.conflict:
                for reason in r.conflict.reasons:
                    lines.append(f"  - {reason}")
            lines += [
                f"- **원문 요약**: {r.card.evidence[:200].strip()}{'...' if len(r.card.evidence) > 200 else ''}",
                f"- **승인 시 처리**: `03_Knowledge/{date}-dp-{_make_slug(r.card.title)}.md` 생성",
                f"",
            ]

    if implemented_items:
        lines += [
            f"---",
            f"",
            f"## ✅ 자동 구현 완료",
            f"",
            f"| 날짜 | 카드 | 파일 |",
            f"|------|------|------|",
        ]
        for date, r in implemented_items:
            fname = r.output_path.name if r.output_path else "-"
            lines.append(f"| {date} | {r.card.title[:45]} | `{fname}` |")
        lines.append("")

    content = "\n".join(lines)

    if not dry_run:
        report_path.write_text(content, encoding="utf-8")

    return report_path


# ──────────────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────────────

def get_unprocessed_dates() -> list[str]:
    """Return dates that have pulse-evolution reports but limited knowledge notes."""
    processed: set[str] = set()
    # Consider a date processed if ≥2 dp-notes exist for it (or next day)
    for note in KNOWLEDGE_DIR.glob("????-??-??-dp-*.md"):
        stem = note.stem
        date_match = re.match(r"(\d{4}-\d{2}-\d{2})", stem)
        if date_match:
            processed.add(date_match.group(1))

    unprocessed: list[str] = []
    for report in sorted(PULSE_REPORT_DIR.glob("????-??-??.md")):
        date_str = report.stem
        text = report.read_text(encoding="utf-8", errors="replace")
        if "card_count: 0" in text or "candidate_count: 0" in text:
            continue
        # Check if this date or next day has notes
        next_day = _next_day(date_str)
        if date_str not in processed and next_day not in processed:
            unprocessed.append(date_str)

    return unprocessed


def print_conflict_summary(all_results: dict[str, list[ProcessResult]]) -> None:
    """Print a concise conflict summary to stdout."""
    total_held = sum(1 for results in all_results.values() for r in results if r.action == "held")
    total_impl = sum(1 for results in all_results.values() for r in results if r.action == "implemented")
    total_skip = sum(1 for results in all_results.values() for r in results if r.action == "skipped")

    print(f"\n{'='*60}")
    print(f"자동 구현 파이프라인 결과")
    print(f"{'='*60}")
    print(f"  ✅ 자동 구현:  {total_impl}건")
    print(f"  🔴 충돌 보류:  {total_held}건")
    print(f"  ⏭️  이미 처리:  {total_skip}건")

    if total_held > 0:
        print(f"\n🔴 보류 항목 상세:")
        for date, results in sorted(all_results.items()):
            for r in results:
                if r.action == "held":
                    print(f"  [{date}] {r.card.title}")
                    if r.conflict:
                        for reason in r.conflict.reasons:
                            print(f"    → {reason}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Auto Stage-to-Implement Pipeline")
    parser.add_argument("--date", help="처리할 날짜 (YYYY-MM-DD)")
    parser.add_argument("--all", action="store_true", help="미처리 날짜 전체 처리")
    parser.add_argument("--dry-run", action="store_true", help="파일 쓰기 없이 미리보기")
    args = parser.parse_args()

    dry_run = args.dry_run
    if dry_run:
        print("[DRY-RUN 모드] 파일을 생성하지 않습니다.\n")

    if args.all:
        dates = get_unprocessed_dates()
        if not dates:
            print("미처리 날짜 없음. 모두 처리 완료 상태입니다.")
            return
        print(f"미처리 날짜 {len(dates)}개 처리 시작...")
    elif args.date:
        dates = [args.date]
    else:
        dates = [datetime.now(KST).strftime("%Y-%m-%d")]

    all_results: dict[str, list[ProcessResult]] = {}
    for date in dates:
        results = process_date(date, dry_run)
        if results:
            all_results[date] = results

    if not all_results:
        print("처리할 카드가 없습니다.")
        return

    print_conflict_summary(all_results)

    # Generate report
    report_path = generate_conflict_report(all_results, dry_run)
    print(f"\n📄 충돌 보고서: {report_path.relative_to(ROOT)}")

    # Regenerate dashboard
    if not dry_run:
        dashboard_script = ROOT / "scripts" / "apply_pulse_notes.py"
        if dashboard_script.exists():
            print("\n대시보드 상태 업데이트 중...")
            result = subprocess.run(
                [sys.executable, "-X", "utf8", str(dashboard_script)],
                capture_output=True,
                text=True,
                cwd=str(ROOT),
            )
            if result.returncode == 0:
                print("대시보드 업데이트 완료")
            else:
                print(f"대시보드 업데이트 경고: {result.stderr[:200]}")


if __name__ == "__main__":
    main()
