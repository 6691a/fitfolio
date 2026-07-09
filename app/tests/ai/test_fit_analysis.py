from datetime import date
from types import SimpleNamespace

from app.ai.analysis import (
    filter_matched_skills,
    format_experience,
    job_posting_fit_input,
    select_best_position,
    total_experience_months,
)


def test_total_experience_months_sums_ranges_including_ongoing():
    # 실제 이력서(문서 43) 경력: 재직중 항목을 포함해 합산해야 한다.
    work = [
        {"company": "Xpace", "period": "2024.06 - 재직중 (1년 11개월)"},
        {"company": "에임(AIM)", "period": "2024.04 - 2024.05 (2개월)"},
        {"company": "(주) 얼리페이", "period": "2022.12 - 2024.01 (1년 2개월)"},
        {"company": "스프링클라우드", "period": "2021.09 - 2022.12 (1년 4개월)"},
    ]
    # Xpace 2024.06~2026.07 = 26, 에임 2, 얼리페이 14, 스프링 16 → 58개월.
    assert total_experience_months(work, today=date(2026, 7, 1)) == 58


def test_total_experience_months_deterministic_regardless_of_call():
    work = [{"period": "2024.06 - 재직중"}]
    first = total_experience_months(work, today=date(2026, 7, 1))
    second = total_experience_months(work, today=date(2026, 7, 1))
    assert first == second == 26


def test_total_experience_months_returns_none_when_unparseable():
    assert total_experience_months([{"company": "회사"}, "설명만 있음"]) is None
    assert total_experience_months([]) is None


def test_format_experience():
    assert format_experience(58) == "4년 10개월"
    assert format_experience(24) == "2년"
    assert format_experience(5) == "5개월"


def test_filter_matched_skills_drops_hallucinated_and_keeps_casefold_match():
    kept = filter_matched_skills(
        ["python", "FastAPI", "Kubernetes"],
        ["Python", "fastapi", "Django"],
    )

    assert kept == ["python", "FastAPI"]


def test_filter_matched_skills_handles_empty_inputs():
    assert filter_matched_skills([], ["Python"]) == []
    assert filter_matched_skills(["Python"], []) == []


def test_select_best_position_picks_highest_skill_overlap():
    positions = [
        {"title": "HR 담당자", "tech_tags": ["MS Office"], "qualifications": ["엑셀 활용"]},
        {"title": "백엔드 개발자", "tech_tags": ["Python", "Django"], "qualifications": ["REST API 설계"]},
        {"title": "임베디드", "tech_tags": ["C++"], "qualifications": ["펌웨어"]},
    ]
    best = select_best_position(positions, ["Python", "Django", "AWS"])
    assert best is not None
    assert best["title"] == "백엔드 개발자"


def test_select_best_position_none_when_no_positions():
    assert select_best_position([], ["Python"]) is None


def test_select_best_position_ties_prefer_first():
    # 겹치는 기술이 전혀 없으면 동점(0) → 공고에 먼저 나온 포지션.
    positions = [{"title": "A", "tech_tags": ["Go"]}, {"title": "B", "tech_tags": ["Rust"]}]
    best = select_best_position(positions, ["Python"])
    assert best is not None
    assert best["title"] == "A"


def test_job_posting_fit_input_scopes_to_selected_position():
    profile = SimpleNamespace(
        company_name="회사",
        title="통합 채용",
        career_requirement="경력 2년 이상",
        education_requirement="전문학사 이상",
        responsibilities=["백엔드 개발", "HR 행정", "C++ 펌웨어"],
        qualifications=["Python", "MS Office", "C++"],
        preferred_qualifications=["Docker", "노무 지식"],
    )
    position = {
        "title": "백엔드 개발자",
        "responsibilities": ["백엔드 개발"],
        "qualifications": ["Python", "Django"],
        "preferred_qualifications": ["Docker"],
    }
    result = job_posting_fit_input(profile, position=position)  # pyrefly: ignore [bad-argument-type]
    assert result["title"] == "백엔드 개발자"
    assert result["qualifications"] == ["Python", "Django"]
    assert result["responsibilities"] == ["백엔드 개발"]
    # 포지션에 없는 경력 요건은 공고 전체 값으로 폴백.
    assert result["career_requirement"] == "경력 2년 이상"
