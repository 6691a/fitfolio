from datetime import date
from types import SimpleNamespace

from app.ai.interests import aggregate_user_profile


def _job(domain=None, tech_tags=(), title=None):
    return SimpleNamespace(domain=domain, tech_tags=list(tech_tags), title=title)


def _resume(skills=(), work_experiences=()):
    return SimpleNamespace(skills=list(skills), work_experiences=list(work_experiences))


def test_aggregate_empty_input_returns_empty():
    result = aggregate_user_profile([])
    assert result.interest_domains == []
    assert result.interest_tech == []
    assert result.own_skills == []
    assert result.experience_months is None


def test_aggregate_ranks_by_recency_weighted_frequency():
    recent = [
        (_job(domain="백엔드", tech_tags=["Python", "AWS"]), _resume(skills=["Python"])),
        (_job(domain="백엔드", tech_tags=["Python"]), _resume(skills=["Python", "SQL"])),
        (_job(domain="데이터", tech_tags=["SQL"]), _resume(skills=["SQL"])),
    ]
    result = aggregate_user_profile(recent)
    assert result.interest_domains[0] == "백엔드"
    assert "데이터" in result.interest_domains
    assert result.interest_tech[0] == "Python"
    assert result.own_skills[0] == "Python"


def test_aggregate_falls_back_to_title_when_domain_missing():
    result = aggregate_user_profile([(_job(title="서버 개발자"), None)])
    assert result.interest_domains == ["서버 개발자"]


def test_aggregate_recency_can_outweigh_older_repeats():
    result = aggregate_user_profile(
        [(_job(domain="A"), None), (_job(domain="B"), None), (_job(domain="B"), None)], decay=0.3
    )
    assert result.interest_domains[0] == "A"


def test_aggregate_merges_casefold_duplicates():
    result = aggregate_user_profile([(_job(tech_tags=["Python", "python"]), None)])
    assert result.interest_tech == ["Python"]


def test_aggregate_uses_most_recent_resume_experience():
    recent = [
        (_job(domain="백엔드"), _resume(work_experiences=[{"period": "2022.01 ~ 2024.01"}])),
        (_job(domain="데이터"), _resume(work_experiences=[{"period": "2010.01 ~ 2011.01"}])),
    ]
    result = aggregate_user_profile(recent, today=date(2026, 7, 1))
    assert result.experience_months == 25
