"""Create the 09:00 Bucky morning report for Daily Plus.

This script regenerates docs/daily-plus.html, then writes a compact AgentBus
report so Bucky has a durable daily artifact to show or relay to the user.
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
import json
import os
import subprocess
import sys
import time
import urllib.request

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
from daily_graphify_evolution import run_daily_graphify_evolution


PUBLIC_URL = "https://jaeha81.github.io/obsidian-agent-brain-system/daily-plus.html"

_GBRAIN_URL = "http://localhost:8787/mcp"
_GBRAIN_TOKEN = os.environ.get(
    "GBRAIN_TOKEN",
    "Bearer gbrain_df591891043aaadcfe912558300f9aad84873cfca7545511487a7cc6dea8f440",
)


def _try_gbrain_timeline(date: str, candidates: int, applied: int, status: str) -> None:
    """Best-effort: write daily-plus summary to gbrain timeline for evolution loop.
    Silently no-ops when gbrain is offline — never blocks the report pipeline.
    """
    summary = (
        f"Daily Plus {date}: candidates={candidates}, applied={applied}, status={status}, "
        f"dashboard={PUBLIC_URL}"
    )
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "add_timeline_entry",
            "arguments": {"slug": f"daily-plus/{date}", "summary": summary, "date": date},
        },
    }
    try:
        req = urllib.request.Request(
            _GBRAIN_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": _GBRAIN_TOKEN,
                "Accept": "application/json, text/event-stream",
            },
            method="POST",
        )
        urllib.request.urlopen(req, timeout=5).read()
        print(f"[daily-plus-morning-report] gbrain timeline entry saved: {date}")
    except Exception as exc:
        print(f"[daily-plus-morning-report] gbrain timeline skipped: {exc}", file=sys.stderr)


def _safe_int(value: object, default: int = 0) -> int:
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return default


def _looks_like_error_capture(text: str) -> bool:
    compact = " ".join(text.lower().split())
    return any(
        marker in compact
        for marker in ("404 not found", "page not found", "this page could not be found")
    )


def report_needs_attention(report_text: str, capture_text: str) -> bool:
    meta = parse_frontmatter(report_text)
    card_count = _safe_int(meta.get("card_count"))
    candidate_count = _safe_int(meta.get("candidate_count"))
    return _looks_like_error_capture(capture_text) or card_count <= 0 or candidate_count <= 0


def write_attention_report(report_path: Path, capture_path: Path, reason: str) -> Path:
    report_text = read_text(report_path)
    meta = parse_frontmatter(report_text)
    date = meta.get("date") or report_path.stem
    kst = timezone(timedelta(hours=9))
    now = datetime.now(kst).strftime("%Y-%m-%dT%H:%M:%S%z")
    compact = date.replace("-", "")
    reports_dir = VAULT / "10_AgentBus" / "reports"
    outbox_dir = VAULT / "10_AgentBus" / "outbox" / "Bucky"
    reports_dir.mkdir(parents=True, exist_ok=True)
    outbox_dir.mkdir(parents=True, exist_ok=True)
    morning_report = reports_dir / f"{compact}_daily_plus_dashboard_report.md"
    outbox_message = outbox_dir / f"{compact}_090000_daily_plus_dashboard_bucky.md"

    body = f"""---
type: bucky-morning-report
scope: daily-plus-dashboard
date: {date}
created_at: {now}
owner: Bucky
status: needs-attention
dashboard: docs/daily-plus.html
public_url: {PUBLIC_URL}
---

# Daily Plus Morning Report - {date}

## User Summary

- Status: `needs-attention`
- Reason: {reason}
- Dashboard: [{PUBLIC_URL}]({PUBLIC_URL})
- Pulse report: `{report_path.relative_to(ROOT)}`
- Source note: `{capture_path.relative_to(ROOT)}`

## Bucky Operating Rule

- Do not overwrite the public dashboard with an empty or failed Pulse capture.
- Tell the user that Daily Plus ran but needs attention.
- Fix collection/login/source access first, then regenerate the dashboard.
"""
    write_text_or_keep_existing(
        morning_report,
        body,
        [f"date: {date}", "status: needs-attention", PUBLIC_URL],
    )

    outbox_body = f"""---
type: bucky-user-report
scope: daily-plus-dashboard
date: {date}
created_at: {now}
status: needs-attention
dashboard: docs/daily-plus.html
public_url: {PUBLIC_URL}
---

# Bucky Daily Plus 09:00 Report - {date}

오늘의 플러스는 실행됐지만 정상 카드 수집에 실패했습니다.

- 원인: {reason}
- 대시보드: [{PUBLIC_URL}]({PUBLIC_URL})
- 원본 수집: `{capture_path.relative_to(ROOT)}`
- 진화 리포트: `{report_path.relative_to(ROOT)}`

다음 조치:
- ChatGPT Pulse 접근 또는 로그인 상태를 복구한다.
- 빈/404 캡처를 저장하지 않도록 collector 검증을 유지한다.
- 정상 수집 후 대시보드를 다시 생성한다.
"""
    write_text_or_keep_existing(
        outbox_message,
        outbox_body,
        [f"date: {date}", "status: needs-attention", PUBLIC_URL],
    )
    return morning_report


def generate_dashboard(date: str | None) -> Path:
    try:
        return generate(date)
    except PermissionError as exc:
        script = ROOT / "scripts" / "generate_daily_plus_dashboard.py"
        prefix = "[daily-plus-dashboard] wrote "
        variants = [[]] if not date else [["--date", date], []]
        last_error = ""
        for extra_args in variants:
            result = subprocess.run(
                [sys.executable, str(script), *extra_args],
                cwd=ROOT,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
            if result.returncode == 0:
                for line in reversed(result.stdout.splitlines()):
                    if line.startswith(prefix):
                        return Path(line[len(prefix) :].strip())
                return ROOT / "docs" / "daily-plus.html"
            last_error = result.stderr.strip() or result.stdout.strip()

        raise RuntimeError(last_error) from exc


def dashboard_is_current(output: Path, date: str) -> bool:
    if not output.exists():
        return False
    text = output.read_text(encoding="utf-8")
    return date in text and f"pulse-evolution\\{date}.md" in text


def write_text_or_keep_existing(path: Path, body: str, required_markers: list[str]) -> None:
    last_error: PermissionError | None = None
    for attempt in range(3):
        try:
            path.write_text(body, encoding="utf-8")
            return
        except PermissionError as exc:
            last_error = exc
            if path.exists():
                text = path.read_text(encoding="utf-8")
                if all(marker in text for marker in required_markers):
                    return
            if attempt < 2:
                time.sleep(0.5)
                continue
            raise last_error


def build_report() -> Path:
    report_path = latest_report(None)
    report_text = read_text(report_path)
    meta = parse_frontmatter(report_text)
    date = meta.get("date") or report_path.stem
    capture_path = VAULT / "04_Wiki" / "daily-plus" / f"{date}.md"
    capture_text = read_text(capture_path) if capture_path.exists() else ""

    if report_needs_attention(report_text, capture_text):
        if _looks_like_error_capture(capture_text):
            reason = "ChatGPT Pulse source returned a not-found page."
        else:
            reason = "Pulse report has no cards or upgrade candidates."
        return write_attention_report(report_path, capture_path, reason)

    output = ROOT / "docs" / "daily-plus.html"
    try:
        output = generate_dashboard(date)
    except RuntimeError as exc:
        if not dashboard_is_current(output, date):
            return write_attention_report(
                report_path,
                capture_path,
                f"Public dashboard refresh failed: {exc}",
            )
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
    write_text_or_keep_existing(
        morning_report,
        body,
        [f"date: {date}", "status: ready", PUBLIC_URL],
    )
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
    write_text_or_keep_existing(
        outbox_message,
        outbox_body,
        [f"date: {date}", "status: ready", PUBLIC_URL],
    )
    try:
        run_daily_graphify_evolution(date=date)
    except Exception as exc:
        print(f"[daily-plus-morning-report] graphify evolution skipped: {exc}", file=sys.stderr)
    return morning_report


def main() -> None:
    report = build_report()
    print(f"[daily-plus-morning-report] wrote {report}")
    # Evolution loop: record daily-plus summary in gbrain for future session recall
    report_text = report.read_text(encoding="utf-8")
    meta = parse_frontmatter(report_text)
    date = meta.get("date") or report.stem[:8]
    candidates_raw = parse_candidates(report_text)
    attach_statuses(date, candidates_raw)
    applied = sum(1 for c in candidates_raw if c.status == "applied")
    status = meta.get("status", "ready")
    _try_gbrain_timeline(date, len(candidates_raw), applied, status)


if __name__ == "__main__":
    main()
