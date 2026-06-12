#!/usr/bin/env python3
"""
키워드 기반 에이전트 자동 라우팅 레이어 v2.

Discord 봇 + Agent Dispatcher 양쪽에서 import하여 사용.
기존 라우팅 유지 원칙: 이 모듈의 결과는 힌트(hint)이며
기존 task_type / force_agent 결정을 override하지 않는다.

에이전트 역할:
  gemini     — 리서치, 최신 정보, 멀티모달 (GEMINI_API_KEY 필요)
  chris      — Graphify 기반 지식 구조 분석, 브레인 성능 개선 제안
  codex      — 2번 구현자: 백엔드·스크립트·API·테스트·자동화·DB·버그수정·리팩토링
  claude     — 1번 구현자: 프론트엔드·UI·복잡한 멀티파일·아키텍처 결정·전략
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

# Codex: 2번 구현자 — 백엔드·스크립트·API·테스트·자동화·DB·버그수정·리팩토링
_CODEX_KEYWORDS: tuple[str, ...] = (
    # 백엔드 / 서버
    "백엔드", "backend", "서버", "server", "api", "endpoint", "라우터", "router",
    # 스크립트 / 자동화
    "스크립트", "script", "자동화", "automation", "배치", "batch", "크론", "cron",
    "파이썬", "python", "shell", "셸",
    # 데이터베이스
    "데이터베이스", "database", "db", "쿼리", "query", "마이그레이션", "migration", "seed",
    # 테스트
    "테스트", "test", "pytest", "unittest", "테스트 작성", "단위테스트", "unit test",
    # 버그 / 디버깅 / 리팩토링
    "버그", "bug", "오류", "error", "디버깅", "debug", "리팩토링", "refactor",
    "버그수정", "fix", "수정해",
    # 데이터 처리
    "데이터 처리", "data processing", "파싱", "parsing", "크롤링", "crawl",
    # 검수 (명시적 요청만)
    "검수", "코드 리뷰", "code review",
)

# Claude Code: 1번 구현자 — 프론트엔드·UI·복잡한 멀티파일·아키텍처 결정·전략
_CLAUDE_CODE_KEYWORDS: tuple[str, ...] = (
    # 프론트엔드 / UI
    "프론트엔드", "frontend", "html", "css", "javascript", "js", "react", "vue",
    "ui", "ux", "디자인", "레이아웃", "layout", "컴포넌트", "component",
    "페이지", "page", "대시보드", "dashboard", "차트", "chart",
    # 복잡한 구현
    "구현", "만들어", "개발해", "implement", "create", "build", "추가해",
    # 아키텍처 / 전략
    "아키텍처", "architecture", "설계", "시스템", "system design", "전략", "strategy",
    "복잡한", "complex", "전체적", "overall",
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
