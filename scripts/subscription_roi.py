#!/usr/bin/env python3
"""
Subscription ROI Measurement
Codex + Claude Code 구독 사용량 측정 → $100×2 ROI 검증.

수집 대상:
  - Codex: ~/.codex/sessions/YYYY/MM/DD/rollout-*.jsonl
  - Claude Code: ~/.claude/projects/<project>/*.jsonl

집계:
  - 세션 수, 메시지 수, 토큰 사용량 (가능한 경우)
  - 일별 분포, 활동 일수
  - 비대칭 분석 (Claude vs Codex)

Usage:
    python subscription_roi.py                    # 최근 7일
    python subscription_roi.py --days 30          # 최근 30일
    python subscription_roi.py --save             # Vault에 리포트 저장
    python subscription_roi.py --project obsidian # 특정 프로젝트만
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys

# Force UTF-8 stdout on Windows (cp949 default breaks unicode dashes/emojis)
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

KST = timezone(timedelta(hours=9))
USER_HOME = Path(os.environ.get("USERPROFILE", os.path.expanduser("~")))
CODEX_SESSIONS = USER_HOME / ".codex" / "sessions"
CLAUDE_PROJECTS = USER_HOME / ".claude" / "projects"
VAULT_REPORTS = Path("G:/내 드라이브/obsidian-agent-brain-system/ObsidianVault/00_System/roi-reports")
ROOT = Path(__file__).resolve().parents[1]
CLI_TOOLS_LOG = ROOT / "ObsidianVault" / "05_Logs" / "cli-tools.jsonl"
QUOTA_OVERRIDE_PATH = ROOT / "data" / "ai_usage_quota.json"

SUB_COST_MONTHLY = 100  # USD per service
CLI_LIMIT_PATTERNS = re.compile(
    r"(usage limit|rate limit|subscription limit|out of .*usage|resets .*(am|pm)|"
    r"too many requests|429|사용\s*한도|구독\s*한도|한도\s*초과|할당량\s*초과)",
    re.IGNORECASE,
)


def _parse_ts(value: object) -> datetime | None:
    """Parse an ISO timestamp string into a KST-aware datetime, or None."""
    if not value:
        return None
    text = str(value).strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=KST)
    return dt.astimezone(KST)


def _humanize_delta(delta: timedelta) -> str:
    """Render a timedelta as '3h 12m', or '리셋 지남' when already past."""
    total = int(delta.total_seconds())
    if total <= 0:
        return "리셋 지남"
    hours, rem = divmod(total, 3600)
    minutes = rem // 60
    if hours:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"


@dataclass
class DailyStats:
    sessions: int = 0
    messages: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cached_tokens: int = 0


@dataclass
class AgentReport:
    name: str
    total_sessions: int = 0
    total_messages: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_cached_tokens: int = 0
    active_days: set = field(default_factory=set)
    by_day: dict = field(default_factory=lambda: defaultdict(DailyStats))
    # Per-message timestamps for reset-window bucketing (added Phase 1-1)
    event_times: list = field(default_factory=list)
    # Official quota tracking — populated externally; None means not yet collected
    official_limit_status: str | None = None
    last_limit_event: str | None = None
    reset_at: str | None = None
    remaining_until_reset: str | None = None
    quota_source: str | None = None  # "estimated" | "manual" | None

    @property
    def total_tokens(self) -> int:
        return self.total_input_tokens + self.total_output_tokens

    def add_session(
        self,
        day: str,
        messages: int,
        in_tok: int,
        out_tok: int,
        cached: int,
        event_times: list | None = None,
    ) -> None:
        self.total_sessions += 1
        self.total_messages += messages
        self.total_input_tokens += in_tok
        self.total_output_tokens += out_tok
        self.total_cached_tokens += cached
        self.active_days.add(day)
        s = self.by_day[day]
        s.sessions += 1
        s.messages += messages
        s.input_tokens += in_tok
        s.output_tokens += out_tok
        s.cached_tokens += cached
        if event_times:
            self.event_times.extend(event_times)


def parse_codex_file(path: Path) -> tuple[str, int, int, int, int, list[datetime]]:
    """Return (day_iso, msg_count, in_tok, out_tok, cached_tok, event_times)."""
    msg_count = 0
    in_tok = out_tok = cached_tok = 0
    event_times: list[datetime] = []
    day = path.parent.name
    month = path.parent.parent.name
    year = path.parent.parent.parent.name
    day_iso = f"{year}-{month}-{day}"

    try:
        with path.open("r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                t = rec.get("type", "")
                payload = rec.get("payload", {}) or {}
                if t in ("user_message", "agent_message", "response_item", "message"):
                    msg_count += 1
                    ts = _parse_ts(rec.get("timestamp") or payload.get("timestamp"))
                    if ts:
                        event_times.append(ts)
                # token usage often in token_count or usage payload
                usage = payload.get("usage") or payload.get("token_usage") or {}
                if isinstance(usage, dict):
                    in_tok += int(usage.get("input_tokens") or usage.get("prompt_tokens") or 0)
                    out_tok += int(usage.get("output_tokens") or usage.get("completion_tokens") or 0)
                    cached_tok += int(usage.get("cached_input_tokens") or usage.get("cache_read_tokens") or 0)
    except OSError:
        pass

    return day_iso, msg_count, in_tok, out_tok, cached_tok, event_times


def parse_claude_file(path: Path) -> tuple[str, int, int, int, int, list[datetime]]:
    """Return (day_iso, msg_count, in_tok, out_tok, cached_tok, event_times). Day from mtime."""
    msg_count = 0
    in_tok = out_tok = cached_tok = 0
    event_times: list[datetime] = []
    try:
        mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=KST)
        day_iso = mtime.strftime("%Y-%m-%d")
    except OSError:
        day_iso = "unknown"

    try:
        with path.open("r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                t = rec.get("type", "")
                if t in ("user", "assistant"):
                    msg_count += 1
                    ts = _parse_ts(rec.get("timestamp"))
                    if ts:
                        event_times.append(ts)
                msg = rec.get("message") or {}
                usage = msg.get("usage") if isinstance(msg, dict) else None
                if isinstance(usage, dict):
                    in_tok += int(usage.get("input_tokens") or 0)
                    out_tok += int(usage.get("output_tokens") or 0)
                    cached_tok += int(usage.get("cache_read_input_tokens") or 0)
    except OSError:
        pass

    return day_iso, msg_count, in_tok, out_tok, cached_tok, event_times


def collect_codex(since: datetime, project_filter: str | None = None) -> AgentReport:
    rep = AgentReport(name="Codex")
    if not CODEX_SESSIONS.exists():
        return rep
    for jsonl in CODEX_SESSIONS.rglob("rollout-*.jsonl"):
        try:
            mtime = datetime.fromtimestamp(jsonl.stat().st_mtime, tz=KST)
        except OSError:
            continue
        if mtime < since:
            continue
        day, msgs, in_t, out_t, cached, ev_times = parse_codex_file(jsonl)
        rep.add_session(day, msgs, in_t, out_t, cached, ev_times)
    return rep


def collect_claude(since: datetime, project_filter: str | None = None) -> AgentReport:
    rep = AgentReport(name="Claude Code")
    if not CLAUDE_PROJECTS.exists():
        return rep
    for proj_dir in CLAUDE_PROJECTS.iterdir():
        if not proj_dir.is_dir():
            continue
        if project_filter and project_filter.lower() not in proj_dir.name.lower():
            continue
        for jsonl in proj_dir.rglob("*.jsonl"):
            try:
                mtime = datetime.fromtimestamp(jsonl.stat().st_mtime, tz=KST)
            except OSError:
                continue
            if mtime < since:
                continue
            day, msgs, in_t, out_t, cached, ev_times = parse_claude_file(jsonl)
            rep.add_session(day, msgs, in_t, out_t, cached, ev_times)
    return rep


def format_int(n: int) -> str:
    return f"{n:,}"


def collect_cli_usage_state(
    log_path: Path | str | None = None,
    since: datetime | None = None,
) -> dict[str, object]:
    """Summarize real Bucky/Claude/Codex CLI call state from the append-only log."""
    path = Path(log_path) if log_path is not None else CLI_TOOLS_LOG
    models: dict[str, dict[str, int]] = {}
    state: dict[str, object] = {
        "total_calls": 0,
        "successes": 0,
        "failures": 0,
        "limit_events": 0,
        "latest_limit_event": None,
        "limit_event_times": [],
        "recommended_claude_model": "sonnet",
        "models": models,
    }
    if not path.exists():
        return state

    def model_bucket(model: str) -> dict[str, int]:
        key = model or "unknown"
        if key not in models:
            models[key] = {"calls": 0, "successes": 0, "failures": 0}
        return models[key]

    try:
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    except OSError:
        return state

    for line in lines:
        if not line.strip():
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue

        timestamp = str(rec.get("timestamp") or "")
        if since and timestamp:
            try:
                ts = datetime.fromisoformat(timestamp)
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=KST)
                if ts < since:
                    continue
            except ValueError:
                pass

        model = str(rec.get("model") or "unknown")
        success = bool(rec.get("success"))
        detail = str(rec.get("response_summary") or "")
        bucket = model_bucket(model)
        bucket["calls"] += 1
        state["total_calls"] = int(state["total_calls"]) + 1
        if success:
            bucket["successes"] += 1
            state["successes"] = int(state["successes"]) + 1
        else:
            bucket["failures"] += 1
            state["failures"] = int(state["failures"]) + 1

        command = str(rec.get("command") or "").lower()
        if "claude" in command and not success and CLI_LIMIT_PATTERNS.search(detail):
            state["limit_events"] = int(state["limit_events"]) + 1
            ev_ts = _parse_ts(timestamp)
            if ev_ts:
                state["limit_event_times"].append(ev_ts)  # type: ignore[union-attr]
            state["latest_limit_event"] = {
                "timestamp": timestamp,
                "model": model,
                "task_type": str(rec.get("task_type") or ""),
                "source": str(rec.get("source") or ""),
                "detail": detail,
            }

    sonnet = models.get("sonnet", {})
    haiku = models.get("haiku", {})
    if int(state["limit_events"]) > 0 or int(sonnet.get("failures", 0)) > 0:
        state["recommended_claude_model"] = "haiku"
    elif int(haiku.get("calls", 0)) == 0 and int(state["total_calls"]) > 0:
        state["recommended_claude_model"] = "haiku"

    return state


def summarize_usage(
    report: AgentReport,
    days: int,
    monthly_usd: float = SUB_COST_MONTHLY,
    reset_hours: float = 5,
    target_sessions_per_reset: int = 2,
) -> dict[str, object]:
    """Return subscription-efficiency metrics for dashboard rendering."""
    windows_per_day = 24 / reset_hours if reset_hours > 0 else 0
    reset_windows = round(days * windows_per_day)
    target_sessions = max(1, reset_windows * max(1, target_sessions_per_reset))
    prorated_budget = monthly_usd * (days / 30) if days else 0
    active_days = len(report.active_days)
    sessions = report.total_sessions
    messages = report.total_messages
    total_tokens = report.total_tokens

    return {
        "agent": report.name,
        "days": days,
        "monthly_usd": monthly_usd,
        "reset_hours": reset_hours,
        "reset_windows": reset_windows,
        "target_sessions": target_sessions,
        "sessions": sessions,
        "messages": messages,
        "input_tokens": report.total_input_tokens,
        "output_tokens": report.total_output_tokens,
        "cached_tokens": report.total_cached_tokens,
        "total_tokens": total_tokens,
        "active_days": active_days,
        "active_day_percent": round(min(100, (active_days / days * 100) if days else 0), 1),
        "session_utilization_percent": round(min(100, sessions / target_sessions * 100), 1),
        "prorated_budget_usd": round(prorated_budget, 2),
        "cost_per_session_usd": round((prorated_budget / sessions), 2) if sessions else None,
        "cost_per_message_usd": round((prorated_budget / messages), 3) if messages else None,
        "official_limit_status": report.official_limit_status,
        "last_limit_event": report.last_limit_event,
        "reset_at": report.reset_at,
        "remaining_until_reset": report.remaining_until_reset,
    }


def usage_recommendation(agent_name: str, summary: dict[str, object]) -> str:
    """Compact operational guidance for underuse, balance, and limit interruptions."""
    utilization = float(summary.get("session_utilization_percent") or 0)
    active_days = float(summary.get("active_day_percent") or 0)
    is_codex = agent_name.lower().startswith("codex")

    if utilization < 35 or active_days < 50:
        status = "UNDERUSED"
        if is_codex:
            action = (
                "Assign unreviewed diffs, failing test analysis, and Daily Plus / documentation "
                "verification to consume spare quota before the next reset window."
            )
            if utilization < 50:
                action += " Low-risk backlog recommended: doc updates, minor refactors, test coverage."
        else:
            action = (
                "Assign implementation, refactors, and testing in each reset window before quota expires. "
                "Quota headroom: prioritise low-risk backlog items."
            )
    elif utilization > 85:
        status = "LIMIT-RISK"
        if is_codex:
            action = (
                "Save current review state as a handoff note; pause Codex until the next reset window; "
                "queue pending diffs for the next cycle."
            )
        else:
            action = (
                "Save handoff notes now; switch to Codex for review, reproduction, handoff compilation, "
                "and task decomposition until the next reset window."
            )
    else:
        status = "BALANCED"
        if is_codex:
            action = (
                "Continue code review, diff analysis, and test verification; "
                "preserve handoff state before context limits."
            )
        else:
            action = (
                "Continue implementation and long coding sessions; "
                "save handoff notes before heavy context growth."
            )

    return (
        f"{status}: {action} "
        f"Fallback: create a handoff, queue the blocked task, and switch lanes until the next reset window."
    )


def window_distribution(
    event_times: list[datetime],
    reset_hours: float,
    now: datetime,
    lookback_windows: int = 8,
) -> list[dict]:
    """Bucket events into the past `lookback_windows` reset windows (oldest first).

    Each window: {start, end, count, is_current}. The current window is the most
    recent (ends at `now`).
    """
    if reset_hours <= 0:
        reset_hours = 5
    span = timedelta(hours=reset_hours)
    windows: list[dict] = []
    for i in range(lookback_windows):
        end = now - span * i
        start = end - span
        count = sum(1 for t in event_times if t and start <= t < end)
        windows.append({"start": start, "end": end, "count": count, "is_current": i == 0})
    windows.reverse()  # oldest -> newest for left-to-right charting
    return windows


def _model_family(name: str) -> str:
    n = (name or "").lower()
    for fam in ("opus", "sonnet", "haiku"):
        if fam in n:
            return fam
    return "기타"


def efficiency_signals(
    claude: AgentReport,
    codex: AgentReport,
    cli_state: dict[str, object] | None,
    reset_hours: float,
    now: datetime,
    lookback_windows: int = 8,
) -> dict[str, object]:
    """Compute the four real efficiency signals + per-agent status.

    Signals: model_mix, agent_balance, limit_frequency, idle_warning.
    Status (per agent + global): LIMIT-RISK | IDLE | BALANCED.
    """
    cli_state = cli_state or {}
    models = cli_state.get("models") or {}

    # --- model_mix ---
    fam_calls = {"haiku": 0, "sonnet": 0, "opus": 0, "기타": 0}
    if isinstance(models, dict):
        for mname, stats in models.items():
            if isinstance(stats, dict):
                fam_calls[_model_family(mname)] += int(stats.get("calls", 0) or 0)
    total_calls = sum(fam_calls.values())
    model_mix = {
        "counts": fam_calls,
        "total": total_calls,
        "percent": {
            k: (round(v / total_calls * 100, 1) if total_calls else 0.0)
            for k, v in fam_calls.items()
        },
    }

    # --- limit_frequency (mapped to reset windows) ---
    limit_times = cli_state.get("limit_event_times") or []
    if not isinstance(limit_times, list):
        limit_times = []
    limit_windows = window_distribution(limit_times, reset_hours, now, lookback_windows)
    recent_limit = limit_windows[-1]["count"]
    if len(limit_windows) >= 2:
        recent_limit += limit_windows[-2]["count"]
    limit_frequency = {
        "windows": limit_windows,
        "total": int(cli_state.get("limit_events", 0) or 0),
        "recent": recent_limit,
        "latest": cli_state.get("latest_limit_event"),
    }

    # --- agent_balance ---
    c_sess, x_sess = claude.total_sessions, codex.total_sessions
    if c_sess and x_sess:
        ratio = c_sess / x_sess
        heavier = claude.name if ratio >= 1 else codex.name
        mult = ratio if ratio >= 1 else 1 / ratio
    else:
        heavier = claude.name if c_sess >= x_sess else codex.name
        mult = 0.0
    agent_balance = {
        "claude_sessions": c_sess,
        "codex_sessions": x_sess,
        "claude_messages": claude.total_messages,
        "codex_messages": codex.total_messages,
        "heavier": heavier,
        "multiple": round(mult, 1),
    }

    # --- per-agent window load + idle + status ---
    per_agent: dict[str, dict] = {}
    for report, is_claude in ((claude, True), (codex, False)):
        win = window_distribution(report.event_times, reset_hours, now, lookback_windows)
        loads = [w["count"] for w in win]
        current = loads[-1] if loads else 0
        peak = max(loads) if loads else 0
        idle = peak > 0 and current < max(1, peak * 0.3)
        if is_claude and recent_limit > 0:
            status = "LIMIT-RISK"
        elif idle:
            status = "IDLE"
        else:
            status = "BALANCED"
        per_agent[report.name] = {
            "status": status,
            "windows": win,
            "current_load": current,
            "peak_load": peak,
            "idle": idle,
        }

    idle_warning = all(per_agent[r.name]["idle"] for r in (claude, codex))
    if recent_limit > 0:
        gstatus = "LIMIT-RISK"
    elif idle_warning:
        gstatus = "IDLE"
    else:
        gstatus = "BALANCED"

    return {
        "model_mix": model_mix,
        "limit_frequency": limit_frequency,
        "agent_balance": agent_balance,
        "per_agent": per_agent,
        "status": gstatus,
        "idle_warning": idle_warning,
    }


def resolve_quota(
    cli_state: dict[str, object] | None,
    reset_hours: float,
    now: datetime,
    override_path: Path | str | None = None,
) -> dict[str, dict]:
    """Merge auto-estimated and manual quota per agent.

    Auto: latest Claude limit event + reset_hours -> reset_at (label 'estimated').
    Manual: data/ai_usage_quota.json overrides auto (label 'manual').
    Neither: all None (caller renders '미수집').
    """
    agents = ["Claude Code", "Codex"]
    out: dict[str, dict] = {
        a: {
            "limit_status": None,
            "reset_at": None,
            "remaining_until_reset": None,
            "source": None,
        }
        for a in agents
    }

    # auto estimate — only Claude limit events are tracked in the CLI log
    latest = (cli_state or {}).get("latest_limit_event")
    if isinstance(latest, dict) and latest.get("timestamp"):
        ts = _parse_ts(latest.get("timestamp"))
        if ts:
            reset_at = ts + timedelta(hours=reset_hours)
            out["Claude Code"].update(
                {
                    "limit_status": latest.get("detail") or "최근 한도 이벤트 기준 추정",
                    "reset_at": reset_at.isoformat(),
                    "remaining_until_reset": _humanize_delta(reset_at - now),
                    "source": "estimated",
                }
            )

    # manual override
    path = Path(override_path) if override_path else QUOTA_OVERRIDE_PATH
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            data = {}
        if isinstance(data, dict):
            for a in agents:
                entry = data.get(a)
                if not isinstance(entry, dict):
                    continue
                reset_at = entry.get("reset_at")
                limit_status = entry.get("limit_status")
                if reset_at:
                    out[a]["reset_at"] = reset_at
                    rt = _parse_ts(reset_at)
                    out[a]["remaining_until_reset"] = (
                        _humanize_delta(rt - now) if rt else None
                    )
                if limit_status:
                    out[a]["limit_status"] = limit_status
                if reset_at or limit_status:
                    out[a]["source"] = "manual"

    return out


def render_report(reports: list[AgentReport], days: int) -> str:
    lines = []
    lines.append(f"# Subscription ROI Report — last {days} days")
    lines.append(f"_Generated: {datetime.now(KST).strftime('%Y-%m-%d %H:%M KST')}_")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append("| Agent | Sessions | Active Days | Messages | Input Tokens | Output Tokens | Cached |")
    lines.append("|-------|---------:|------------:|---------:|-------------:|--------------:|-------:|")
    for r in reports:
        lines.append(
            f"| {r.name} | {format_int(r.total_sessions)} | {len(r.active_days)}/{days} | "
            f"{format_int(r.total_messages)} | {format_int(r.total_input_tokens)} | "
            f"{format_int(r.total_output_tokens)} | {format_int(r.total_cached_tokens)} |"
        )

    lines.append("")
    lines.append("## ROI Analysis")
    lines.append("")
    lines.append(f"- 구독 비용: ${SUB_COST_MONTHLY}/월 × 2 = **${SUB_COST_MONTHLY * 2}/월**")
    lines.append(f"- 측정 기간: {days}일")
    lines.append("")
    for r in reports:
        active_ratio = (len(r.active_days) / days * 100) if days else 0
        avg_sess = (r.total_sessions / days) if days else 0
        # prorated cost for measurement window
        prorated = SUB_COST_MONTHLY * (days / 30)
        cost_per_session = (prorated / r.total_sessions) if r.total_sessions else float("inf")
        cost_per_message = (prorated / r.total_messages) if r.total_messages else float("inf")
        lines.append(f"### {r.name}")
        lines.append(f"- 가동률: **{active_ratio:.1f}%** ({len(r.active_days)}/{days}일)")
        lines.append(f"- 일평균 세션: **{avg_sess:.1f}회**")
        lines.append(f"- 세션당 비용: ${cost_per_session:.2f}" if r.total_sessions else "- 세션당 비용: N/A")
        lines.append(f"- 메시지당 비용: ${cost_per_message:.3f}" if r.total_messages else "- 메시지당 비용: N/A")
        if r.total_tokens:
            lines.append(f"- 총 토큰: {format_int(r.total_tokens)}")
        lines.append("")

    # asymmetry analysis
    if len(reports) == 2:
        a, b = reports
        if a.total_sessions and b.total_sessions:
            ratio = a.total_sessions / b.total_sessions
            heavier = a.name if ratio > 1 else b.name
            mult = ratio if ratio > 1 else 1 / ratio
            lines.append("## 비대칭 분석")
            lines.append("")
            lines.append(f"- **{heavier}**가 다른 쪽보다 **{mult:.1f}배** 더 활발")
            if mult > 3:
                lines.append(f"- ⚠️ 비대칭이 심함 — 적게 쓰는 쪽 구독 재검토 가치 있음")
            elif mult > 1.5:
                lines.append(f"- 보통 수준 비대칭. 정상 범위")
            else:
                lines.append(f"- ✅ 균형 잡힌 사용 패턴")
            lines.append("")

    lines.append("## Daily Breakdown")
    lines.append("")
    all_days = set()
    for r in reports:
        all_days |= set(r.by_day.keys())
    sorted_days = sorted(d for d in all_days if d != "unknown")
    if sorted_days:
        header = "| Date | " + " | ".join(r.name for r in reports) + " |"
        sep = "|------|" + "|".join(["---:"] * len(reports)) + "|"
        lines.append(header)
        lines.append(sep)
        for d in sorted_days:
            row = [d]
            for r in reports:
                s = r.by_day.get(d, DailyStats())
                row.append(f"{s.sessions}s/{s.messages}m")
            lines.append("| " + " | ".join(row) + " |")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description="Codex + Claude Code 구독 ROI 측정")
    ap.add_argument("--days", type=int, default=7, help="측정 기간 (일) [default: 7]")
    ap.add_argument("--save", action="store_true", help="Vault에 리포트 저장")
    ap.add_argument("--project", type=str, default=None, help="Claude Code 프로젝트 필터")
    args = ap.parse_args()

    since = datetime.now(KST) - timedelta(days=args.days)
    print(f"[i] 측정 시작 — since {since.strftime('%Y-%m-%d')} ({args.days}일)", file=sys.stderr)

    codex = collect_codex(since, args.project)
    print(f"[i] Codex 수집 완료: {codex.total_sessions} sessions", file=sys.stderr)

    claude = collect_claude(since, args.project)
    print(f"[i] Claude Code 수집 완료: {claude.total_sessions} sessions", file=sys.stderr)

    report = render_report([claude, codex], args.days)
    print(report)

    if args.save:
        VAULT_REPORTS.mkdir(parents=True, exist_ok=True)
        out = VAULT_REPORTS / f"roi-{datetime.now(KST).strftime('%Y%m%d-%H%M')}.md"
        out.write_text(report, encoding="utf-8")
        print(f"\n[✓] 리포트 저장: {out}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
