"""Daily Plus -> Graphify evolution bridge.

Runs after the Daily Plus 09:00 report so Bucky has a compact daily record of
the current Graphify map, context pack path, and AgentBus bridge message.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VAULT = ROOT / "ObsidianVault"
DEFAULT_GRAPH_DIR = VAULT / "graphify-out"
DEFAULT_CONTEXT_PACK = VAULT / "06_Context_Packs" / "Graphify" / "ObsidianVault_graphify_pack.md"


def _compact(date: str) -> str:
    return date.replace("-", "")


def _today_kst() -> str:
    return datetime.now(timezone(timedelta(hours=9))).strftime("%Y-%m-%d")


def _relative(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def _read_text(path: Path, limit: int = 2000) -> str:
    if not path.exists():
        return "(missing)"
    text = path.read_text(encoding="utf-8", errors="replace").strip()
    return text[:limit] + ("\n...[truncated]" if len(text) > limit else "")


def _daily_report_path(root: Path, date: str) -> Path:
    return root / "ObsidianVault" / "10_AgentBus" / "reports" / f"{_compact(date)}_daily_plus_dashboard_report.md"


def _latest_daily_report_date(root: Path) -> str:
    reports = sorted((root / "ObsidianVault" / "10_AgentBus" / "reports").glob("*_daily_plus_dashboard_report.md"))
    if not reports:
        return _today_kst()
    match = re.match(r"(\d{8})_", reports[-1].name)
    if not match:
        return _today_kst()
    raw = match.group(1)
    return f"{raw[:4]}-{raw[4:6]}-{raw[6:]}"


def _parse_bridge_message(stdout: str) -> Path | None:
    marker = "AgentBus message written:"
    for line in stdout.splitlines():
        if marker in line:
            return Path(line.split(marker, 1)[1].strip())
    return None


def _run(cmd: list[str], root: Path) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    result = subprocess.run(
        cmd,
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(f"{cmd[0]} failed: {detail}")
    return result


def build_graphify_summary(
    *,
    root: Path,
    date: str,
    graph_dir: Path,
    context_pack: Path,
    bridge_message: Path | None,
) -> str:
    report_path = _daily_report_path(root, date)
    graph_report = graph_dir / "GRAPH_REPORT.md"
    bridge_display = _relative(bridge_message, root) if bridge_message else "(not reported)"
    now = datetime.now(timezone(timedelta(hours=9))).strftime("%Y-%m-%dT%H:%M:%S%z")

    return f"""---
type: daily-graphify-evolution
date: {date}
created_at: {now}
source: daily-plus-0900
status: ready
daily_plus_report: {_relative(report_path, root)}
graph_report: {_relative(graph_report, root)}
context_pack: {_relative(context_pack, root)}
bridge_message: {bridge_display}
---

# Daily Graphify Evolution - {date}

## Daily Plus 09:00 report

`{_relative(report_path, root)}`

```text
{_read_text(report_path, 1200)}
```

## Graphify Summary

`{_relative(graph_report, root)}`

```text
{_read_text(graph_report, 1200)}
```

## Bucky Knowledge Links

- Context Pack: `{_relative(context_pack, root)}`
- AgentBus bridge message: `{bridge_display}`
- Bucky default context source: `ObsidianVault/10_AgentBus/completed/latest_daily_graphify_evolution.md`
"""


def run_daily_graphify_evolution(
    *,
    date: str | None = None,
    root: Path = ROOT,
    graph_dir: Path | None = None,
    context_pack: Path | None = None,
    skip_graphify: bool = False,
) -> Path:
    root = Path(root)
    date = date or _latest_daily_report_date(root)
    graph_dir = graph_dir or root / "ObsidianVault" / "graphify-out"
    context_pack = context_pack or root / "ObsidianVault" / "06_Context_Packs" / "Graphify" / "ObsidianVault_graphify_pack.md"
    report_path = _daily_report_path(root, date)
    if not report_path.exists():
        raise FileNotFoundError(f"Daily Plus 09:00 report not found: {report_path}")

    if not skip_graphify:
        _run([sys.executable, "-X", "utf8", "-m", "graphify", "update", str(root / "ObsidianVault"), "--no-cluster"], root)
        _run([sys.executable, "-X", "utf8", str(root / "scripts" / "graphify_post_build.py"), str(graph_dir)], root)
        _run(
            [
                sys.executable,
                "-X",
                "utf8",
                str(root / "scripts" / "graphify_context_pack.py"),
                "--project",
                "ObsidianVault",
                "--graph",
                str(graph_dir),
                "--output",
                _relative(context_pack, root),
            ],
            root,
        )

    bridge = _run(
        [
            sys.executable,
            "-X",
            "utf8",
            str(root / "scripts" / "agentbus_graphify_bridge.py"),
            "--project",
            "ObsidianVault",
            "--graph",
            _relative(graph_dir, root),
            "--context-pack",
            _relative(context_pack, root),
        ],
        root,
    )
    bridge_message = _parse_bridge_message(bridge.stdout)
    summary = build_graphify_summary(
        root=root,
        date=date,
        graph_dir=graph_dir,
        context_pack=context_pack,
        bridge_message=bridge_message,
    )

    completed_dir = root / "ObsidianVault" / "10_AgentBus" / "completed"
    completed_dir.mkdir(parents=True, exist_ok=True)
    daily_record = completed_dir / f"{_compact(date)}_daily_graphify_evolution.md"
    latest_record = completed_dir / "latest_daily_graphify_evolution.md"
    daily_record.write_text(summary, encoding="utf-8")
    latest_record.write_text(summary, encoding="utf-8")
    return daily_record


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Daily Plus Graphify evolution bridge")
    parser.add_argument("--date", default=None, help="Daily Plus date YYYY-MM-DD; defaults to latest report")
    parser.add_argument("--skip-graphify", action="store_true", help="Skip graph update and use existing GRAPH_REPORT.md")
    args = parser.parse_args()
    record = run_daily_graphify_evolution(date=args.date, skip_graphify=args.skip_graphify)
    print(f"[daily-graphify-evolution] wrote {record}")


if __name__ == "__main__":
    main()
