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
    _humanize_delta,
    _parse_ts,
    collect_cli_usage_state,
    collect_claude,
    collect_codex,
    efficiency_signals,
    format_int,
    resolve_quota,
    summarize_usage,
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


def _quota_val(val: object) -> str:
    if val is None or str(val).strip() == "":
        return "공식 잔여량 미수집"
    return str(val)


# --- efficiency status (efficiency_signals based, replaces fake utilization) ---
def signal_class(status: str) -> str:
    return {"LIMIT-RISK": "limit", "IDLE": "underused", "BALANCED": "balanced"}.get(status, "balanced")


def signal_label(status: str) -> str:
    return {"LIMIT-RISK": "한도 위험", "IDLE": "유휴", "BALANCED": "균형"}.get(status, status)


def agent_action(name: str, status: str) -> str:
    is_codex = "codex" in name.lower()
    if status == "LIMIT-RISK":
        return "핸드오프 노트를 먼저 저장하고, 다음 리셋 창까지 다른 에이전트를 검수·분석 대기로 둡니다."
    if status == "IDLE":
        if is_codex:
            return "유휴 — 미검수 diff·실패 테스트 분석·문서 검증을 배정합니다."
        return "유휴 — 저위험 backlog(문서·테스트·리팩토링)를 배정합니다."
    return "균형 — 현재 배분을 유지하고 작업 단위를 작게 가져갑니다."


def humanize_tokens(n: int) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return str(n)


def src_badge(source: str | None) -> str:
    if source == "manual":
        return '<em class="src manual">확정</em>'
    if source == "estimated":
        return '<em class="src est">추정</em>'
    return ""


# --- SVG chart helpers (server-side, no build step) ---
def _stacked_bar_svg(segments: list[tuple[float, str, str]], height: int = 22) -> str:
    total = sum(max(0.0, v) for v, _, _ in segments) or 1.0
    parts, x = [], 0.0
    for v, color, label in segments:
        w = max(0.0, v) / total * 100
        if w <= 0:
            continue
        parts.append(
            f'<rect x="{x:.2f}" y="0" width="{w:.2f}" height="{height}" fill="{color}">'
            f"<title>{esc(label)}</title></rect>"
        )
        x += w
    return (
        f'<svg class="chart" viewBox="0 0 100 {height}" preserveAspectRatio="none" '
        f'role="img">{"".join(parts)}</svg>'
    )


def _legend(items: list[tuple[str, str]]) -> str:
    spans = "".join(
        f'<span class="lg"><i style="background:{c}"></i>{esc(label)}</span>' for c, label in items
    )
    return f'<div class="legend">{spans}</div>'


def render_window_gauge(quota_entry: dict, reset_hours: float, now: datetime) -> str:
    reset_at = quota_entry.get("reset_at")
    rt = _parse_ts(reset_at) if reset_at else None
    if not rt:
        return (
            '<div class="gauge-wrap">'
            '<svg class="gauge" viewBox="0 0 100 8" preserveAspectRatio="none" role="img">'
            '<rect width="100" height="8" rx="4" fill="var(--line)"/></svg>'
            '<span class="gauge-label">리셋창 미수집 — 한도 이벤트/수동 입력 시 표시</span></div>'
        )
    span = timedelta(hours=reset_hours)
    start = rt - span
    frac = (now - start).total_seconds() / span.total_seconds()
    frac = min(1.0, max(0.0, frac))
    pct = frac * 100
    remaining = quota_entry.get("remaining_until_reset") or _humanize_delta(rt - now)
    color = "var(--red)" if frac > 0.85 else ("var(--amber)" if frac > 0.6 else "var(--green)")
    return (
        '<div class="gauge-wrap">'
        '<svg class="gauge" viewBox="0 0 100 8" preserveAspectRatio="none" role="img">'
        '<rect width="100" height="8" rx="4" fill="var(--line)"/>'
        f'<rect width="{pct:.1f}" height="8" rx="4" fill="{color}"/></svg>'
        f'<span class="gauge-label">리셋창 {pct:.0f}% 경과 · 잔여 {esc(remaining)} '
        f"{src_badge(quota_entry.get('source'))}</span></div>"
    )


def render_model_mix(model_mix: dict) -> str:
    if not model_mix or model_mix.get("total", 0) == 0:
        return '<p class="note">모델 호출 로그 없음</p>'
    pct = model_mix["percent"]
    rows = [
        ("haiku", pct["haiku"], "var(--green)", "Haiku"),
        ("sonnet", pct["sonnet"], "var(--blue)", "Sonnet"),
        ("opus", pct["opus"], "#7c3aed", "Opus"),
        ("기타", pct["기타"], "var(--muted)", "기타"),
    ]
    segs = [(v, c, f"{name} {v}%") for _, v, c, name in rows]
    legend = _legend([(c, f"{name} {v}%") for _, v, c, name in rows if v > 0])
    return _stacked_bar_svg(segs) + legend


def render_agent_split(ab: dict) -> str:
    c, x = ab.get("claude_sessions", 0), ab.get("codex_sessions", 0)
    if not (c or x):
        return '<p class="note">세션 데이터 없음</p>'
    segs = [(c, "var(--blue)", f"Claude {c}세션"), (x, "var(--green)", f"Codex {x}세션")]
    legend = _legend([("var(--blue)", f"Claude {c}"), ("var(--green)", f"Codex {x}")])
    mult = ab.get("multiple", 0)
    note = (
        f'<p class="note">{esc(ab.get("heavier", ""))}가 {mult:g}배 더 활발</p>'
        if mult
        else '<p class="note">한쪽 데이터만 존재</p>'
    )
    return _stacked_bar_svg(segs) + legend + note


def render_limit_freq(windows: list[dict]) -> str:
    counts = [w.get("count", 0) for w in windows]
    peak = max(counts) if counts else 0
    if peak == 0:
        return f'<p class="note">최근 {len(windows) or 8}개 리셋 창에 한도 이벤트 없음</p>'
    n = len(windows)
    bw = 100 / n
    bars = []
    for i, w in enumerate(windows):
        h = w.get("count", 0) / peak * 100
        x = i * bw + bw * 0.15
        color = "var(--red)" if w.get("count", 0) > 0 else "var(--line)"
        bars.append(
            f'<rect x="{x:.2f}" y="{100 - h:.2f}" width="{bw * 0.7:.2f}" height="{h:.2f}" '
            f'fill="{color}"><title>{w.get("count", 0)}건</title></rect>'
        )
    return (
        '<svg class="chart vbar" viewBox="0 0 100 100" preserveAspectRatio="none" '
        f'role="img">{"".join(bars)}</svg>'
        '<p class="note">최근 8개 리셋 창의 한도 이벤트 (좌→우, 우측이 최신)</p>'
    )


def render_daily_spark(reports: list[AgentReport]) -> str:
    days = sorted({d for r in reports for d in r.by_day if d != "unknown"})[-14:]
    if not days:
        return '<p class="note">기간 내 일별 데이터 없음</p>'
    peak = max(
        (r.by_day[d].sessions for r in reports for d in days if d in r.by_day),
        default=0,
    ) or 1
    n = len(days)
    gw = 100 / n
    colors = ["var(--blue)", "var(--green)"]
    bars = []
    for i, d in enumerate(days):
        for j, r in enumerate(reports[:2]):
            stats = r.by_day.get(d)
            sess = stats.sessions if stats else 0
            h = sess / peak * 100
            bw = gw * 0.4
            x = i * gw + gw * 0.1 + j * bw
            bars.append(
                f'<rect x="{x:.2f}" y="{100 - h:.2f}" width="{bw * 0.9:.2f}" height="{h:.2f}" '
                f'fill="{colors[j % 2]}"><title>{esc(d)} · {esc(r.name)} {sess}세션</title></rect>'
            )
    legend = _legend([("var(--blue)", "Claude 세션"), ("var(--green)", "Codex 세션")])
    return (
        '<svg class="chart vbar" viewBox="0 0 100 100" preserveAspectRatio="none" '
        f'role="img">{"".join(bars)}</svg>'
        + legend
    )


def render_agent_card(
    report: AgentReport,
    days: int,
    reset_hours: float,
    status_entry: dict,
    quota_entry: dict,
    now: datetime,
) -> str:
    summary = summarize_usage(
        report,
        days=days,
        monthly_usd=SUB_COST_MONTHLY,
        reset_hours=reset_hours,
    )
    status = status_entry.get("status", "BALANCED")
    cost_per_session = summary["cost_per_session_usd"]
    cost_per_message = summary["cost_per_message_usd"]
    cost_session_text = "N/A" if cost_per_session is None else f"${cost_per_session:.2f}"
    cost_message_text = "N/A" if cost_per_message is None else f"${cost_per_message:.3f}"

    is_codex = "codex" in report.name.lower()
    in_tok = int(summary["input_tokens"])
    out_tok = int(summary["output_tokens"])
    cached_tok = int(summary["cached_tokens"])
    real_tok = in_tok + out_tok
    if is_codex and real_tok == 0 and cached_tok == 0:
        token_text = "미수집"
    else:
        prompt_total = in_tok + cached_tok
        hit = round(cached_tok / prompt_total * 100) if prompt_total else 0
        token_text = f"실토큰 {humanize_tokens(real_tok)} · 캐시적중 {hit}%"

    official_status = _quota_val(quota_entry.get("limit_status"))
    reset_at_val = _quota_val(quota_entry.get("reset_at"))
    remaining_val = _quota_val(quota_entry.get("remaining_until_reset"))
    quota_cls = "uncollected" if official_status == "공식 잔여량 미수집" else ""
    src = src_badge(quota_entry.get("source"))

    return f"""
      <article class="agent-card {signal_class(status)}">
        <div class="agent-head">
          <h3>{esc(report.name)}</h3>
          <span>{esc(signal_label(status))}</span>
        </div>
        <p class="action"><strong>지금 할 것</strong> {esc(agent_action(report.name, status))}</p>
        <div class="metric-grid">
          <div><strong>{format_int(int(summary["sessions"]))}</strong><span>세션</span></div>
          <div><strong>{format_int(int(summary["messages"]))}</strong><span>메시지</span></div>
          <div><strong>{summary["active_day_percent"]}%</strong><span>활성일</span></div>
          <div><strong>{status_entry.get("current_load", 0)}</strong><span>현재창 부하</span></div>
        </div>
        {render_window_gauge(quota_entry, reset_hours, now)}
        <dl>
          <div><dt>토큰</dt><dd>{esc(token_text)}</dd></div>
          <div><dt>예산</dt><dd>{days}일 기준 ${summary["prorated_budget_usd"]:.2f}, 월 ${SUB_COST_MONTHLY}</dd></div>
          <div><dt>단가</dt><dd>세션당 {cost_session_text} / 메시지당 {cost_message_text}</dd></div>
        </dl>
        <div class="official-quota">
          <h4 class="quota-title">공식 잔여량 (Official Quota) {src}</h4>
          <dl class="quota-dl">
            <div><dt>한도 상태</dt><dd class="{quota_cls}">{esc(official_status)}</dd></div>
            <div><dt>리셋 예정</dt><dd class="{quota_cls}">{esc(reset_at_val)}</dd></div>
            <div><dt>리셋까지 잔여</dt><dd class="{quota_cls}">{esc(remaining_val)}</dd></div>
          </dl>
        </div>
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


def render_bucky_routing() -> str:
    """Bucky routing rules — when to use each agent and how to handle quota limits."""
    routes = [
        {
            "condition": "Claude 여유 있음",
            "when": "최근 리셋 창 한도 이벤트 없음 (균형)",
            "action": "구현 · 수정 · 테스트 작업 배정",
            "detail": "Assign implementation, code edits, and test runs to Claude Code. Use for long coding sessions and repository-level changes.",
            "cls": "route-ok",
        },
        {
            "condition": "Claude 한도 도달",
            "when": "현재/직전 리셋 창에 한도 이벤트",
            "action": "Codex로 전환: 검수 · 재현 · 핸드오프 · 작업분해",
            "detail": "Save handoff notes immediately, then switch to Codex for code review, test reproduction, handoff compilation, and task decomposition until the next reset window.",
            "cls": "route-limit",
        },
        {
            "condition": "Codex 여유 있음",
            "when": "미검수 diff 처리 시기",
            "action": "미검수 diff · 실패 테스트 분석 · Daily Plus/문서 검증",
            "detail": "Run Codex on unreviewed diffs, failing test analysis, and Daily Plus / documentation verification to convert spare quota into quality checks.",
            "cls": "route-ok",
        },
        {
            "condition": "리셋 전 여유 큼",
            "when": "현재 창 부하 낮음 & 리셋 임박",
            "action": "저위험 backlog 자동 추천",
            "detail": "When significant quota remains before the next reset window, recommend low-risk backlog items: documentation updates, minor refactors, and test coverage improvements.",
            "cls": "route-backlog",
        },
    ]
    items = "\n".join(
        f"""        <div class="route-item {r['cls']}">
          <strong>{esc(r['condition'])}</strong>
          <em>{esc(r['when'])}</em>
          <p>{esc(r['action'])}</p>
          <small>{esc(r['detail'])}</small>
        </div>"""
        for r in routes
    )
    return f"""      <div class="bucky-grid">
{items}
      </div>"""


def render_cli_usage_state(usage_state: dict[str, object] | None) -> str:
    """Render observed CLI state so the dashboard is not just a static policy page."""
    if not usage_state:
        usage_state = {
            "total_calls": 0,
            "limit_events": 0,
            "recommended_claude_model": "sonnet",
            "latest_limit_event": None,
            "models": {},
        }
    latest = usage_state.get("latest_limit_event")
    if isinstance(latest, dict):
        latest_text = (
            f"{latest.get('timestamp', '-')} · {latest.get('model', '-')} · "
            f"{latest.get('detail', '-')}"
        )
    else:
        latest_text = "최근 한도 이벤트 없음"

    models = usage_state.get("models")
    rows = []
    if isinstance(models, dict):
        for model, stats in sorted(models.items()):
            if not isinstance(stats, dict):
                continue
            rows.append(
                "<tr>"
                f"<td>{esc(model)}</td>"
                f"<td>{esc(stats.get('calls', 0))}</td>"
                f"<td>{esc(stats.get('successes', 0))}</td>"
                f"<td>{esc(stats.get('failures', 0))}</td>"
                "</tr>"
            )
    if not rows:
        rows.append('<tr><td colspan="4">아직 CLI 호출 로그가 없습니다.</td></tr>')

    recommended = str(usage_state.get("recommended_claude_model") or "sonnet")
    if recommended == "haiku":
        policy = (
            "Haiku 우선: 상태 확인, 분류, 짧은 요약, 태그/추출은 Haiku로 보내고 "
            "Sonnet 절약: 구현, 파일 편집, 테스트 수정, 긴 분석에만 Sonnet을 사용합니다."
        )
    else:
        policy = (
            "Sonnet 기본: 구현과 긴 분석은 Sonnet을 유지하되, 반복 분류/상태 확인은 Haiku로 분리합니다."
        )

    return f"""
    <section class="panel">
      <h2>실제 감지 상태</h2>
      <div class="state-grid">
        <div><strong>{esc(usage_state.get("total_calls", 0))}</strong><span>최근 CLI 호출</span></div>
        <div><strong>{esc(usage_state.get("limit_events", 0))}</strong><span>Claude 한도 이벤트</span></div>
        <div><strong>{esc(recommended)}</strong><span>권장 Claude 모델</span></div>
      </div>
      <p class="note">{esc(latest_text)}</p>
      <table>
        <thead><tr><th>모델</th><th>호출</th><th>성공</th><th>실패</th></tr></thead>
        <tbody>{"".join(rows)}</tbody>
      </table>
      <p class="note"><strong>{esc(policy)}</strong></p>
    </section>
"""


def render_efficiency_panel(signals: dict[str, object]) -> str:
    mm = signals.get("model_mix", {}) or {}
    ab = signals.get("agent_balance", {}) or {}
    lf = signals.get("limit_frequency", {}) or {}
    status = str(signals.get("status", "BALANCED"))
    return f"""
    <section class="panel">
      <h2>효율 신호 <span class="status-pill {signal_class(status)}">{esc(signal_label(status))}</span></h2>
      <div class="signal-grid">
        <div class="signal-box"><h4>모델 믹스</h4>{render_model_mix(mm)}</div>
        <div class="signal-box"><h4>Claude vs Codex 배분</h4>{render_agent_split(ab)}</div>
        <div class="signal-box"><h4>한도 도달 빈도</h4>{render_limit_freq(lf.get("windows", []))}</div>
      </div>
    </section>
"""


def render_dashboard(
    reports: list[AgentReport],
    days: int,
    generated_at: str,
    reset_hours: float,
    target_sessions_per_reset: int = 2,
    usage_state: dict[str, object] | None = None,
    signals: dict[str, object] | None = None,
    quota: dict[str, dict] | None = None,
    now: datetime | None = None,
) -> str:
    if now is None:
        now = datetime.now(KST)
    claude = reports[0] if reports else AgentReport(name="Claude Code")
    codex = reports[1] if len(reports) > 1 else AgentReport(name="Codex")
    if signals is None:
        signals = efficiency_signals(claude, codex, usage_state, reset_hours, now)
    if quota is None:
        quota = resolve_quota(usage_state, reset_hours, now)

    per_agent = signals.get("per_agent", {})  # type: ignore[union-attr]
    default_status = {"status": "BALANCED", "current_load": 0}
    default_quota = {"limit_status": None, "reset_at": None, "remaining_until_reset": None, "source": None}
    cards = "\n".join(
        render_agent_card(
            report,
            days,
            reset_hours,
            per_agent.get(report.name, default_status),
            quota.get(report.name, default_quota),
            now,
        )
        for report in reports
    )
    daily_rows = render_daily_rows(reports)
    bucky_routing = render_bucky_routing()
    cli_state = render_cli_usage_state(usage_state)
    efficiency_panel = render_efficiency_panel(signals)
    daily_spark = render_daily_spark(reports)
    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<link rel="manifest" href="/manifest.json">
<meta name="theme-color" content="#58a6ff">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="Bucky">
<link rel="apple-touch-icon" href="/icons/icon-192.svg">
<script>if('serviceWorker' in navigator){{navigator.serviceWorker.register('/sw.js');}}</script>
<title>AI Usage · AI 사용량 대시보드</title>
<script>
(function(){{
  function getCookie(n){{var v=document.cookie.split(';');for(var i=0;i<v.length;i++){{var p=v[i].trim();if(p.startsWith(n+'='))return p.substring(n.length+1);}}return '';}}
  document.documentElement.style.visibility='hidden';
  if(!getCookie('bucky_auth')){{location.replace('/login.html?r='+encodeURIComponent(location.pathname));}}
  else{{document.documentElement.style.visibility='';}}
  if(window!==window.top){{document.documentElement.classList.add('in-iframe');}}
}})();
</script>
<style>.in-iframe header,.in-iframe footer{{display:none!important}}</style>
<script src="/shared/nav.js" defer></script>
<script src="/shared/auth.js"></script>
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
  .gen-stamp {{ display:flex; align-items:baseline; gap:14px; margin-top:20px; padding:14px 20px; background:rgba(255,255,255,.08); border:1px solid rgba(255,255,255,.15); border-radius:10px; }}
  .gen-label {{ font-size:12px; color:#94a3b8; text-transform:uppercase; letter-spacing:.07em; white-space:nowrap; }}
  .gen-time {{ font-size:clamp(18px,2.5vw,30px); font-weight:700; color:#f8fafc; font-variant-numeric:tabular-nums; letter-spacing:-.02em; }}
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
  .state-grid {{ display:grid; grid-template-columns:repeat(3,minmax(160px,1fr)); gap:10px; margin-bottom:12px; }}
  .state-grid div {{ border:1px solid var(--line); border-radius:8px; padding:12px; background:#fbfdff; }}
  .state-grid strong {{ display:block; font-size:22px; }}
  .state-grid span {{ color:var(--muted); font-size:13px; }}
  .metric-grid span, .note, td, th, dd, dt {{ color:var(--muted); font-size:13px; line-height:1.5; }}
  .bar {{ height:10px; background:#e5e7eb; border-radius:999px; overflow:hidden; }}
  .bar span {{ display:block; height:100%; background:var(--blue); border-radius:inherit; }}
  dl {{ display:grid; gap:8px; margin:0; }}
  dl div {{ display:grid; grid-template-columns:120px 1fr; gap:12px; }}
  dt {{ font-weight:800; color:var(--ink); }}
  dd {{ margin:0; }}
  .official-quota {{ border-top:1px solid var(--line); padding-top:12px; }}
  .quota-title {{ margin:0 0 10px; font-size:12px; font-weight:700; color:var(--muted); text-transform:uppercase; letter-spacing:.06em; }}
  .quota-dl {{ display:grid; gap:6px; margin:0; }}
  .quota-dl div {{ display:grid; grid-template-columns:130px 1fr; gap:8px; }}
  .uncollected {{ color:var(--amber) !important; font-style:italic; }}
  .ops-grid {{ display:grid; grid-template-columns:repeat(4,minmax(170px,1fr)); gap:12px; }}
  .ops-grid div {{ border:1px solid var(--line); border-radius:8px; background:#fbfdff; padding:14px; }}
  .ops-grid strong {{ display:block; margin-bottom:8px; }}
  .ops-grid span {{ color:var(--muted); font-size:13px; line-height:1.5; }}
  .bucky-grid {{ display:grid; grid-template-columns:repeat(2,minmax(240px,1fr)); gap:14px; }}
  .route-item {{ border-radius:8px; padding:16px; border:1px solid var(--line); background:#fbfdff; display:grid; gap:6px; }}
  .route-item strong {{ font-size:15px; color:var(--ink); }}
  .route-item em {{ font-size:12px; color:var(--muted); font-style:normal; }}
  .route-item p {{ margin:0; font-size:13px; font-weight:600; color:var(--ink); }}
  .route-item small {{ font-size:12px; color:var(--muted); line-height:1.5; display:block; }}
  .route-ok {{ border-left:4px solid var(--green); }}
  .route-limit {{ border-left:4px solid var(--red); }}
  .route-backlog {{ border-left:4px solid var(--blue); }}
  table {{ width:100%; border-collapse:collapse; font-size:13px; }}
  th, td {{ border:1px solid var(--line); padding:9px 10px; text-align:left; }}
  th {{ background:#eef3f8; color:var(--ink); }}
  .guardrails {{ display:grid; grid-template-columns:repeat(3,minmax(220px,1fr)); gap:12px; }}
  .guardrails div {{ border-left:4px solid var(--blue); background:#fbfdff; padding:14px; border-radius:8px; }}
  .guardrails strong {{ display:block; margin-bottom:6px; }}
  footer {{ padding:22px clamp(14px,3vw,42px); color:var(--muted); border-top:1px solid var(--line); font-size:13px; }}
  .action {{ margin:0; padding:10px 12px; background:#f1f5f9; border:1px solid var(--line); border-radius:8px; font-size:13px; color:var(--ink); line-height:1.5; }}
  .action strong {{ color:var(--blue); margin-right:6px; }}
  .limit .action {{ background:#fef2f2; border-color:#fecaca; }}
  .underused .action {{ background:#fff7ed; border-color:#fed7aa; }}
  .gauge-wrap {{ display:grid; gap:6px; }}
  .gauge {{ width:100%; height:8px; display:block; }}
  .gauge-label {{ font-size:12px; color:var(--muted); }}
  .src {{ font-style:normal; font-weight:800; font-size:11px; padding:1px 6px; border-radius:999px; }}
  .src.est {{ color:var(--amber); background:#fff7ed; border:1px solid #fed7aa; }}
  .src.manual {{ color:var(--green); background:#f0fdf4; border:1px solid #bbf7d0; }}
  .signal-grid {{ display:grid; grid-template-columns:repeat(3,minmax(220px,1fr)); gap:14px; }}
  .signal-box {{ border:1px solid var(--line); border-radius:8px; padding:14px; background:#fbfdff; display:grid; gap:8px; align-content:start; }}
  .signal-box h4 {{ margin:0; font-size:13px; color:var(--muted); text-transform:uppercase; letter-spacing:.05em; }}
  .chart {{ width:100%; display:block; border-radius:6px; }}
  .chart.vbar {{ height:90px; background:#fff; border:1px solid var(--line); }}
  .legend {{ display:flex; flex-wrap:wrap; gap:10px; }}
  .legend .lg {{ display:inline-flex; align-items:center; gap:5px; font-size:12px; color:var(--muted); }}
  .legend .lg i {{ width:11px; height:11px; border-radius:3px; display:inline-block; }}
  .status-pill {{ font-size:13px; font-weight:800; padding:3px 10px; border-radius:999px; border:1px solid var(--line); vertical-align:middle; margin-left:8px; }}
  .status-pill.balanced {{ color:var(--green); background:#f0fdf4; border-color:#bbf7d0; }}
  .status-pill.underused {{ color:var(--amber); background:#fff7ed; border-color:#fed7aa; }}
  .status-pill.limit {{ color:var(--red); background:#fef2f2; border-color:#fecaca; }}
  @media (max-width:900px) {{ .agent-grid, .ops-grid, .guardrails, .bucky-grid, .state-grid, .signal-grid {{ grid-template-columns:1fr; }} .metric-grid {{ grid-template-columns:repeat(2,1fr); }} dl div, .quota-dl div {{ grid-template-columns:1fr; }} }}
</style>
</head>
<body>
<header>
  <nav class="jh-nav"></nav>
  <h1>AI Usage 대시보드</h1>
  <p>Codex와 Claude Code 구독 사용량, 공식 잔여량, Bucky 운영 규칙, 리셋 창 전환 기준을 한 화면에서 확인합니다.</p>
  <div class="gen-stamp">
    <span class="gen-label">페이지 생성 시각</span>
    <time class="gen-time">{esc(generated_at)}</time>
  </div>
</header>
<main>
  <section class="agent-grid">
    {cards}
  </section>
  {efficiency_panel}
  {cli_state}
  <section class="panel">
    <h2>Bucky 운영 규칙</h2>
    {bucky_routing}
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
    {daily_spark}
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
    usage_state = collect_cli_usage_state(since=since)
    generated_at = datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S KST")
    html_text = render_dashboard(reports, days, generated_at, reset_hours, target_sessions, usage_state)
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
