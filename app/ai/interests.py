from collections import defaultdict
from datetime import date
from typing import Any

from pydantic import BaseModel

from app.ai.analysis import total_experience_months

# 최근 분석일수록 큰 가중치를 주는 감쇠 계수(0=최근). w = _DECAY ** rank.
_DECAY = 0.9
# 관심 직군/기술/보유 기술 각각 노출할 상위 항목 수.
_TOP_K = 8


class UserProfileData(BaseModel):
    """최근 분석 이력에서 집계한 사용자 요약 프로필(물질화 뷰 재료).

    interest_domains/interest_tech는 분석한 공고의 정규화 태그, own_skills는 이력서 보유 기술,
    experience_months는 가장 최근 이력서의 총 경력이다. 같은 입력이면 같은 결과(멱등).
    """

    interest_domains: list[str] = []
    interest_tech: list[str] = []
    own_skills: list[str] = []
    experience_months: int | None = None


def _weighted_top(counts: dict[str, float], display: dict[str, str], top_k: int) -> list[str]:
    """가중 빈도(casefold 키) dict를 값 내림차순 정렬해 상위 top_k의 표시 표기를 돌려준다."""
    ranked = sorted(counts.items(), key=lambda kv: kv[1], reverse=True)
    return [display[key] for key, _ in ranked[:top_k]]


def _accumulate(counts: dict[str, float], display: dict[str, str], value: Any, weight: float) -> None:
    """토큰 하나를 casefold 키로 가중 집계하고 첫 등장(가장 최근) 표기를 표시값으로 보관한다."""
    token = str(value).strip()
    if not token:
        return
    key = token.casefold()
    counts[key] += weight
    display.setdefault(key, token)


def aggregate_user_profile(
    recent: list[tuple[Any, Any]],
    *,
    decay: float = _DECAY,
    top_k: int = _TOP_K,
    today: date | None = None,
) -> UserProfileData:
    """최근 분석한 (채용공고, 이력서) 목록에서 사용자 요약 프로필을 최근 가중 빈도로 집계한다.

    최근순 입력에서 i번째(0=가장 최근) 항목에 decay**i 가중치를 준다. 이 최근성 감쇠가
    시간이 지나며 관심사가 바뀌게 하는 핵심이다. 관심 직군/기술은 공고의 정규화 태그(domain,
    tech_tags)를 쓰되, 태그가 없는(구버전) 공고는 title로 폴백한다. experience_months는
    가장 최근 이력서의 경력에서 결정적으로 계산한다.

    Args:
        recent: 분석 최신순 (채용공고 프로필, 이력서 프로필 또는 None) 튜플 목록.
        decay: 순위당 가중치 감쇠 계수(0<decay<=1). 1이면 감쇠 없음.
        top_k: 각 태그 목록의 상위 노출 개수.
        today: 재직중 항목 경력 계산 기준일(테스트 결정성용). None이면 오늘.

    Returns:
        집계된 UserProfileData.
    """
    domain_counts: dict[str, float] = defaultdict(float)
    domain_display: dict[str, str] = {}
    tech_counts: dict[str, float] = defaultdict(float)
    tech_display: dict[str, str] = {}
    skill_counts: dict[str, float] = defaultdict(float)
    skill_display: dict[str, str] = {}
    experience_months: int | None = None

    for rank, (job_posting, resume) in enumerate(recent):
        weight = decay**rank

        # 정규화 domain 우선, 없으면 title로 폴백(구버전 공고 호환).
        domain = (getattr(job_posting, "domain", None) or getattr(job_posting, "title", None) or "").strip()
        if domain:
            _accumulate(domain_counts, domain_display, domain, weight)
        for tag in getattr(job_posting, "tech_tags", None) or []:
            _accumulate(tech_counts, tech_display, tag, weight)

        if resume is None:
            continue
        for skill in getattr(resume, "skills", None) or []:
            _accumulate(skill_counts, skill_display, skill, weight)
        # 가장 최근(rank가 가장 작은) 이력서의 경력을 채택한다.
        if experience_months is None:
            experience_months = total_experience_months(getattr(resume, "work_experiences", None) or [], today=today)

    return UserProfileData(
        interest_domains=_weighted_top(domain_counts, domain_display, top_k),
        interest_tech=_weighted_top(tech_counts, tech_display, top_k),
        own_skills=_weighted_top(skill_counts, skill_display, top_k),
        experience_months=experience_months,
    )


def demo() -> None:
    """aggregate_user_profile의 최근 가중치·태그 폴백·빈 입력 분기를 assert로 자체 검증한다."""

    class _Job:
        def __init__(self, domain=None, tech_tags=(), title=None):
            self.domain = domain
            self.tech_tags = list(tech_tags)
            self.title = title

    class _Resume:
        def __init__(self, skills=(), work_experiences=()):
            self.skills = list(skills)
            self.work_experiences = list(work_experiences)

    # 빈 입력 → 빈 결과.
    empty = aggregate_user_profile([])
    assert empty.interest_domains == [] and empty.interest_tech == []
    assert empty.own_skills == [] and empty.experience_months is None

    recent = [
        (_Job(domain="백엔드", tech_tags=["Python", "AWS"]), _Resume(skills=["Python"])),
        (_Job(domain="백엔드", tech_tags=["Python"]), _Resume(skills=["Python", "SQL"])),
        (_Job(domain="데이터", tech_tags=["SQL"]), _Resume(skills=["SQL"])),
    ]
    result = aggregate_user_profile(recent)
    assert result.interest_domains[0] == "백엔드", result.interest_domains
    assert "데이터" in result.interest_domains
    assert result.interest_tech[0] == "Python", result.interest_tech
    assert result.own_skills[0] == "Python", result.own_skills

    # domain이 없으면 title로 폴백.
    fallback = aggregate_user_profile([(_Job(title="서버 개발자"), None)])
    assert fallback.interest_domains == ["서버 개발자"], fallback.interest_domains

    # casefold 병합: python/Python은 한 항목.
    merged = aggregate_user_profile([(_Job(tech_tags=["Python", "python"]), None)])
    assert merged.interest_tech == ["Python"], merged.interest_tech

    # 최근성: 가장 최근 1건(A)이 오래된 반복(B 2건)을 이긴다(decay 작게).
    weighted = aggregate_user_profile(
        [(_Job(domain="A"), None), (_Job(domain="B"), None), (_Job(domain="B"), None)],
        decay=0.3,
    )
    assert weighted.interest_domains[0] == "A", weighted.interest_domains

    # experience_months는 가장 최근 이력서 기준.
    exp = aggregate_user_profile(
        [(_Job(domain="백엔드"), _Resume(work_experiences=[{"period": "2022.01 ~ 2024.01"}]))],
        today=date(2026, 7, 1),
    )
    assert exp.experience_months == 25, exp.experience_months

    print("ok")


if __name__ == "__main__":
    demo()
