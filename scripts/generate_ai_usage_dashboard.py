"""Generate the public AI subscription usage dashboard."""

from __future__ import annotations

import html
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.subscription_roi import (  # noqa: E402
    SUB_COST_MONTHLY,
    AgentReport,
    collect_claude,
    collect_codex,
    format_int,
    summarize_usage,
    usage_recommendation,
)


DOCS = ROOT / "docs"
KST = timezone(timedelta(hours=9))


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def env_float(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, str(default)))
    except ValueError:
        return default


def env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, str(default)))
    except ValueError:
        return default


def status_class(recommendation: str) -> str:
    if recommendation.startswith("UNDERUSED"):
        return "underused"
    if recommendation.startswith("LIMIT-RISK"):
        return "limit"
    return "balanced"


def render_agent_card(report: AgentReport, days: int, reset_hours: float, target_sessions_per_reset: int) -> str:
    summary = summarize_usage(
        report,
        days=days,
        monthly_usd=SUB_COST_MONTHLY,
        reset_hours=reset_hours,
        target_sessions_per_reset=target_sessions_per_reset,
    )
    recommendation = usage_recommendation(report.name, summary)
    cost_per_session = summary["cost_per_session_usd"]
    cost_per_message = summary["cost_per_message_usd"]
    cost_session_text = "N/A" if cost_per_session is None else f"${cost_per_session:.2f}"
    cost_message_text = "N/A" if cost_per_message is None else f"${cost_per_message:.3f}"
    return f"""
      <article class="agent-card {status_class(recommendation)}">
        <div class="agent-head">
          <h3>{esc(report.name)}</h3>
          <span>{esc(recommendation.split(':', 1)[0])}</span>
        </div>
        <div class="metric-grid">
          <div><strong>{format_int(int(summary["sessions"]))}</strong><span>sessions</span></div>
          <div><strong>{format_int(int(summary["messages"]))}</strong><span>messages</span></div>
          <div><strong>{summary["active_day_percent"]}%</strong><span>active days</span></div>
          <div><strong>{summary["session_utilization_percent"]}%</strong><span>target use</span></div>
        </div>
        <div class="bar"><span style="width:{esc(summary["session_utilization_percent"])}%"></span></div>
        <dl>
          <div><dt>Tokens</dt><dd>{format_int(int(summary["total_tokens"]))} total / {format_int(int(summary["cached_tokens"]))} cached</dd></div>
          <div><dt>Budget</dt><dd>${summary["prorated_budget_usd"]:.2f} for {days} days, ${SUB_COST_MONTHLY}/month</dd></div>
          <div><dt>Unit cost</dt><dd>{cost_session_text} per session / {cost_message_text} per message</dd></div>
          <div><dt>Plan</dt><dd>{esc(recommendation)}</dd></div>
        </dl>
      </article>
"""


def render_daily_rows(reports: list[AgentReport]) -> str:
    days = sorted({day for report in reports for day in report.by_day if day != "unknown"})
    if not days:
        return "<tr><td colspan=\"3\">No local session logs found in the selected window.</td></tr>"
    rows = []
    for day in days[-14:]:
        cells = [f"<td>{esc(day)}</td>"]
        for report in reports:
            stats = report.by_day.get(day)
            if stats:
                cells.append(f"<td>{stats.sessions}s / {stats.messages}m</td>")
            else:
                cells.append("<td>0s / 0m</td>")
        rows.append("<tr>" + "".join(cells) + "</tr>")
    return "\n".join(rows)


def render_reset_plan(reset_hours: float) -> str:
    return f"""
      <div class="ops-grid">
        <div><strong>Window 1</strong><span>Start with Claude Code implementation. Keep prompts scoped to one repo and one goal.</span></div>
        <div><strong>Window 2</strong><span>Use Codex for review, failing-test analysis, and architecture risk checks while Claude quota cools.</span></div>
        <div><strong>Window 3</strong><span>Resume Claude Code for fixes from review. Stop before context gets heavy and write handoff notes.</span></div>
        <div><strong>Window 4+</strong><span>Use remaining capacity for documentation, small automation, and queued low-risk improvements.</span></div>
      </div>
      <p class="note">Current dashboard reset window: {reset_hours:g} hours. Claude Max documentation currently describes a five-hour reset; if the account banner shows four hours, run with <code>AI_USAGE_RESET_HOURS=4</code>.</p>
"""


def render_dashboard(
    reports: list[AgentReport],
    days: int,
    generated_at: str,
    reset_hours: float,
    target_sessions_per_reset: int = 2,
) -> str:
    cards = "\n".join(render_agent_card(report, days, reset_hours, target_sessions_per_reset) for report in reports)
    daily_rows = render_daily_rows(reports)
    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AI Usage Dashboard</title>
<style>
  :root {{ --bg:#f6f8fb; --surface:#fff; --ink:#0f172a; --muted:#64748b; --line:#d8e0ea; --blue:#2563eb; --green:#15803d; --amber:#b45309; --red:#b91c1c; }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; font-family:"Segoe UI", system-ui, sans-serif; background:var(--bg); color:var(--ink); }}
  header {{ background:#0f172a; color:#fff; padding:28px clamp(18px,4vw,48px) 24px; }}
  nav {{ display:flex; gap:10px; flex-wrap:wrap; margin-bottom:18px; }}
  nav a {{ color:#cbd5e1; text-decoration:none; border:1px solid #334155; border-radius:999px; padding:7px 12px; font-size:13px; }}
  nav a.active, nav a:hover {{ color:#fff; border-color:#60a5fa; }}
  h1 {{ margin:0; font-size:clamp(28px,4vw,44px); letter-spacing:0; }}
  header p {{ max-width:920px; color:#cbd5e1; line-height:1.65; margin:12px 0 0; }}
  main {{ padding:24px clamp(14px,3vw,42px) 48px; display:grid; gap:22px; }}
  .panel, .agent-card {{ background:var(--surface); border:1px solid var(--line); border-radius:8px; box-shadow:0 8px 28px rgba(15,23,42,.05); }}
  .panel {{ padding:20px; }}
  .agent-grid {{ display:grid; grid-template-columns:repeat(2,minmax(280px,1fr)); gap:14px; }}
  .agent-card {{ padding:18px; display:grid; gap:14px; }}
  .agent-head {{ display:flex; align-items:center; justify-content:space-between; gap:12px; }}
  .agent-head h3 {{ margin:0; font-size:20px; }}
  .agent-head span {{ border-radius:999px; padding:5px 9px; font-size:12px; font-weight:800; border:1px solid var(--line); }}
  .balanced .agent-head span {{ color:var(--green); background:#f0fdf4; border-color:#bbf7d0; }}
  .underused .agent-head span {{ color:var(--amber); background:#fff7ed; border-color:#fed7aa; }}
  .limit .agent-head span {{ color:var(--red); background:#fef2f2; border-color:#fecaca; }}
  .metric-grid {{ display:grid; grid-template-columns:repeat(4,minmax(90px,1fr)); gap:10px; }}
  .metric-grid div {{ border:1px solid var(--line); border-radius:8px; padding:12px; background:#fbfdff; min-height:82px; }}
  .metric-grid strong {{ display:block; font-size:24px; }}
  .metric-grid span, .note, td, th, dd, dt {{ color:var(--muted); font-size:13px; line-height:1.5; }}
  .bar {{ height:10px; background:#e5e7eb; border-radius:999px; overflow:hidden; }}
  .bar span {{ display:block; height:100%; background:var(--blue); border-radius:inherit; }}
  dl {{ display:grid; gap:8px; margin:0; }}
  dl div {{ display:grid; grid-template-columns:120px 1fr; gap:12px; }}
  dt {{ font-weight:800; color:var(--ink); }}
  dd {{ margin:0; }}
  .ops-grid {{ display:grid; grid-template-columns:repeat(4,minmax(170px,1fr)); gap:12px; }}
  .ops-grid div {{ border:1px solid var(--line); border-radius:8px; background:#fbfdff; padding:14px; }}
  .ops-grid strong {{ display:block; margin-bottom:8px; }}
  .ops-grid span {{ color:var(--muted); font-size:13px; line-height:1.5; }}
  table {{ width:100%; border-collapse:collapse; font-size:13px; }}
  th, td {{ border:1px solid var(--line); padding:9px 10px; text-align:left; }}
  th {{ background:#eef3f8; color:var(--ink); }}
  .guardrails {{ display:grid; grid-template-columns:repeat(3,minmax(220px,1fr)); gap:12px; }}
  .guardrails div {{ border-left:4px solid var(--blue); background:#fbfdff; padding:14px; border-radius:8px; }}
  .guardrails strong {{ display:block; margin-bottom:6px; }}
  footer {{ padding:22px clamp(14px,3vw,42px); color:var(--muted); border-top:1px solid var(--line); font-size:13px; }}
  @media (max-width:900px) {{ .agent-grid, .ops-grid, .guardrails {{ grid-template-columns:1fr; }} .metric-grid {{ grid-template-columns:repeat(2,1fr); }} dl div {{ grid-template-columns:1fr; }} }}
</style>
</head>
<body>
<header>
  <nav>
    <a href="index.html">Repo Dashboard</a>
    <a href="wishket.html">Wishket</a>
    <a href="daily-plus.html">Daily Plus</a>
    <a href="ai-usage.html" class="active">AI Usage</a>
    <a href="https://github.com/jaeha81/obsidian-agent-brain-system" target="_blank" rel="noreferrer">GitHub</a>
  </nav>
  <h1>AI Usage Dashboard</h1>
  <p>Codex and Claude Code subscription usage, reset-window planning, and fallback guardrails for keeping development moving when one lane reaches a time or usage limit.</p>
</header>
<main>
  <section class="agent-grid">
    {cards}
  </section>
  <section class="panel">
    <h2>Reset Window Operating Plan</h2>
    {render_reset_plan(reset_hours)}
  </section>
  <section class="panel">
    <h2>Recommended Allocation</h2>
    <div class="guardrails">
      <div><strong>Claude Code 60%</strong><span>Use for implementation, repo edits, test fixes, and long-running development sessions.</span></div>
      <div><strong>Codex 40%</strong><span>Use for independent review, debugging, verification, and compact handoff generation.</span></div>
      <div><strong>Limit fallback</strong><span>When blocked, save a handoff, queue the task, switch agents, and resume after the next reset window.</span></div>
    </div>
  </section>
  <section class="panel">
    <h2>Daily Breakdown</h2>
    <table>
      <thead><tr><th>Date</th><th>Claude Code</th><th>Codex</th></tr></thead>
      <tbody>{daily_rows}</tbody>
    </table>
  </section>
</main>
<footer>
  Generated: {esc(generated_at)}. Costs use ${SUB_COST_MONTHLY}/month per lane. Official service banners remain the final source for live limits.
</footer>
</body>
</html>
"""


def generate(days: int = 7) -> Path:
    reset_hours = env_float("AI_USAGE_RESET_HOURS", 5)
    target_sessions = env_int("AI_USAGE_TARGET_SESSIONS_PER_RESET", 2)
    since = datetime.now(KST) - timedelta(days=days)
    reports = [collect_claude(since), collect_codex(since)]
    generated_at = datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S KST")
    html_text = render_dashboard(reports, days, generated_at, reset_hours, target_sessions)
    DOCS.mkdir(parents=True, exist_ok=True)
    output = DOCS / "ai-usage.html"
    output.write_text("\n".join(line.rstrip() for line in html_text.splitlines()) + "\n", encoding="utf-8", newline="\n")
    return output


def main() -> int:
    output = generate()
    print(f"[ai-usage-dashboard] wrote {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
