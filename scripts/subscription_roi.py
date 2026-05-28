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
import io
import json
import os
import sys

# Force UTF-8 stdout on Windows (cp949 default breaks unicode dashes/emojis)
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

KST = timezone(timedelta(hours=9))
USER_HOME = Path(os.environ.get("USERPROFILE", os.path.expanduser("~")))
CODEX_SESSIONS = USER_HOME / ".codex" / "sessions"
CLAUDE_PROJECTS = USER_HOME / ".claude" / "projects"
VAULT_REPORTS = Path("G:/내 드라이브/obsidian-agent-brain-system/ObsidianVault/00_System/roi-reports")

SUB_COST_MONTHLY = 100  # USD per service


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

    @property
    def total_tokens(self) -> int:
        return self.total_input_tokens + self.total_output_tokens

    def add_session(self, day: str, messages: int, in_tok: int, out_tok: int, cached: int) -> None:
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


def parse_codex_file(path: Path) -> tuple[str, int, int, int, int]:
    """Return (day_iso, msg_count, in_tok, out_tok, cached_tok)."""
    msg_count = 0
    in_tok = out_tok = cached_tok = 0
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
                # token usage often in token_count or usage payload
                usage = payload.get("usage") or payload.get("token_usage") or {}
                if isinstance(usage, dict):
                    in_tok += int(usage.get("input_tokens") or usage.get("prompt_tokens") or 0)
                    out_tok += int(usage.get("output_tokens") or usage.get("completion_tokens") or 0)
                    cached_tok += int(usage.get("cached_input_tokens") or usage.get("cache_read_tokens") or 0)
    except OSError:
        pass

    return day_iso, msg_count, in_tok, out_tok, cached_tok


def parse_claude_file(path: Path) -> tuple[str, int, int, int, int]:
    """Return (day_iso, msg_count, in_tok, out_tok, cached_tok). Day taken from mtime."""
    msg_count = 0
    in_tok = out_tok = cached_tok = 0
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
                msg = rec.get("message") or {}
                usage = msg.get("usage") if isinstance(msg, dict) else None
                if isinstance(usage, dict):
                    in_tok += int(usage.get("input_tokens") or 0)
                    out_tok += int(usage.get("output_tokens") or 0)
                    cached_tok += int(usage.get("cache_read_input_tokens") or 0)
    except OSError:
        pass

    return day_iso, msg_count, in_tok, out_tok, cached_tok


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
        day, msgs, in_t, out_t, cached = parse_codex_file(jsonl)
        rep.add_session(day, msgs, in_t, out_t, cached)
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
            day, msgs, in_t, out_t, cached = parse_claude_file(jsonl)
            rep.add_session(day, msgs, in_t, out_t, cached)
    return rep


def format_int(n: int) -> str:
    return f"{n:,}"


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
