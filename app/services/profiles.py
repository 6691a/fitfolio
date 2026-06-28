import json

from app.schemas.documents import DocumentKind, ParsedDocument
from app.schemas.profiles import JobPostingProfileData, ProfileData, ResumeProfileData


class UnsupportedProfileTypeError(Exception):
    pass


def build_profile_data(document_type: DocumentKind, parsed: ParsedDocument) -> ProfileData:
    """파싱 결과를 문서 종류에 맞는 프로필 데이터로 변환한다.

    Args:
        document_type: 문서 종류(이력서/채용공고).
        parsed: 추출 텍스트와 메타데이터가 담긴 파싱 결과.

    Returns:
        이력서면 ResumeProfileData, 채용공고면 JobPostingProfileData.

    Raises:
        UnsupportedProfileTypeError: 지원하지 않는 문서 종류일 때.
    """
    kind = DocumentKind(document_type)
    if kind == DocumentKind.RESUME:
        structured = parsed.metadata.get("resume_extract")
        raw_sections = {"resume_extract": structured} if isinstance(structured, dict) else {}
        return ResumeProfileData(
            raw_text=_resume_ai_text(parsed.extracted_text, structured),
            self_introduction=_structured_value(structured, "self_introduction"),
            career_summary=_structured_value(structured, "career_summary"),
            work_experiences=_structured_list(structured, "work_experiences"),
            projects=_structured_list(structured, "projects"),
            skills=_structured_list(structured, "skills"),
            education=_structured_list(structured, "education"),
            certifications=_structured_list(structured, "certifications"),
            raw_sections=raw_sections,
        )

    if kind == DocumentKind.JOB_POSTING:
        structured = parsed.metadata.get("job_posting_extract")
        raw_sections = {"job_posting_extract": structured} if isinstance(structured, dict) else {}
        return JobPostingProfileData(
            raw_text=_job_posting_ai_text(parsed.extracted_text, structured),
            title=_structured_value(structured, "title") or _structured_value(structured, "position"),
            location=_structured_value(structured, "work_location"),
            opening_period=_structured_value(structured, "application_start_date"),
            deadline=_structured_value(structured, "application_end_date"),
            source_url=parsed.metadata.get("source_url"),
            raw_sections=raw_sections,
        )

    raise UnsupportedProfileTypeError(f"Unsupported document type: {document_type}")


def _job_posting_ai_text(raw_text: str, structured: object) -> str:
    """채용공고 구조화 JSON과 원문을 합쳐 AI 입력용 텍스트를 만든다.

    Args:
        raw_text: 채용공고 원문 텍스트.
        structured: 구조화 추출 결과(dict가 아니면 원문만 사용).

    Returns:
        구조화 JSON과 본문을 결합한 텍스트(구조화가 없으면 원문 그대로).
    """
    if not isinstance(structured, dict):
        return raw_text

    structured_json = json.dumps(structured, ensure_ascii=False, indent=2)
    return f"구조화된 채용공고 JSON\n{structured_json}\n\n채용공고 본문\n{raw_text}"


def _resume_ai_text(raw_text: str, structured: object) -> str:
    """이력서 구조화 JSON과 원문을 합쳐 AI 입력용 텍스트를 만든다.

    Args:
        raw_text: 이력서 원문 텍스트.
        structured: 구조화 추출 결과(dict가 아니면 원문만 사용).

    Returns:
        구조화 JSON과 본문을 결합한 텍스트(구조화가 없으면 원문 그대로).
    """
    if not isinstance(structured, dict):
        return raw_text

    structured_json = json.dumps(structured, ensure_ascii=False, indent=2)
    return f"구조화된 이력서 JSON\n{structured_json}\n\n이력서 본문\n{raw_text}"


def _structured_value(structured: object, key: str) -> str | None:
    """구조화 결과에서 비어 있지 않은 문자열 필드를 안전하게 꺼낸다.

    Args:
        structured: 구조화 추출 결과(dict가 아니면 None 반환).
        key: 꺼낼 필드 이름.

    Returns:
        값이 비어 있지 않은 문자열이면 그 값, 아니면 None.
    """
    if not isinstance(structured, dict):
        return None

    value = structured.get(key)
    return value if isinstance(value, str) and value else None


def _structured_list(structured: object, key: str) -> list:
    """구조화 결과에서 리스트 필드를 안전하게 꺼낸다.

    Args:
        structured: 구조화 추출 결과(dict가 아니면 빈 리스트 반환).
        key: 꺼낼 필드 이름.

    Returns:
        값이 리스트면 그 리스트, 아니면 빈 리스트.
    """
    if not isinstance(structured, dict):
        return []

    value = structured.get(key)
    return value if isinstance(value, list) else []
