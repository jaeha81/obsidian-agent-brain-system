"""Wishket project classification filters.

Bucky Wishket Agent only collects outsourced development requests.
Employment/recruiting posts must be rejected before they reach the dashboard.
"""
from __future__ import annotations

from collections.abc import Iterable

EMPLOYMENT_TERMS = (
    "구인", "구합니다", "구해요", "채용", "정규직", "계약직", "파견", "상주",
    "근무지", "직원", "인력", "인재", "프리랜서 모집", "개발자 모집",
    "엔지니어 모집", "채용공고", "잡코리아", "사람인",
    "경력 무관", "년 이상", "고급", "중급", "초급", "주 2회", "재택 근무",
    "출근", "엔지니어", "프로덕트 매니저", "pmo", "pm (",
    "engineer", "forward deployed engineer", "fde", "외장 디자인", "기구 설계",
)

DEV_REQUEST_TERMS = (
    "개발", "구축", "제작", "구현", "연동", "고도화", "자동화", "프로토타입",
    "poc", "mvp", "api", "backend", "frontend", "백엔드", "프론트엔드",
    "웹", "앱", "시스템", "플랫폼", "솔루션", "python", "fastapi", "react",
    "ai", "llm", "agent", "데이터", "크롤링", "챗봇", "에이전트",
)


def _combined_text(title: str, description: str) -> str:
    return f"{title or ''} {description or ''}".casefold()


def is_employment_post(title: str, description: str = "") -> bool:
    """Return True when a Wishket card looks like recruiting or staff hiring."""
    text = _combined_text(title, description)
    return any(term.casefold() in text for term in EMPLOYMENT_TERMS)


def is_development_request(title: str, description: str = "", keywords: Iterable[str] | None = None) -> bool:
    """Return True when a card looks like an outsourced development request."""
    text = _combined_text(title, description)
    terms = tuple(keywords or ()) + DEV_REQUEST_TERMS
    return any(str(term).strip().casefold() in text for term in terms if str(term).strip())


def is_collectable_development_request(title: str, description: str = "", keywords: Iterable[str] | None = None) -> bool:
    """Final collection gate for the Wishket Agent."""
    if is_employment_post(title, description):
        return False
    return is_development_request(title, description, keywords=keywords)


def classify_project(project: dict, keywords: Iterable[str] | None = None) -> dict:
    """Return a lightweight classification record for logs/tests/dashboard defense."""
    title = str(project.get("title") or "")
    description = str(project.get("description") or "")
    if is_employment_post(title, description):
        return {"accepted": False, "reason": "employment_post"}
    if not is_development_request(title, description, keywords=keywords):
        return {"accepted": False, "reason": "not_development_request"}
    return {"accepted": True, "reason": "development_request"}


def filter_collectable_projects(projects: Iterable[dict], keywords: Iterable[str] | None = None) -> list[dict]:
    """Filter a project iterable down to Bucky Wishket Agent's allowed scope."""
    accepted: list[dict] = []
    for project in projects:
        classification = classify_project(project, keywords=keywords)
        if classification["accepted"]:
            item = dict(project)
            item["classification"] = classification["reason"]
            accepted.append(item)
    return accepted
