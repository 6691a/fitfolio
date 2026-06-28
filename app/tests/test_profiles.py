from app.schemas.documents import DocumentFormat, DocumentKind, ParsedDocument, TextInput, UrlInput
from app.schemas.profiles import JobPostingProfileData, ResumeProfileData
from app.services.profiles import build_profile_data


def test_job_posting_profile_includes_structured_extract_for_ai_input():
    structured = {
        "source": "wanted",
        "detail_url": "https://www.wanted.co.kr/wd/366125",
        "position": "FastAPI 백엔드 엔지니어",
        "text": "주요업무\nAPI 개발",
        "work_location": "서울",
        "application_start_date": "2026.06.01 09:00",
        "application_end_date": "2026.06.30 18:00",
        "application_method": "홈페이지 지원",
    }
    parsed = ParsedDocument(
        original_input=UrlInput(
            document_type=DocumentKind.JOB_POSTING,
            input_type=DocumentFormat.URL,
            url="https://www.wanted.co.kr/wd/366125",
        ),
        extracted_text="채용공고 본문",
        metadata={
            "source_url": "https://www.wanted.co.kr/wd/366125",
            "job_posting_extract": structured,
        },
    )

    profile = build_profile_data(DocumentKind.JOB_POSTING, parsed)

    assert isinstance(profile, JobPostingProfileData)
    assert profile.raw_sections["job_posting_extract"] == structured
    assert '"position": "FastAPI 백엔드 엔지니어"' in profile.raw_text
    assert "채용공고 본문" in profile.raw_text
    assert profile.title == "FastAPI 백엔드 엔지니어"
    assert profile.location == "서울"
    assert profile.deadline == "2026.06.30 18:00"


def test_resume_profile_includes_structured_extract_for_ai_input():
    structured = {
        "source": "resume",
        "text": "이력서 본문",
        "name": "홍길동",
        "email": "hong@example.com",
        "phone": "010-1234-5678",
        "skills": ["Python", "FastAPI"],
        "projects": ["채용 공고 크롤러 개선"],
    }
    parsed = ParsedDocument(
        original_input=TextInput(
            document_type=DocumentKind.RESUME,
            input_type=DocumentFormat.TEXT,
            text="이력서 본문",
        ),
        extracted_text="이력서 본문",
        metadata={"resume_extract": structured},
    )

    profile = build_profile_data(DocumentKind.RESUME, parsed)

    assert isinstance(profile, ResumeProfileData)
    assert profile.raw_sections["resume_extract"] == structured
    assert '"email": "hong@example.com"' in profile.raw_text
    assert "이력서 본문" in profile.raw_text
    assert profile.skills == ["Python", "FastAPI"]
    assert profile.projects == ["채용 공고 크롤러 개선"]
