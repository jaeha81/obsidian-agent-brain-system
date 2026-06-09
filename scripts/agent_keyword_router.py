#!/usr/bin/env python3
"""
키워드 기반 에이전트 자동 라우팅 레이어 v1.

Discord 봇 + Agent Dispatcher 양쪽에서 import하여 사용.
기존 라우팅 유지 원칙: 이 모듈의 결과는 힌트(hint)이며
기존 task_type / force_agent 결정을 override하지 않는다.

에이전트 역할:
  gemini     — 리서치, 최신 정보, 멀티모달 (GEMINI_API_KEY 필요)
  chris      — Graphify 기반 지식 구조 분석, 브레인 성능 개선 제안
  codex      — 설계 검토, 버그 분석, 리뷰, 리팩토링
  claude     — 구현, 코드 작성, 수정 (Claude Code CLI)
  bucky      — 일반 대화, 분류 불가 폴백
"""

import os

# ── 키워드 테이블 ──────────────────────────────────────────────────────────────

# Gemini: 리서치, 최신 정보, 멀티모달 (URL·영상·PDF·이미지 포함)
_GEMINI_KEYWORDS: tuple[str, ...] = (
    "리서치", "조사해", "조사하", "최신", "최근",
    "영상", "유튜브", "youtube", "pdf",
    "이미지 분석", "코드베이스 분석",
    "research", "video transcript", "image analysis",
    "트렌드", "뉴스", "동향",
)

# Codex: 설계 검토, 버그 분석, 코드 리뷰, 리팩토링
_CODEX_KEYWORDS: tuple[str, ...] = (
    "설계", "아키텍처", "오류", "버그", "디버깅", "리팩토링",
    "검토", "리뷰", "위험",
    "architecture", "debug", "error", "refactor", "review", "risk",
    "code review", "코드 리뷰", "검수",
)

# Claude Code: 구현, 코드 작성, 수정
_CLAUDE_CODE_KEYWORDS: tuple[str, ...] = (
    "구현", "만들어", "수정", "코드 써", "작성해",
    "implement", "create", "build", "write code", "modify",
    "추가해", "개발해",
)

# Chris: Graphify 전담 지식 지도 에이전트
_CHRIS_KEYWORDS: tuple[str, ...] = (
    "chris", "크리스", "graphify", "그래피파이", "그래프파이", "그래프",
    "지식 그래프", "knowledge graph", "지식 구조", "지식 정리",
    "브레인 성능", "brain performance", "연결성", "고립 노드",
    "isolated node", "context pack 후보", "컨텍스트팩 후보",
    "지식 갭", "knowledge gap",
)

# ── 상수 ───────────────────────────────────────────────────────────────────────

_GEMINI_AVAILABLE: bool = bool(os.getenv("GEMINI_API_KEY", "").strip())

AGENT_ICONS: dict[str, str] = {
    "gemini": "🔭",
    "chris": "🧭",
    "codex": "⚡",
    "claude": "🧠",
    "bucky": "🤖",
}


# ── 공개 API ───────────────────────────────────────────────────────────────────

def classify(text: str) -> tuple[str | None, list[str]]:
    """텍스트 키워드 감지 → (agent, matched_keywords).

    Returns:
        agent: "gemini" | "chris" | "codex" | "claude" | None  (키워드 미감지 시 None)
        matched_keywords: 감지된 키워드 목록 (표시용)
    """
    b = text.lower()

    gemini_hits = [k for k in _GEMINI_KEYWORDS if k in b]
    chris_hits = [k for k in _CHRIS_KEYWORDS if k in b]
    codex_hits = [k for k in _CODEX_KEYWORDS if k in b]
    claude_hits = [k for k in _CLAUDE_CODE_KEYWORDS if k in b]

    # 점수 기반 정렬 (동점 시 우선순위: chris > claude > codex > gemini)
    ranked = sorted(
        [
            (len(gemini_hits), 0, "gemini", gemini_hits),
            (len(codex_hits),  1, "codex",  codex_hits),
            (len(claude_hits), 2, "claude", claude_hits),
            (len(chris_hits),  3, "chris",  chris_hits),
        ],
        key=lambda x: (x[0], x[1]),
        reverse=True,
    )

    top_score, _, top_agent, top_hits = ranked[0]
    if top_score == 0:
        return None, []

    # Gemini 불가 → bucky 폴백 (API 키 미설정)
    if top_agent == "gemini" and not _GEMINI_AVAILABLE:
        return "bucky", top_hits

    return top_agent, top_hits


def format_routing_hint(agent: str | None, matched: list[str]) -> str:
    """Discord 표시용 라우팅 힌트 문자열 반환."""
    if not agent or not matched:
        return ""
    icon = AGENT_ICONS.get(agent, "")
    kw_str = " · ".join(f"`{k}`" for k in matched[:3])
    suffix = " _(Gemini API 미설정 → Bucky 폴백)_" if agent == "bucky" else ""
    return f"{icon} **{agent.upper()}** 키워드: {kw_str}{suffix}"


def log_routing(body: str, source: str = "") -> str:
    """라우팅 결과를 로그 문자열로 반환 (agent_dispatcher 용)."""
    agent, hits = classify(body)
    if not agent:
        return ""
    prefix = f"[KeywordRouter{f':{source}' if source else ''}]"
    return f"{prefix} → {agent} | 키워드: {hits[:3]}"
