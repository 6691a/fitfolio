from datetime import date

from app.ai.analysis import filter_matched_skills, format_experience, total_experience_months


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
