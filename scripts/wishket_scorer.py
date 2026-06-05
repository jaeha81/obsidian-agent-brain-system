"""Wishket 공고 자동 점수화 모듈.

각 공고를 예산·키워드 적합도·설명 풍부도·카테고리 기준으로 0~100점 채점.
priority: P1(75+) > P2(50-74) > P3(30-49) > P4(<30)
"""

from __future__ import annotations

import re

# ── JH 전문 스택 키워드 (가중치별) ────────────────────────────────────────
_HIGH = [
    "python", "ai", "인공지능", "자동화", "claude", "gpt", "llm", "chatgpt",
    "에이전트", "agent", "discord", "봇", "bot", "fastapi", "크롤링", "스크래핑",
    "langchain", "rag", "생성형", "수집엔진",
]
_MED = [
    "웹개발", "웹 개발", "데이터", "분석", "api", "백엔드", "챗봇",
    "자동", "노코드", "n8n", "make.com", "zapier", "워크플로우",
    "대시보드", "dashboard", "obsidian", "수집", "파이프라인", "법령", "판례",
]
_LOW = [
    "react", "javascript", "next.js", "typescript", "node.js",
    "서버", "프론트엔드", "frontend",
]

# 인테리어/건축 — 재하님 전문 분야
_INTERIOR = [
    "인테리어", "건축", "설계", "도면", "시공", "리모델링", "인테리어 설계",
    "autocad", "캐드",
]

# 재하님과 맞지 않는 영역 (감점)
_PENALTY = [
    "c++", "임베디드", "하드웨어", "plc", "펌웨어", "fpga",
    "로봇", "드론", "iot 하드웨어", "회로",
]


def _lower(text: str) -> str:
    return (text or "").lower()


def _budget_score(budget_wan: int) -> int:
    """예산 점수 (0~35)."""
    if budget_wan >= 1000:
        return 35
    if budget_wan >= 500:
        return 30
    if budget_wan >= 300:
        return 25
    if budget_wan >= 150:
        return 20
    if budget_wan >= 100:
        return 15
    if budget_wan >= 50:
        return 10
    if budget_wan > 0:
        return 5
    return 8  # 미정 — 협의 가능성 있음


def _keyword_score(combined: str) -> int:
    """키워드 적합도 점수 (0~30)."""
    pts = 0
    for kw in _HIGH:
        if kw in combined:
            pts += 3
    for kw in _MED:
        if kw in combined:
            pts += 2
    for kw in _LOW:
        if kw in combined:
            pts += 1
    return min(pts, 30)


def _category_bonus(combined: str) -> int:
    """카테고리 보너스/패널티 (-10 ~ +25)."""
    for kw in _PENALTY:
        if kw in combined:
            return -10

    ai_match = sum(1 for kw in ["ai", "llm", "claude", "gpt", "에이전트", "생성형", "인공지능"] if kw in combined)
    if ai_match >= 1:
        return 25

    auto_match = sum(1 for kw in ["자동화", "봇", "에이전트", "크롤링", "스크래핑", "수집엔진", "파이프라인"] if kw in combined)
    if auto_match >= 1:
        return 20

    interior_match = sum(1 for kw in _INTERIOR if kw in combined)
    if interior_match >= 1:
        return 18

    web_match = sum(1 for kw in ["웹", "fastapi", "django", "flask"] if kw in combined)
    if web_match >= 1:
        return 12

    return 5


def _desc_score(description: str) -> int:
    """설명 풍부도 점수 (0~10)."""
    n = len(description or "")
    if n >= 150:
        return 10
    if n >= 80:
        return 7
    if n >= 30:
        return 4
    return 0


def score_project(project: dict) -> dict:
    """공고 dict에 score, priority, score_breakdown 필드를 추가해 반환."""
    title = _lower(project.get("title", ""))
    description = _lower(project.get("description", ""))
    budget_wan: int = project.get("budget_wan", 0) or 0
    combined = title + " " + description

    budget_pts = _budget_score(budget_wan)
    keyword_pts = _keyword_score(combined)
    category_pts = _category_bonus(combined)
    desc_pts = _desc_score(project.get("description", ""))

    raw = budget_pts + keyword_pts + category_pts + desc_pts
    score = max(0, min(100, raw))

    if score >= 70:
        priority = "P1"
    elif score >= 50:
        priority = "P2"
    elif score >= 30:
        priority = "P3"
    else:
        priority = "P4"

    return {
        **project,
        "score": score,
        "priority": priority,
        "score_breakdown": {
            "budget": budget_pts,
            "keyword": keyword_pts,
            "category": category_pts,
            "description": desc_pts,
        },
    }


def score_projects(projects: list[dict]) -> list[dict]:
    """프로젝트 목록 전체를 채점 후 점수 내림차순으로 반환."""
    scored = [score_project(p) for p in projects]
    scored.sort(key=lambda p: p["score"], reverse=True)
    return scored


if __name__ == "__main__":
    import json
    from pathlib import Path

    inbox = Path(__file__).parent.parent / "ObsidianVault" / "10_AgentBus" / "wishket_inbox"
    latest = sorted(inbox.glob("*.json"))[-1]
    projects = json.loads(latest.read_text(encoding="utf-8"))
    scored = score_projects(projects)
    for p in scored:
        print(f"[{p['priority']}] {p['score']:3d}점  {p['title'][:40]}  ({p.get('budget_wan', 0)}만원)")
