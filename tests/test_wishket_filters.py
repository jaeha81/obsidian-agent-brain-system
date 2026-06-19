from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from wishket_filters import (  # noqa: E402
    classify_project,
    filter_collectable_projects,
    is_collectable_development_request,
    is_employment_post,
)


def test_rejects_recruiting_posts_even_when_python_matches():
    assert is_employment_post("Python 개발자 채용", "정규직 상주 근무지 서울")
    assert not is_collectable_development_request(
        "Python 개발자 채용",
        "정규직 상주 근무지 서울",
        keywords=["Python", "AI"],
    )


def test_accepts_outsourced_development_request():
    assert is_collectable_development_request(
        "LLM 기반 AI Agent 개발",
        "Python FastAPI API 연동 PoC 구축",
        keywords=["Python", "AI"],
    )


def test_rejects_non_development_notice():
    result = classify_project({"title": "마케팅 운영 대행", "description": "콘텐츠 작성"})
    assert result == {"accepted": False, "reason": "not_development_request"}


def test_filters_project_list_and_marks_classification():
    projects = [
        {"title": "Python 개발자 모집", "description": "계약직 상주"},
        {"title": "FastAPI 백엔드 개발", "description": "API 구축"},
    ]
    assert filter_collectable_projects(projects) == [
        {"title": "FastAPI 백엔드 개발", "description": "API 구축", "classification": "development_request"}
    ]
