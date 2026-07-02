#!/usr/bin/env python3
"""
Bucky Multi-Task Dispatcher — 다중 지시 파싱 + 병렬 실행

Discord 메시지에 여러 태스크가 포함된 경우(체크박스, 번호 목록, 불릿 등)
각 태스크를 독립 채널 컨텍스트로 분리해 asyncio.gather()로 병렬 실행합니다.
"""

from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Awaitable


# ── 다중 태스크 패턴 ────────────────────────────────────────────────────────────

# 체크박스: [ ] / [x] / [  ] 등
_CHECKBOX_RE = re.compile(r"^\s*\[[ xX✓]?\]\s+(.+)$", re.MULTILINE)

# 번호 목록: 1. / 1) / 1단계
_NUMBERED_RE = re.compile(r"^\s*(\d+)[.)단계:]\s+(.+)$", re.MULTILINE)

# 불릿: • / - / * (최소 2항)
_BULLET_RE = re.compile(r"^\s*[•\-\*]\s+(.+)$", re.MULTILINE)

# 병렬/다중 트리거 키워드
_PARALLEL_KEYWORDS = re.compile(
    r"(병렬|분업|동시에|단계별로|각각|순서대로|멀티|parallel|서브에이전트)",
    re.IGNORECASE,
)

# 에이전트 배분 prefix 감지 — "단계 N — " / "Step N:"
_STEP_HEADER_RE = re.compile(r"^\s*(?:단계|Step|stage)\s*\d+\s*[-—:]\s*", re.IGNORECASE | re.MULTILINE)


@dataclass
class ParsedTask:
    index: int
    label: str      # "1단계", "태스크 2" 등
    body: str       # 실제 지시문


def parse_multi_tasks(text: str) -> list[ParsedTask]:
    """
    메시지 텍스트에서 다중 태스크를 추출한다.
    단일 태스크이면 빈 리스트 반환 → 기존 단일 처리 경로 사용.
    """
    tasks: list[ParsedTask] = []

    # 1순위: 체크박스
    checkboxes = _CHECKBOX_RE.findall(text)
    if len(checkboxes) >= 2:
        for i, body in enumerate(checkboxes):
            tasks.append(ParsedTask(i + 1, f"태스크 {i + 1}", body.strip()))
        return tasks

    # 2순위: 번호 목록
    numbered = _NUMBERED_RE.findall(text)
    if len(numbered) >= 2:
        for num, body in numbered:
            tasks.append(ParsedTask(int(num), f"{num}단계", body.strip()))
        return tasks

    # 3순위: 불릿 (트리거 키워드 있을 때만 — 일반 불릿은 단일 메시지로 처리)
    if _PARALLEL_KEYWORDS.search(text):
        bullets = _BULLET_RE.findall(text)
        if len(bullets) >= 2:
            for i, body in enumerate(bullets):
                tasks.append(ParsedTask(i + 1, f"태스크 {i + 1}", body.strip()))
            return tasks

    return []


def is_multi_task(text: str) -> bool:
    """다중 태스크 메시지인지 빠르게 판별."""
    return len(parse_multi_tasks(text)) >= 2


# ── 병렬 실행 ───────────────────────────────────────────────────────────────────

AskFn = Callable[[str, str], Awaitable[str]]


async def _run_single(
    ask_fn: AskFn,
    base_channel_id: str,
    task: ParsedTask,
    timeout: float = 300.0,
) -> tuple[ParsedTask, str]:
    """단일 태스크를 독립 채널 컨텍스트로 실행. (task, reply) 반환."""
    isolated_channel = f"{base_channel_id}_multi_{task.index}"
    try:
        reply = await asyncio.wait_for(ask_fn(isolated_channel, task.body), timeout=timeout)
    except asyncio.TimeoutError:
        reply = f"⏱️ 타임아웃 ({timeout}초 초과)"
    except Exception as e:
        reply = f"❌ 실행 오류: {e}"
    return task, reply


async def run_parallel(
    ask_fn: AskFn,
    base_channel_id: str,
    tasks: list[ParsedTask],
    notify_start: Callable[[str], Awaitable[None]] | None = None,
    notify_done: Callable[[str, str], Awaitable[None]] | None = None,
    timeout: float = 300.0,
) -> list[tuple[ParsedTask, str]]:
    """
    여러 태스크를 asyncio.gather()로 병렬 실행한다.

    Parameters
    ----------
    ask_fn : async (channel_id, message) -> str
        discord_bot.ask_bucky와 동일 시그니처
    base_channel_id : str
        원본 Discord 채널 ID (각 태스크는 _multi_N suffix로 격리)
    tasks : list[ParsedTask]
        parse_multi_tasks()로 추출한 태스크 목록
    notify_start : optional async (label) -> None
        각 태스크 시작 시 호출 (Discord "작업 시작" 메시지 등)
    notify_done : optional async (label, reply) -> None
        각 태스크 완료 시 호출 (결과를 즉시 Discord로 전송)
    timeout : float
        태스크당 최대 대기 시간(초)

    Returns
    -------
    list of (ParsedTask, reply_str) in original order
    """
    if notify_start:
        for t in tasks:
            await notify_start(t.label)

    coros = [
        _run_single(ask_fn, base_channel_id, t, timeout)
        for t in tasks
    ]
    results: list[tuple[ParsedTask, str]] = await asyncio.gather(*coros)

    if notify_done:
        for task, reply in results:
            await notify_done(task.label, reply)

    return list(results)


def format_multi_result(results: list[tuple[ParsedTask, str]]) -> str:
    """병렬 실행 결과를 Discord용 통합 메시지로 포맷."""
    ts = datetime.now().strftime("%H:%M")
    lines = [f"**⚡ 병렬 작업 완료 ({len(results)}개, {ts})**\n"]
    for task, reply in results:
        lines.append(f"**[{task.label}]** {task.body[:60]}{'...' if len(task.body) > 60 else ''}")
        # 답변이 길면 요약 (2000자 Discord 제한 고려)
        reply_preview = reply[:400].strip()
        if len(reply) > 400:
            reply_preview += "\n…(이하 생략)"
        lines.append(reply_preview)
        lines.append("")
    return "\n".join(lines)
