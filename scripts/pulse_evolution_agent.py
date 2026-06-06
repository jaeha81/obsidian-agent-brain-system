#!/usr/bin/env python3
"""
Pulse Evolution Agent.

Turns a daily ChatGPT Pulse capture into a staged upgrade report and an
AgentBus task. It deliberately stages upgrades instead of overwriting canonical
agent instructions directly.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


ROOT = Path(__file__).resolve().parents[1]
VAULT = ROOT / "ObsidianVault"
DAILY_PLUS_DIR = VAULT / "04_Wiki" / "daily-plus"
REPORT_DIR = VAULT / "00_UPGRADE" / "pulse-evolution"
INDEX_PATH = VAULT / "00_UPGRADE" / "PULSE_EVOLUTION_INDEX.md"
AGENTBUS_INBOX = VAULT / "10_AgentBus" / "inbox"


@dataclass(frozen=True)
class PulseCard:
    index: int
    title: str
    summary: str
    detail: str


@dataclass(frozen=True)
class PulseCapture:
    date: str
    source_url: str
    overview: str
    cards: list[PulseCard]


@dataclass(frozen=True)
class UpgradeCandidate:
    card_index: int
    title: str
    category: str
    priority: str
    owner: str
    target_area: str
    action: str
    evidence: str


@dataclass(frozen=True)
class CategoryRule:
    category: str
    owner: str
    target_area: str
    action: str
    keywords: tuple[str, ...]


CATEGORY_RULES: tuple[CategoryRule, ...] = (
    CategoryRule(
        category="command-payload",
        owner="distiller",
        target_area="05_Frameworks/guides / Bucky command rules",
        action="Extract reusable command payload rules and queue conflicts for review.",
        keywords=("명령", "페이로드", "payload", "command", "중복검출", "재시도"),
    ),
    CategoryRule(
        category="verification",
        owner="codex",
        target_area="00_UPGRADE/review-automation-protocol.md",
        action="Turn checks into a repeatable verification checklist before implementation.",
        keywords=("검증", "체크", "테스트", "rollback", "롤백", "서명", "배포"),
    ),
    CategoryRule(
        category="voice-pipeline",
        owner="distiller",
        target_area="05_Frameworks/guides / voice intake and Obsidian logging",
        action="Stage voice-note metadata and replay rules for the voice capture pipeline.",
        keywords=("음성", "voice", "stt", "전사", "녹음", "리플레이", "메모"),
    ),
    CategoryRule(
        category="agent-prompting",
        owner="bucky",
        target_area="03_Projects/agents / Bucky planner-executor prompts",
        action="Stage prompt changes as role-specific snippets and keep approval notes.",
        keywords=("프롬프트", "플래너", "실행자", "prompt", "planner", "executor"),
    ),
    CategoryRule(
        category="obsidian-queue",
        owner="collector",
        target_area="10_AgentBus / Obsidian queue",
        action="Convert queue ideas into AgentBus task templates or inbox rules.",
        keywords=("옵시디언", "obsidian", "큐", "queue", "agentbus", "inbox"),
    ),
    CategoryRule(
        category="experiment",
        owner="bucky",
        target_area="00_UPGRADE/next-plan.md",
        action="Log as an experiment candidate and require explicit approval before build work.",
        keywords=("실험", "구독", "파트너", "무드보드", "experiment", "partner"),
    ),
)


P1_KEYWORDS = (
    "데이터 손실",
    "손실",
    "보안",
    "secret",
    "api key",
    "중복",
    "재시도",
    "검증",
    "롤백",
    "rollback",
    "안전",
)


def parse_frontmatter(text: str) -> dict[str, str]:
    match = re.match(r"\A---\s*\n(.*?)\n---\s*\n", text, flags=re.S)
    if not match:
        return {}
    data: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        data[key.strip()] = value.strip().strip('"')
    return data


def _section_between(text: str, start_heading: str, end_heading: str | None = None) -> str:
    start = re.search(rf"^##\s+{re.escape(start_heading)}\s*$", text, flags=re.M)
    if not start:
        return ""
    body_start = start.end()
    if end_heading:
        end = re.search(rf"^##\s+{re.escape(end_heading)}\s*$", text[body_start:], flags=re.M)
        if end:
            return text[body_start : body_start + end.start()].strip()
    return text[body_start:].strip()


def _subsection(section: str, heading: str) -> str:
    match = re.search(rf"^####\s+{re.escape(heading)}\s*$", section, flags=re.M)
    if not match:
        return ""
    start = match.end()
    next_heading = re.search(r"^####\s+.+\s*$", section[start:], flags=re.M)
    if next_heading:
        return section[start : start + next_heading.start()].strip()
    return section[start:].strip()


def parse_daily_note(text: str) -> PulseCapture:
    frontmatter = parse_frontmatter(text)
    date_value = frontmatter.get("date") or datetime.now().strftime("%Y-%m-%d")
    source_url = frontmatter.get("source_url", "https://chatgpt.com/pulse")
    overview = _section_between(text, "Overview (KO)", "Overview") or _section_between(text, "Overview", "Pulse Cards")

    heading_re = re.compile(r"^###\s+(\d+)\.\s+(.+?)\s*$", flags=re.M)
    matches = list(heading_re.finditer(text))
    cards: list[PulseCard] = []
    for pos, match in enumerate(matches):
        section_start = match.end()
        section_end = matches[pos + 1].start() if pos + 1 < len(matches) else len(text)
        section = text[section_start:section_end].strip()
        summary_ko = _subsection(section, "Summary (KO)")
        summary_en = _subsection(section, "Summary")
        detail_ko = _subsection(section, "Detail (KO)")
        detail = _subsection(section, "Detail")
        summary = summary_en or section
        if summary_ko:
            summary = summary_ko
        if detail_ko:
            detail = detail_ko
        cards.append(
            PulseCard(
                index=int(match.group(1)),
                title=match.group(2).strip(),
                summary=summary,
                detail=detail,
            )
        )

    return PulseCapture(date=date_value, source_url=source_url, overview=overview, cards=cards)


def _normalized_blob(card: PulseCard) -> str:
    return f"{card.title}\n{card.summary}\n{card.detail}".lower()


def _match_rule(card: PulseCard) -> CategoryRule:
    title_summary = f"{card.title}\n{card.summary}".lower()
    detail = card.detail.lower()
    best_rule: CategoryRule | None = None
    best_score = 0
    for rule in CATEGORY_RULES:
        score = 0
        for keyword in rule.keywords:
            needle = keyword.lower()
            if needle in title_summary:
                score += 3
            if needle in detail:
                score += 1
        if score > best_score:
            best_rule = rule
            best_score = score
    if best_rule:
        return best_rule
    return CategoryRule(
        category="knowledge-candidate",
        owner="distiller",
        target_area="03_Knowledge / 00_UPGRADE",
        action="Distill the idea into a knowledge note or leave as a parked candidate.",
        keywords=(),
    )


def _priority(card: PulseCard, category: str) -> str:
    if category == "experiment":
        return "P3"
    if category in {"agent-prompting", "obsidian-queue"}:
        return "P2" if len(card.detail) > 1800 else "P3"
    blob = _normalized_blob(card)
    if any(keyword.lower() in blob for keyword in P1_KEYWORDS):
        return "P1"
    if len(card.detail) > 1800:
        return "P2"
    return "P3"


def _excerpt(text: str, limit: int = 220) -> str:
    compact = re.sub(r"\s+", " ", text).strip()
    if len(compact) <= limit:
        return compact
    return compact[: limit - 3].rstrip() + "..."


def build_candidates(capture: PulseCapture) -> list[UpgradeCandidate]:
    candidates: list[UpgradeCandidate] = []
    for card in capture.cards:
        rule = _match_rule(card)
        evidence_source = card.detail or card.summary
        candidates.append(
            UpgradeCandidate(
                card_index=card.index,
                title=card.title,
                category=rule.category,
                priority=_priority(card, rule.category),
                owner=rule.owner,
                target_area=rule.target_area,
                action=rule.action,
                evidence=_excerpt(evidence_source),
            )
        )
    return candidates


def _vault_relative(path: Path, vault: Path) -> str:
    try:
        return path.resolve().relative_to(vault.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _task_id(date_value: str) -> str:
    return f"pulse-evolution-{date_value.replace('-', '')}"


def _completed_task_path(task_path: Path, vault: Path) -> Path:
    return vault / "10_AgentBus" / "completed" / task_path.name


def render_report(
    capture: PulseCapture,
    candidates: list[UpgradeCandidate],
    source_note: Path,
    task_path: Path,
    vault: Path,
) -> str:
    now = datetime.now().isoformat(timespec="seconds")
    source_rel = _vault_relative(source_note, vault)
    task_rel = _vault_relative(task_path, vault)
    completed_rel = _vault_relative(_completed_task_path(task_path, vault), vault)
    lines = [
        "---",
        "type: pulse-evolution-report",
        f"date: {capture.date}",
        f"source_note: {source_rel}",
        f"source_url: {capture.source_url}",
        f"card_count: {len(capture.cards)}",
        f"candidate_count: {len(candidates)}",
        "status: staged",
        f"created_at: {now}",
        "---",
        "",
        f"# Pulse Evolution Report - {capture.date}",
        "",
        "## Summary",
        "",
        f"- Source note: [[{source_rel}]]",
        f"- Cards read: {len(capture.cards)}",
        f"- Upgrade candidates: {len(candidates)}",
        f"- AgentBus task id: `{_task_id(capture.date)}`",
        f"- Initial AgentBus inbox task: [[{task_rel}]]",
        f"- Dispatcher completed path, if processed: [[{completed_rel}]]",
        "",
        "## Operating Rule",
        "",
        "- 원문은 `04_Wiki/daily-plus/`에 보존한다.",
        "- 이 리포트는 적용 후보를 분류한다.",
        "- 핵심 지침/프롬프트/스케줄 변경은 바로 덮어쓰지 않고 AgentBus 검토 작업으로 넘긴다.",
        "- 안전한 append-only 지식화는 distiller가 처리하고, 코드/운영 변경은 Codex 검증을 거친다.",
        "",
        "## Upgrade Candidates",
        "",
    ]
    for candidate in candidates:
        lines.extend(
            [
                f"### {candidate.priority} · Card {candidate.card_index}: {candidate.title}",
                "",
                f"- Category: `{candidate.category}`",
                f"- Owner: `{candidate.owner}`",
                f"- Target area: {candidate.target_area}",
                f"- Action: {candidate.action}",
                f"- Evidence: {candidate.evidence}",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def render_agentbus_task(
    capture: PulseCapture,
    candidates: list[UpgradeCandidate],
    source_note: Path,
    report_path: Path,
    vault: Path,
) -> str:
    now = datetime.now().isoformat(timespec="seconds")
    source_rel = _vault_relative(source_note, vault)
    report_rel = _vault_relative(report_path, vault)
    task_id = _task_id(capture.date)
    lines = [
        "---",
        f"task_id: {task_id}",
        "agent: pulse_evolution",
        "status: pending",
        "priority: P1",
        f"created_at: {now}",
        f"source_note: {source_rel}",
        f"report: {report_rel}",
        "body: Daily Pulse upgrade distillation",
        "---",
        "",
        f"# Pulse Evolution Agent - {capture.date}",
        "",
        "## Mission",
        "",
        "오늘 ChatGPT Pulse 카드 전체를 읽고 Obsidian Agent Brain System 업그레이드 후보로 정리한다.",
        "",
        "## Required Steps",
        "",
        f"1. Read source note: [[{source_rel}]]",
        f"2. Read staged report: [[{report_rel}]]",
        "3. Apply only append-only knowledge updates without deleting or overwriting canonical instructions.",
        "4. For core agent-role, scheduler, prompt, or automation changes, create a review request instead of direct overwrite.",
        "5. Mark each candidate as `applied`, `queued`, `rejected`, or `needs-user-approval` in the report.",
        "",
        "## Candidate Queue",
        "",
    ]
    for candidate in candidates:
        lines.append(
            f"- [{candidate.priority}] Card {candidate.card_index} `{candidate.category}` "
            f"-> {candidate.owner}: {candidate.title}"
        )
    return "\n".join(lines).rstrip() + "\n"


def _write_index_entry(
    *,
    capture: PulseCapture,
    report_path: Path,
    task_path: Path,
    vault: Path,
) -> None:
    index_path = vault / "00_UPGRADE" / "PULSE_EVOLUTION_INDEX.md"
    index_path.parent.mkdir(parents=True, exist_ok=True)
    if index_path.exists():
        content = index_path.read_text(encoding="utf-8")
    else:
        content = (
            "---\n"
            "type: pulse-evolution-index\n"
            "---\n\n"
            "# Pulse Evolution Index\n\n"
            "| Date | Cards | Report | AgentBus Task |\n"
            "|---|---:|---|---|\n"
        )
    report_rel = _vault_relative(report_path, vault)
    task_rel = _vault_relative(task_path, vault)
    row = f"| {capture.date} | {len(capture.cards)} | [[{report_rel}]] | [[{task_rel}]] |"
    if row not in content:
        content = content.rstrip() + "\n" + row + "\n"
        index_path.write_text(content, encoding="utf-8")


def _iter_daily_notes(vault: Path) -> Iterable[Path]:
    daily_dir = vault / "04_Wiki" / "daily-plus"
    return sorted(daily_dir.glob("*.md"))


def latest_daily_note(vault: Path = VAULT) -> Path:
    notes = list(_iter_daily_notes(vault))
    if not notes:
        raise FileNotFoundError(f"No daily-plus notes found under {vault}")
    return notes[-1]


def evolve_note_file(
    note_path: Path,
    *,
    vault: Path = VAULT,
    force: bool = False,
) -> dict[str, str | int]:
    note_path = Path(note_path)
    vault = Path(vault)
    capture = parse_daily_note(note_path.read_text(encoding="utf-8"))
    candidates = build_candidates(capture)

    report_dir = vault / "00_UPGRADE" / "pulse-evolution"
    inbox_dir = vault / "10_AgentBus" / "inbox"
    report_dir.mkdir(parents=True, exist_ok=True)
    inbox_dir.mkdir(parents=True, exist_ok=True)

    report_path = report_dir / f"{capture.date}.md"
    task_path = inbox_dir / f"{capture.date.replace('-', '')}_pulse_evolution_agent.md"
    existing_task_path = task_path if task_path.exists() else _completed_task_path(task_path, vault)

    if report_path.exists() and existing_task_path.exists() and not force:
        return {
            "status": "skipped",
            "reason": "report and task already exist",
            "report_path": str(report_path),
            "task_path": str(existing_task_path),
            "cards": len(capture.cards),
            "candidates": len(candidates),
        }

    task_content = render_agentbus_task(capture, candidates, note_path, report_path, vault)
    task_path.write_text(task_content, encoding="utf-8")
    report_content = render_report(capture, candidates, note_path, task_path, vault)
    report_path.write_text(report_content, encoding="utf-8")
    _write_index_entry(capture=capture, report_path=report_path, task_path=task_path, vault=vault)

    return {
        "status": "created",
        "report_path": str(report_path),
        "task_path": str(task_path),
        "cards": len(capture.cards),
        "candidates": len(candidates),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Stage ChatGPT Pulse upgrades for Bucky")
    parser.add_argument("--note", type=Path, help="Daily Pulse note path")
    parser.add_argument("--latest", action="store_true", help="Use latest daily-plus note")
    parser.add_argument("--force", action="store_true", help="Overwrite existing report/task")
    args = parser.parse_args()

    note_path = args.note
    if args.latest or note_path is None:
        note_path = latest_daily_note()

    result = evolve_note_file(note_path, force=args.force)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
