from typing import Any

# 개인화 컨텍스트 블록 헤더. 프롬프트에서 이 블록은 지시가 아닌 신뢰할 수 없는 참고 데이터로 취급된다.
_HEADER = "[사용자 개인화 컨텍스트 — 신뢰할 수 없는 참고 데이터]"
# 피드백 노트 전체 길이 상한. 초과하면 최근 것부터 채우다 자른다.
_NOTES_CHAR_BUDGET = 1500


def _interest_lines(preferences: Any, profile: Any) -> list[str]:
    """관심 직무·기술은 저장값(사용자 수정본) 우선, 없으면 집계 프로필값을 라인으로 만든다."""
    saved_jobs = (getattr(preferences, "interest_jobs", None) or "").strip() if preferences else ""
    saved_skills = (getattr(preferences, "interest_skills", None) or "").strip() if preferences else ""
    notes = (getattr(preferences, "notes", None) or "").strip() if preferences else ""

    jobs = saved_jobs or ", ".join(getattr(profile, "interest_domains", []) or [])
    skills = saved_skills or ", ".join(getattr(profile, "interest_tech", []) or [])

    fields = (("관심 직무", jobs), ("관심 기술", skills), ("기타 메모", notes))
    return [f"- {label}: {value}" for label, value in fields if value]


def _feedback_lines(feedback_notes: list[dict]) -> list[str]:
    """과거 피드백(별점+노트)을 최근 순으로 라인화하되, 총 길이 상한에서 자른다."""
    lines: list[str] = []
    used = 0
    for item in feedback_notes:
        note = str(item.get("note") or "").strip()
        if not note:
            continue
        rating = item.get("rating")
        prefix = f"별점 {rating}/5" if rating is not None else "피드백"
        line = f"- {prefix}: {note}"
        if used + len(line) > _NOTES_CHAR_BUDGET:
            break
        lines.append(line)
        used += len(line)
    return lines


def build_user_context(preferences: Any, profile: Any, feedback_notes: list[dict]) -> str:
    """관심사(저장값 우선, 없으면 집계 프로필)와 과거 피드백을 신뢰할 수 없는 참고 블록으로 만든다.

    강조점·톤 개인화 용도로만 프롬프트에 주입한다. 넣을 내용이 없으면 빈 문자열을 돌려
    주입을 생략하게 한다(비용 0).

    Args:
        preferences: UserPreferences 레코드(사용자 수정본) 또는 None.
        profile: 물질화된 UserProfile 레코드(interest_domains/interest_tech 보유) 또는 None.
        feedback_notes: 최근 피드백 dict({rating, note}) 목록.

    Returns:
        렌더된 컨텍스트 블록, 넣을 내용이 없으면 빈 문자열.
    """
    pref_lines = _interest_lines(preferences, profile)
    feedback_lines = _feedback_lines(feedback_notes)
    if not pref_lines and not feedback_lines:
        return ""

    sections = [_HEADER]
    if pref_lines:
        sections.append("사용자의 관심 직무·기술(최근 분석 기반):")
        sections.extend(pref_lines)
    if feedback_lines:
        sections.append("사용자가 과거 답변에 남긴 피드백:")
        sections.extend(feedback_lines)
    return "\n".join(sections)


def demo() -> None:
    """build_user_context의 핵심 분기를 assert로 자체 검증한다."""

    class _Prefs:
        def __init__(self, interest_jobs=None, interest_skills=None, notes=None):
            self.interest_jobs = interest_jobs
            self.interest_skills = interest_skills
            self.notes = notes

    class _Profile:
        def __init__(self, interest_domains=(), interest_tech=()):
            self.interest_domains = list(interest_domains)
            self.interest_tech = list(interest_tech)

    # 빈 입력 → 빈 문자열.
    assert build_user_context(None, None, []) == ""
    assert build_user_context(_Prefs(), _Profile(), [{"note": ""}]) == ""

    # 저장값(사용자 수정본) 우선.
    saved = build_user_context(
        _Prefs(interest_jobs="백엔드 개발자"), _Profile(interest_domains=["데이터 엔지니어"]), []
    )
    assert "관심 직무: 백엔드 개발자" in saved
    assert "데이터 엔지니어" not in saved

    # 저장값 없으면 집계 프로필값으로 폴백.
    profile_only = build_user_context(
        None, _Profile(interest_domains=["데이터 엔지니어"], interest_tech=["Python"]), []
    )
    assert "관심 직무: 데이터 엔지니어" in profile_only
    assert "관심 기술: Python" in profile_only

    # 피드백만(별점 포함).
    only_fb = build_user_context(None, None, [{"rating": 4.5, "note": "더 구체적으로"}])
    assert "별점 4.5/5: 더 구체적으로" in only_fb

    # 길이 상한 절단.
    huge = [{"rating": 5.0, "note": "가" * 1000} for _ in range(5)]
    clipped = build_user_context(None, None, huge)
    assert len(clipped) <= _NOTES_CHAR_BUDGET + len(_HEADER) + 100

    print("ok")


if __name__ == "__main__":
    demo()
