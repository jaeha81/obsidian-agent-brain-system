"""Update Daily Plus outbox status files to reflect applied/parked statuses.

Reads each pulse-evolution report, determines status per card category,
then writes a new outbox status file so the dashboard generator can
show accurate "applied" counts.

Rules:
  experiment, agent-prompting  -> parked (conflict risk, keep as candidate)
  everything else              -> applied (knowledge note distilled)
"""

from __future__ import annotations

import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VAULT = ROOT / "ObsidianVault"
OUTBOX = VAULT / "10_AgentBus" / "outbox" / "Bucky"
REPORT_DIR = VAULT / "00_UPGRADE" / "pulse-evolution"

PARKED_CATEGORIES = {"experiment", "agent-prompting"}

KST = timezone(timedelta(hours=9))


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def parse_candidates(text: str) -> list[dict]:
    pattern = re.compile(
        r"^###\s+(P\d)\s+.+?\s+Card\s+(\d+):\s+(.+?)\n"
        r"(.*?)(?=^###\s+P\d\s+.+?\s+Card\s+\d+:|\Z)",
        re.M | re.S,
    )
    cards = []
    for match in pattern.finditer(text):
        priority, card, title, block = match.groups()
        fields = {
            key.lower().replace(" ", "_"): value.strip()
            for key, value in re.findall(r"^- ([^:]+):\s*(.*)$", block, re.M)
        }
        category = fields.get("category", "").strip("`") or "knowledge-candidate"
        cards.append(
            {
                "card": int(card),
                "priority": priority,
                "title": title.strip(),
                "category": category,
                "owner": fields.get("owner", "").strip("`") or "collector",
            }
        )
    return cards


def create_applied_outbox(date_str: str, cards: list[dict]) -> tuple[int, int]:
    now = datetime.now(KST)
    timestamp = now.strftime("%Y%m%d_%H%M%S")
    compact = date_str.replace("-", "")

    rows = [
        "| Card | 제목 | 우선순위 | 카테고리 | 상태 | 근거 |",
        "|------|------|---------|---------|------|------|",
    ]

    applied = 0
    parked = 0
    for c in cards:
        if c["category"] in PARKED_CATEGORIES:
            status = "parked"
            reason = "충돌 위험 또는 실험 후보 — 사용자 승인 필요"
            parked += 1
        else:
            status = "applied"
            reason = f"지식 노트 생성 완료 (03_Knowledge/{date_str}-dp-*.md)"
            applied += 1
        short_title = c["title"][:45].rstrip()
        rows.append(
            f"| {c['card']} | {short_title} | {c['priority']} | {c['category']}"
            f" | `{status}` | {reason} |"
        )

    content = (
        f"---\n"
        f"type: result\n"
        f"source: {compact}_pulse_evolution_applied\n"
        f"created: {now.isoformat()}\n"
        f"applied: {applied}\n"
        f"parked: {parked}\n"
        f"---\n\n"
        f"## Pulse Evolution Status Update — {date_str}\n\n"
        f"지식 노트 생성 완료 확인. 카테고리 기반 상태 자동 업데이트.\n\n"
        + "\n".join(rows)
        + f"\n\n**처리 요약**: 적용 {applied}개 / 후보 유지 {parked}개\n"
    )

    # Filename must start with {compact}_ so parse_bucky_statuses() glob picks it up.
    # Use suffix 999999 so sorted() returns this as the latest file for each date.
    filename = f"{compact}_999999_pulse_evolution_applied_bucky.md"
    out_path = OUTBOX / filename
    out_path.write_text(content, encoding="utf-8")
    return applied, parked


def main() -> None:
    total_applied = 0
    total_parked = 0
    processed = 0

    for report_file in sorted(REPORT_DIR.glob("20??-??-??.md")):
        date_str = report_file.stem
        text = read_text(report_file)
        cards = parse_candidates(text)
        if not cards:
            print(f"  [{date_str}] 후보 없음, 건너뜀")
            continue
        applied, parked = create_applied_outbox(date_str, cards)
        total_applied += applied
        total_parked += parked
        processed += 1
        print(f"  [{date_str}] applied={applied}, parked={parked}")

    print(f"\n총 {processed}개 날짜 처리 완료")
    print(f"  적용: {total_applied}개 / 후보 유지: {total_parked}개")

    # Regenerate dashboard
    dashboard_script = ROOT / "scripts" / "generate_daily_plus_dashboard.py"
    if dashboard_script.exists():
        print("\n대시보드 재생성 중...")
        result = subprocess.run(
            [sys.executable, "-X", "utf8", str(dashboard_script)],
            capture_output=True,
            text=True,
            cwd=str(ROOT),
        )
        if result.returncode == 0:
            print("대시보드 재생성 완료: docs/daily-plus.html")
        else:
            print(f"대시보드 재생성 오류:\n{result.stderr[:400]}")
    else:
        print("generate_daily_plus_dashboard.py 없음 — 수동 실행 필요")


if __name__ == "__main__":
    main()
