"""Create the 09:00 Bucky morning report for Daily Plus.

This script regenerates docs/daily-plus.html, then writes a compact AgentBus
report so Bucky has a durable daily artifact to show or relay to the user.
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

from generate_daily_plus_dashboard import (
    ROOT,
    VAULT,
    attach_statuses,
    candidate_scores,
    latest_report,
    load_history,
    parse_candidates,
    parse_frontmatter,
    read_text,
    generate,
)


PUBLIC_URL = "https://jaeha81.github.io/obsidian-agent-brain-system/daily-plus.html"


def build_report() -> Path:
    output = generate(None)
    report_path = latest_report(None)
    report_text = read_text(report_path)
    meta = parse_frontmatter(report_text)
    date = meta.get("date") or report_path.stem
    candidates = parse_candidates(report_text)
    attach_statuses(date, candidates)
    statuses = Counter(item.status for item in candidates)
    efficiency, compatibility = candidate_scores(candidates)
    history = load_history()

    kst = timezone(timedelta(hours=9))
    now = datetime.now(kst).strftime("%Y-%m-%dT%H:%M:%S%z")
    compact = date.replace("-", "")
    reports_dir = VAULT / "10_AgentBus" / "reports"
    outbox_dir = VAULT / "10_AgentBus" / "outbox" / "Bucky"
    reports_dir.mkdir(parents=True, exist_ok=True)
    outbox_dir.mkdir(parents=True, exist_ok=True)
    morning_report = reports_dir / f"{compact}_daily_plus_dashboard_report.md"
    outbox_message = outbox_dir / f"{compact}_090000_daily_plus_dashboard_bucky.md"

    first_date = history[0].date if history else date
    cumulative = sum(item.candidates for item in history)
    approval = statuses.get("needs-user-approval", 0)
    queued = statuses.get("queued", 0) + statuses.get("staged", 0)
    applied = statuses.get("applied", 0)

    body = f"""---
type: bucky-morning-report
scope: daily-plus-dashboard
date: {date}
created_at: {now}
owner: Bucky
status: ready
dashboard: docs/daily-plus.html
public_url: {PUBLIC_URL}
---

# Daily Plus Morning Report - {date}

## User Summary

- Dashboard: [{PUBLIC_URL}]({PUBLIC_URL})
- Local file: `{output.relative_to(ROOT)}`
- First Daily Plus baseline: `{first_date}`
- Today candidates: `{len(candidates)}`
- Applied today: `{applied}`
- Queued/staged today: `{queued}`
- Needs user approval: `{approval}`
- Average efficiency: `{efficiency}`
- Average compatibility: `{compatibility}`
- Cumulative candidates since baseline: `{cumulative}`

## Bucky Operating Rule

At 09:00 KST, Bucky should point the user to the dashboard and summarize:

1. What Daily Plus collected today.
2. What was actually implemented or operationally processed.
3. What is queued, staged, or blocked on user approval.
4. How today's result compares to the first Daily Plus baseline.
5. Which item is the safest next action.

## Source

- Pulse report: `{report_path.relative_to(ROOT)}`
- Dashboard generator: `scripts/generate_daily_plus_dashboard.py`
- Morning report script: `scripts/daily_plus_morning_report.py`
"""
    morning_report.write_text(body, encoding="utf-8")
    outbox_body = f"""---
type: bucky-user-report
scope: daily-plus-dashboard
date: {date}
created_at: {now}
status: ready
dashboard: docs/daily-plus.html
public_url: {PUBLIC_URL}
---

# Bucky Daily Plus 09:00 Report - {date}

오늘의 플러스 처리 결과입니다.

- 대시보드: [{PUBLIC_URL}]({PUBLIC_URL})
- 로컬 파일: `{output.relative_to(ROOT)}`
- 첫 기준일: `{first_date}`
- 오늘 후보: `{len(candidates)}`
- 구현 반영: `{applied}`
- 큐/스테이징: `{queued}`
- 사용자 승인 필요: `{approval}`
- 평균 효율성: `{efficiency}`
- 평균 호환성: `{compatibility}`
- 누적 후보: `{cumulative}`

요약:
- 오늘의 플러스는 수집, 진화 리포트 생성, Bucky 보고 산출물 생성까지 완료됐다.
- 직접 구현보다 큐/승인대기 중심으로 분리되어 있어, 무리한 자동 변경 없이 다음 액션을 고르기 좋다.
- 사용자는 대시보드에서 첫 오늘의 플러스 대비 진화 추세와 오늘 실행 후보를 바로 확인하면 된다.
"""
    outbox_message.write_text(outbox_body, encoding="utf-8")
    return morning_report


def main() -> None:
    report = build_report()
    print(f"[daily-plus-morning-report] wrote {report}")


if __name__ == "__main__":
    main()
