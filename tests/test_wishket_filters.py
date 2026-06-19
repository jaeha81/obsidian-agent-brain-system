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


def test_rejects_career_level_based_hiring():
    # "경력 무관", "년 이상", "주 2회", "재택 근무", "출근" are employment signals
    assert is_employment_post("주니어 개발자 구합니다", "경력 무관 신입 지원 가능")
    assert is_employment_post("개발팀 확장", "3년 이상 경력자 우대 주 2회 출근")
    assert is_employment_post("파트타임 채용", "재택 근무 가능")


def test_rejects_role_title_based_hiring():
    # "엔지니어", "프로덕트 매니저", "pmo", "pm (" are job title hiring signals
    assert is_employment_post("시니어 엔지니어 채용", "백엔드 팀")
    assert is_employment_post("프로덕트 매니저 구합니다", "스타트업")
    assert is_employment_post("프로젝트 관리", "PMO 역할 수행")
    assert is_employment_post("팀장 구합니다", "PM (경력 5년 이상)")


def test_rejects_english_engineer_job_title():
    # "engineer", "forward deployed engineer", "fde" are English role-title signals
    assert is_employment_post("We are hiring", "forward deployed engineer position")
    assert is_employment_post("FDE 채용", "실리콘밸리 스타일 엔지니어")
    assert not is_collectable_development_request("FDE 채용", "영업 엔지니어 상주")


def test_rejects_hardware_design_roles():
    # "외장 디자인", "기구 설계" are hardware/industrial design, not dev outsourcing
    assert is_employment_post("제품 담당자 구인", "외장 디자인 및 기구 설계 경력자")
    assert not is_collectable_development_request("외장 디자인 파트너", "기구 설계 경력 5년")
