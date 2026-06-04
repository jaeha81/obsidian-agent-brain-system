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


def status_label(recommendation: str) -> str:
    key = recommendation.split(":", 1)[0]
    return {
        "LIMIT-RISK": "한도 위험",
        "UNDERUSED": "사용 여유",
        "BALANCED": "균형",
    }.get(key, key)


def plan_label(recommendation: str) -> str:
    key = recommendation.split(":", 1)[0]
    if key == "LIMIT-RISK":
        return "한도 위험: 작업을 작은 세션으로 나누고, 핸드오프 노트를 먼저 저장한 뒤 다른 에이전트를 검수나 분석 대기로 둡니다. 막히면 핸드오프를 만들고 작업을 큐에 넣은 다음 다음 리셋 창까지 라인을 전환합니다."
    if key == "UNDERUSED":
        return "사용 여유: 해당 에이전트에 검수, 정리, 저위험 자동화 작업을 더 배정할 수 있습니다."
    return "균형: 현재 배분을 유지하면서 작업 단위를 작게 관리합니다."


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
          <span>{esc(status_label(recommendation))}</span>
        </div>
        <div class="metric-grid">
          <div><strong>{format_int(int(summary["sessions"]))}</strong><span>세션</span></div>
          <div><strong>{format_int(int(summary["messages"]))}</strong><span>메시지</span></div>
          <div><strong>{summary["active_day_percent"]}%</strong><span>활성일</span></div>
          <div><strong>{summary["session_utilization_percent"]}%</strong><span>목표 사용률</span></div>
        </div>
        <div class="bar"><span style="width:{esc(summary["session_utilization_percent"])}%"></span></div>
        <dl>
          <div><dt>토큰</dt><dd>총 {format_int(int(summary["total_tokens"]))} / 캐시 {format_int(int(summary["cached_tokens"]))}</dd></div>
          <div><dt>예산</dt><dd>{days}일 기준 ${summary["prorated_budget_usd"]:.2f}, 월 ${SUB_COST_MONTHLY}</dd></div>
          <div><dt>단가</dt><dd>세션당 {cost_session_text} / 메시지당 {cost_message_text}</dd></div>
          <div><dt>운영안</dt><dd>{esc(plan_label(recommendation))}</dd></div>
        </dl>
      </article>
"""


def render_daily_rows(reports: list[AgentReport]) -> str:
    days = sorted({day for report in reports for day in report.by_day if day != "unknown"})
    if not days:
        return "<tr><td colspan=\"3\">선택한 기간의 로컬 세션 로그가 없습니다.</td></tr>"
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
        <div><strong>창 1</strong><span>Claude Code로 구현을 시작합니다. 프롬프트는 레포 하나, 목표 하나로 제한합니다.</span></div>
        <div><strong>창 2</strong><span>Claude 사용량이 식는 동안 Codex로 검수, 실패 테스트 분석, 구조 리스크 점검을 수행합니다.</span></div>
        <div><strong>창 3</strong><span>검수 결과를 바탕으로 Claude Code에서 수정합니다. 컨텍스트가 무거워지기 전에 핸드오프를 남깁니다.</span></div>
        <div><strong>창 4+</strong><span>남은 용량은 문서화, 작은 자동화, 큐에 쌓인 저위험 개선에 사용합니다.</span></div>
      </div>
      <p class="note">현재 대시보드 리셋 창: {reset_hours:g}시간. 계정 배너가 4시간으로 표시되면 <code>AI_USAGE_RESET_HOURS=4</code>로 실행합니다.</p>
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
<title>AI 사용량 대시보드</title>
<style>
  :root {{ --bg:#f6f8fb; --surface:#fff; --ink:#0f172a; --muted:#64748b; --line:#d8e0ea; --blue:#2563eb; --green:#15803d; --amber:#b45309; --red:#b91c1c; }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; font-family:"Segoe UI", system-ui, sans-serif; background:var(--bg); color:var(--ink); }}
  header {{ background:#0f172a; color:#fff; padding:28px clamp(18px,4vw,48px) 24px; }}
  nav {{ display:flex; gap:10px; flex-wrap:wrap; align-items:center; margin-bottom:18px; }}
  nav a {{ color:#cbd5e1; text-decoration:none; border:1px solid #334155; border-radius:999px; padding:7px 12px; font-size:13px; }}
  nav a.active, nav a:hover {{ color:#fff; border-color:#60a5fa; }}
  nav .auth-start {{ margin-left:auto; }}
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
    <a href="index.html">레포대시보드</a>
    <a href="wishket.html">위시켓</a>
    <a href="daily-plus.html">오늘의플러스</a>
    <a href="ai-usage.html" class="active">AI사용량</a>
    <a href="https://github.com/jaeha81/obsidian-agent-brain-system" target="_blank" rel="noreferrer">깃허브</a>
    <a href="login.html" class="auth-start">로그인</a>
    <a href="/api/logout">로그아웃</a>
  </nav>
  <h1>AI 사용량 대시보드</h1>
  <p>Codex와 Claude Code 구독 사용량, 리셋 창 운영 계획, 한쪽 사용량이 막혔을 때의 전환 기준을 한 화면에서 확인합니다.</p>
</header>
<main>
  <section class="agent-grid">
    {cards}
  </section>
  <section class="panel">
    <h2>리셋 창 운영 계획</h2>
    {render_reset_plan(reset_hours)}
  </section>
  <section class="panel">
    <h2>권장 배분</h2>
    <div class="guardrails">
      <div><strong>Claude Code 60%</strong><span>구현, 레포 편집, 테스트 수정, 긴 개발 세션에 사용합니다.</span></div>
      <div><strong>Codex 40%</strong><span>독립 검수, 디버깅, 검증, 짧은 핸드오프 작성에 사용합니다.</span></div>
      <div><strong>한도 fallback</strong><span>막히면 핸드오프를 저장하고 작업을 큐에 넣은 뒤 에이전트를 전환해 다음 리셋 창 이후 재개합니다.</span></div>
    </div>
  </section>
  <section class="panel">
    <h2>일별 사용량</h2>
    <table>
      <thead><tr><th>날짜</th><th>Claude Code</th><th>Codex</th></tr></thead>
      <tbody>{daily_rows}</tbody>
    </table>
  </section>
</main>
<footer>
  생성: {esc(generated_at)}. 비용은 라인당 월 ${SUB_COST_MONTHLY} 기준입니다. 실시간 한도는 공식 서비스 배너를 최종 기준으로 봅니다.
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
