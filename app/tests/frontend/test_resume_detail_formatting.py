from streamlit_app.views.resumes import _format_resume_entry


def test_format_resume_entry_turns_work_experience_dict_into_readable_lines():
    title, lines = _format_resume_entry(
        {
            "company": "Xpace",
            "period": "2024.06 - 현재",
            "role": "Backend Engineer",
            "achievements": ["API 응답 시간 개선", "채용공고 파서 구축"],
        },
        fallback_title="경력",
    )

    assert title == "Xpace · Backend Engineer"
    assert "기간: 2024.06 - 현재" in lines
    assert "성과: API 응답 시간 개선, 채용공고 파서 구축" in lines
    assert not any("{" in line or "company" in line for line in lines)


def test_format_resume_entry_keeps_plain_string_entries_simple():
    title, lines = _format_resume_entry("FastAPI 기반 채용공고 크롤러 개선", fallback_title="프로젝트")

    assert title == "FastAPI 기반 채용공고 크롤러 개선"
    assert lines == []


def test_format_resume_entry_hides_internal_employment_type():
    title, lines = _format_resume_entry(
        {
            "company": "Xpace",
            "role": "Backend Engineer",
            "employment_type": "정규직",
            "achievements": ["API 응답 시간 개선"],
        },
        fallback_title="경력",
    )

    assert title == "Xpace · Backend Engineer"
    assert not any("employment_type" in line or "정규직" in line for line in lines)
