from datetime import UTC, datetime

from app.schemas.documents import DocumentFormat, DocumentKind, ParsedDocument, TextInput, UrlInput
from app.schemas.profiles import JobPostingProfileData, ResumeProfileData
from app.services.profiles import build_profile_data


def test_job_posting_profile_includes_structured_extract_for_ai_input():
    structured = {
        "source": "wanted",
        "detail_url": "https://www.wanted.co.kr/wd/366125",
        "title": "FastAPI 백엔드 엔지니어",
        "position": "다른 포지션 값",
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
    assert profile.document_text == "주요업무\nAPI 개발"
    assert "구조화된 채용공고 JSON" not in profile.document_text
    assert '"position": "FastAPI 백엔드 엔지니어"' not in profile.document_text
    assert profile.title == "FastAPI 백엔드 엔지니어"
    assert profile.location == "서울"
    assert profile.start_date == datetime(2026, 6, 1, 0, 0, tzinfo=UTC)
    assert profile.end_date == datetime(2026, 6, 30, 9, 0, tzinfo=UTC)


def test_job_posting_profile_maps_ai_structured_fields_to_db_columns():
    structured = {
        "source": "text",
        "company_name": "무신사",
        "title": "백엔드 엔지니어",
        "position": "백엔드 엔지니어",
        "text": "채용공고 본문",
        "work_location": "서울 성동구",
        "employment_type": "정규직",
        "career_requirement": "3년 이상",
        "education_requirement": "학력 무관",
        "start_date": "2026-06-01T09:00:00+09:00",
        "end_date": "2026-06-30T18:00:00+09:00",
        "responsibilities": ["주문 API 개발", "서비스 성능 개선"],
        "qualifications": ["Python 실무 경험", "RDBMS 설계 경험"],
        "preferred_qualifications": ["FastAPI 경험"],
        "benefits": ["자율 출퇴근"],
    }
    parsed = ParsedDocument(
        original_input=TextInput(
            document_type=DocumentKind.JOB_POSTING,
            input_type=DocumentFormat.TEXT,
            text="채용공고 본문",
        ),
        extracted_text="채용공고 본문",
        metadata={"job_posting_extract": structured},
    )

    profile = build_profile_data(DocumentKind.JOB_POSTING, parsed)

    assert isinstance(profile, JobPostingProfileData)
    assert profile.company_name == "무신사"
    assert profile.employment_type == "정규직"
    assert profile.career_requirement == "3년 이상"
    assert profile.education_requirement == "학력 무관"
    assert profile.responsibilities == ["주문 API 개발", "서비스 성능 개선"]
    assert profile.qualifications == ["Python 실무 경험", "RDBMS 설계 경험"]
    assert profile.preferred_qualifications == ["FastAPI 경험"]
    assert profile.benefits == ["자율 출퇴근"]
    assert profile.start_date == datetime(2026, 6, 1, 0, 0, tzinfo=UTC)
    assert profile.end_date == datetime(2026, 6, 30, 9, 0, tzinfo=UTC)


def test_job_posting_profile_document_text_prefers_metadata_over_dto_text():
    structured = {
        "source": "text",
        "company_name": "무신사",
        "title": "백엔드 엔지니어",
        "text": "AI가 정리한 채용공고 텍스트",
        "responsibilities": ["API 개발"],
    }
    parsed = ParsedDocument(
        original_input=TextInput(
            document_type=DocumentKind.JOB_POSTING,
            input_type=DocumentFormat.TEXT,
            text="사용자 업로드 원문",
        ),
        extracted_text="사용자 업로드 원문",
        metadata={
            "job_posting_extract": structured,
            "document_text": "문서에서 추출한 본문",
            "image_text": "이미지에서 추출한 본문",
        },
    )

    profile = build_profile_data(DocumentKind.JOB_POSTING, parsed)

    assert isinstance(profile, JobPostingProfileData)
    assert profile.document_text == "문서에서 추출한 본문"
    assert profile.image_text == "이미지에서 추출한 본문"


def test_job_posting_profile_maps_permanent_recruiting_to_year_9999():
    structured = {
        "source": "text",
        "title": "백엔드 엔지니어",
        "text": "채용공고 본문",
        "end_date": "상시채용",
    }
    parsed = ParsedDocument(
        original_input=TextInput(
            document_type=DocumentKind.JOB_POSTING,
            input_type=DocumentFormat.TEXT,
            text="채용공고 본문",
        ),
        extracted_text="채용공고 본문",
        metadata={"job_posting_extract": structured},
    )

    profile = build_profile_data(DocumentKind.JOB_POSTING, parsed)

    assert isinstance(profile, JobPostingProfileData)
    assert profile.end_date == datetime(9999, 12, 31, 23, 59, 59, tzinfo=UTC)


def test_job_posting_profile_falls_back_to_image_text_for_company():
    image_text = "mindsground 마인즈그라운드(주) 백엔드 개발자 채용 Key Point We are Hiring 멋진 동료를 찾습니다"
    structured = {
        "source": "saramin",
        "relevant": True,
        "text": f"채용공고 본문\n\n이미지 추출 텍스트\n{image_text}",
        "work_location": "서울 서초구 남부순환로337가길 71",
        "application_start_date": "2026-05-27 08시",
        "application_end_date": "2026-06-26 24시",
        "start_date": "2026-05-26T23:00:00Z",
        "end_date": "2026-06-26T15:00:00Z",
        "image_urls": [
            {
                "src": "https://example.com/recruit.png",
                "alt": "백엔드개발자_ver.png",
                "text": image_text,
            }
        ],
    }
    parsed = ParsedDocument(
        original_input=TextInput(
            document_type=DocumentKind.JOB_POSTING,
            input_type=DocumentFormat.TEXT,
            text="채용공고 본문",
        ),
        extracted_text="채용공고 본문",
        metadata={"job_posting_extract": structured},
    )

    profile = build_profile_data(DocumentKind.JOB_POSTING, parsed)

    assert isinstance(profile, JobPostingProfileData)
    assert profile.company_name == "마인즈그라운드(주)"
    # title은 structured.title만 사용 — 이미지/본문 텍스트로 추측하지 않으므로 None.
    assert profile.title is None
    assert profile.start_date == datetime(2026, 5, 26, 23, 0, tzinfo=UTC)
    assert profile.end_date == datetime(2026, 6, 26, 15, 0, tzinfo=UTC)


def test_job_posting_profile_converts_korean_hour_dates_to_utc_when_ai_utc_fields_are_missing():
    structured = {
        "source": "saramin",
        "title": "백엔드 개발자 채용",
        "text": "접수기간 : 2026-05-27 08시 ~ 2026-06-26 24시",
        "application_start_date": "2026-05-27 08시",
        "application_end_date": "2026-06-26 24시",
    }
    parsed = ParsedDocument(
        original_input=TextInput(
            document_type=DocumentKind.JOB_POSTING,
            input_type=DocumentFormat.TEXT,
            text="채용공고 본문",
        ),
        extracted_text="채용공고 본문",
        metadata={"job_posting_extract": structured},
    )

    profile = build_profile_data(DocumentKind.JOB_POSTING, parsed)

    assert isinstance(profile, JobPostingProfileData)
    assert profile.start_date == datetime(2026, 5, 26, 23, 0, tzinfo=UTC)
    assert profile.end_date == datetime(2026, 6, 26, 15, 0, tzinfo=UTC)


def test_job_posting_profile_serializes_dates_in_configured_timezone(monkeypatch):
    from app.schemas import profiles as profile_schemas

    monkeypatch.setattr(profile_schemas.settings, "JOB_POSTING_DEFAULT_TIMEZONE", "UTC")
    monkeypatch.setattr(profile_schemas.settings, "TIME_ZONE", "Asia/Seoul")
    profile = JobPostingProfileData(
        document_text="채용공고 본문",
        start_date=datetime(2026, 5, 26, 23, 0, tzinfo=UTC),
        end_date=datetime(2026, 6, 26, 15, 0, tzinfo=UTC),
    )

    db_values = profile.model_dump()
    response_values = profile.model_dump(mode="json")

    assert db_values["start_date"] == datetime(2026, 5, 26, 23, 0, tzinfo=UTC)
    assert db_values["end_date"] == datetime(2026, 6, 26, 15, 0, tzinfo=UTC)
    assert response_values["start_date"] == "2026-05-27T08:00:00+09:00"
    assert response_values["end_date"] == "2026-06-27T00:00:00+09:00"


def test_job_posting_profile_serializes_permanent_end_date_without_timezone_overflow(monkeypatch):
    from app.schemas import profiles as profile_schemas

    monkeypatch.setattr(profile_schemas.settings, "TIME_ZONE", "Asia/Seoul")
    profile = JobPostingProfileData(
        document_text="채용공고 본문",
        end_date=datetime(9999, 12, 31, 23, 59, 59, tzinfo=UTC),
    )

    response_values = profile.model_dump(mode="json")

    assert response_values["end_date"] == "9999-12-31T23:59:59Z"


def test_job_posting_profile_parses_dates_with_job_posting_timezone_not_response_timezone(monkeypatch):
    from app.services import profiles as profile_service

    monkeypatch.setattr(profile_service.settings, "JOB_POSTING_DEFAULT_TIMEZONE", "UTC")
    monkeypatch.setattr(profile_service.settings, "TIME_ZONE", "Asia/Seoul")
    structured = {
        "source": "text",
        "text": "접수기간 : 2026-06-01 09:00",
        "application_start_date": "2026-06-01 09:00",
    }
    parsed = ParsedDocument(
        original_input=TextInput(
            document_type=DocumentKind.JOB_POSTING,
            input_type=DocumentFormat.TEXT,
            text="채용공고 본문",
        ),
        extracted_text="채용공고 본문",
        metadata={"job_posting_extract": structured},
    )

    profile = build_profile_data(DocumentKind.JOB_POSTING, parsed)

    assert isinstance(profile, JobPostingProfileData)
    assert profile.start_date == datetime(2026, 6, 1, 9, 0, tzinfo=UTC)


def test_job_posting_profile_parses_dates_with_ai_inferred_timezone(monkeypatch):
    from app.services import profiles as profile_service

    monkeypatch.setattr(profile_service.settings, "JOB_POSTING_DEFAULT_TIMEZONE", "UTC")
    monkeypatch.setattr(profile_service.settings, "TIME_ZONE", "UTC")
    structured = {
        "source": "text",
        "timezone": "Asia/Seoul",
        "text": "접수기간 : 2026-06-01 09:00",
        "application_start_date": "2026-06-01 09:00",
    }
    parsed = ParsedDocument(
        original_input=TextInput(
            document_type=DocumentKind.JOB_POSTING,
            input_type=DocumentFormat.TEXT,
            text="채용공고 본문",
        ),
        extracted_text="채용공고 본문",
        metadata={"job_posting_extract": structured},
    )

    profile = build_profile_data(DocumentKind.JOB_POSTING, parsed)

    assert isinstance(profile, JobPostingProfileData)
    assert profile.start_date == datetime(2026, 6, 1, 0, 0, tzinfo=UTC)


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
    assert profile.document_text == "이력서 본문"
    assert profile.image_text == ""
    assert profile.name == "홍길동"
    assert profile.email == "hong@example.com"
    assert profile.phone == "010-1234-5678"
    assert profile.skills == ["Python", "FastAPI"]
    assert profile.projects == ["채용 공고 크롤러 개선"]
