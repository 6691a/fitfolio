import re
from datetime import datetime
from enum import StrEnum

from app.config.settings import settings
from app.schemas.documents import DocumentKind, EmploymentType, ParsedDocument, Region
from app.schemas.profiles import JobPostingProfileData, ProfileData, ResumeProfileData
from app.utils import parse_datetime_to_utc, resolve_timezone_name

# 근무지 상세주소 접두사 → region 대분류(자치도 풀네임 별칭 포함).
_REGION_PREFIXES: dict[Region, tuple[str, ...]] = {
    Region.SEOUL: ("서울",),
    Region.BUSAN: ("부산",),
    Region.DAEGU: ("대구",),
    Region.INCHEON: ("인천",),
    Region.GWANGJU: ("광주",),
    Region.DAEJEON: ("대전",),
    Region.ULSAN: ("울산",),
    Region.SEJONG: ("세종",),
    Region.GYEONGGI: ("경기",),
    Region.GANGWON: ("강원",),
    Region.CHUNGBUK: ("충북", "충청북도"),
    Region.CHUNGNAM: ("충남", "충청남도"),
    Region.JEONBUK: ("전북", "전라북도"),
    Region.JEONNAM: ("전남", "전라남도"),
    Region.GYEONGBUK: ("경북", "경상북도"),
    Region.GYEONGNAM: ("경남", "경상남도"),
    Region.JEJU: ("제주",),
}


def region_from_location(location: str | None) -> Region | None:
    """상세 주소에서 시/도 대분류(Region)를 추론한다(AI region이 없을 때 폴백).

    Args:
        location: 근무지 상세 주소(없으면 None).

    Returns:
        매칭되는 Region, 추론 불가면 None.
    """
    if not location:
        return None
    for region, prefixes in _REGION_PREFIXES.items():
        if any(prefix in location for prefix in prefixes):
            return region
    return None


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
        document_text = parsed.metadata.get("document_text")
        if not isinstance(document_text, str) or not document_text:
            document_text = parsed.extracted_text
        image_text = parsed.metadata.get("image_text")
        image_text = image_text if isinstance(image_text, str) else ""
        return ResumeProfileData(
            document_text=document_text,
            image_text=image_text,
            title=_structured_value(structured, "title"),
            name=_structured_value(structured, "name"),
            email=_structured_value(structured, "email"),
            phone=_structured_value(structured, "phone"),
            self_introduction=_structured_value(structured, "self_introduction"),
            career_summary=_structured_value(structured, "career_summary"),
            work_experiences=_structured_list(structured, "work_experiences"),
            projects=_structured_list(structured, "projects"),
            skills=_structured_list(structured, "skills"),
            education=_structured_list(structured, "education"),
            certifications=_structured_list(structured, "certifications"),
            links=_structured_list(structured, "links"),
            etc=_structured_list(structured, "etc"),
            raw_sections=raw_sections,
        )

    if kind == DocumentKind.JOB_POSTING:
        structured = parsed.metadata.get("job_posting_extract")
        raw_sections = {"job_posting_extract": structured} if isinstance(structured, dict) else {}
        document_text = parsed.metadata.get("document_text")
        if not isinstance(document_text, str) or not document_text:
            document_text = _job_posting_raw_text(parsed.extracted_text, structured)
        image_text = parsed.metadata.get("image_text")
        image_text = image_text if isinstance(image_text, str) else ""
        fallback_text = _job_posting_fallback_text(document_text, image_text, structured)
        return JobPostingProfileData(
            document_text=document_text,
            image_text=image_text,
            company_name=_structured_value(structured, "company_name") or _fallback_company_name(fallback_text),
            # title은 AI가 이미지+본문 텍스트만 보고 뽑은 값만 사용한다(page title/heading/position fallback 미사용).
            title=_structured_value(structured, "title"),
            location=_structured_value(structured, "work_location"),
            region=_structured_enum(structured, "region", Region)
            or region_from_location(_structured_value(structured, "work_location")),
            employment_type=_structured_enum(structured, "employment_type", EmploymentType),
            career_requirement=_structured_value(structured, "career_requirement"),
            education_requirement=_structured_value(structured, "education_requirement"),
            start_date=_structured_datetime_utc(
                structured,
                "start_date",
                fallback_keys=("opening_starts_at", "application_start_date"),
            ),
            end_date=_structured_datetime_utc(
                structured,
                "end_date",
                fallback_keys=("opening_ends_at", "application_end_date"),
                allow_permanent=True,
            ),
            responsibilities=_structured_list(structured, "responsibilities"),
            qualifications=_structured_list(structured, "qualifications"),
            preferred_qualifications=_structured_list(structured, "preferred_qualifications"),
            benefits=_structured_list(structured, "benefits"),
            source_url=parsed.metadata.get("source_url"),
            raw_sections=raw_sections,
        )

    raise UnsupportedProfileTypeError(f"Unsupported document type: {document_type}")


def build_job_posting_search_text(profile: JobPostingProfileData) -> str:
    """채용공고 프로필을 의미 검색용 임베딩 입력 텍스트로 합성한다.

    Args:
        profile: 임베딩할 채용공고 프로필 데이터.

    Returns:
        주요 필드를 라벨과 함께 이어 붙인 검색 텍스트(비어 있는 값은 제외).
    """
    scalars = [
        ("회사명", profile.company_name),
        ("직무", profile.title),
        ("근무지", profile.location),
        ("고용형태", profile.employment_type),
        ("경력요건", profile.career_requirement),
        ("학력요건", profile.education_requirement),
    ]
    lists = [
        ("주요업무", profile.responsibilities),
        ("자격요건", profile.qualifications),
        ("우대사항", profile.preferred_qualifications),
        ("혜택", profile.benefits),
    ]
    parts = [f"{label}: {value}" for label, value in scalars if value]
    parts += [f"{label}: {', '.join(items)}" for label, items in lists if items]
    return "\n".join(parts)


def _job_posting_raw_text(raw_text: str, structured: object) -> str:
    """DB에 저장할 채용공고 원문 텍스트를 반환한다.

    Args:
        raw_text: 채용공고 원문 텍스트.
        structured: 구조화 추출 결과(dict면 DTO의 text를 우선 사용).

    Returns:
        DTO가 반환한 text 또는 원문 텍스트. JSON 래퍼나 구조화 JSON은 포함하지 않는다.
    """
    if isinstance(structured, dict):
        value = structured.get("text")
        if isinstance(value, str) and value:
            return value

    return raw_text


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


def _structured_enum[E: StrEnum](structured: object, key: str, enum_cls: type[E]) -> E | None:
    """구조화 결과의 문자열 필드를 enum 멤버로 안전하게 변환한다.

    Args:
        structured: 구조화 추출 결과(dict가 아니면 None 반환).
        key: 꺼낼 필드 이름.
        enum_cls: 변환할 StrEnum 클래스.

    Returns:
        값이 enum 멤버면 해당 멤버, 아니면 None.
    """
    value = _structured_value(structured, key)
    if value is None:
        return None
    try:
        return enum_cls(value)
    except ValueError:
        return None


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


def _structured_datetime_utc(
    structured: object,
    key: str,
    *,
    fallback_keys: tuple[str, ...] = (),
    allow_permanent: bool = False,
) -> datetime | None:
    """구조화 결과의 일시 값을 UTC aware datetime으로 변환한다.

    Args:
        structured: 구조화 추출 결과(dict가 아니면 None 반환).
        key: 우선 조회할 필드 이름.
        fallback_keys: key 값이 없을 때 순서대로 조회할 기존 필드 이름들.
        allow_permanent: 상시/채용시/수시 표기를 9999년 종료일로 변환할지 여부.

    Returns:
        UTC timezone이 붙은 datetime 또는 None.
    """
    if not isinstance(structured, dict):
        return None

    value = structured.get(key)
    for fallback_key in fallback_keys:
        value = value or structured.get(fallback_key)
    return parse_datetime_to_utc(
        value,
        default_timezone=_structured_timezone(structured),
        allow_permanent=allow_permanent,
    )


def _structured_timezone(structured: dict) -> str:
    """AI가 추론한 timezone을 우선 사용하고, 없거나 invalid면 설정 fallback을 쓴다."""
    return resolve_timezone_name(
        _structured_value(structured, "timezone"),
        fallback=settings.JOB_POSTING_DEFAULT_TIMEZONE,
    )


def _job_posting_fallback_text(document_text: str, image_text: str, structured: object) -> str:
    """AI가 비운 필드를 보강할 때 쓸 채용공고 텍스트(본문 + 이미지 OCR)를 만든다.

    Args:
        document_text: 문서/페이지 본문 텍스트.
        image_text: 이미지 OCR 텍스트.
        structured: 구조화 추출 결과(dict면 title/position/company_name도 추가).

    Returns:
        규칙 기반 회사명/제목 추출에 쓸 결합 텍스트.
    """
    parts = [document_text, image_text]
    if isinstance(structured, dict):
        for key in ("title", "position", "company_name"):
            value = structured.get(key)
            if isinstance(value, str) and value:
                parts.append(value)
    return "\n".join(part for part in parts if part)


def _fallback_company_name(text: str) -> str | None:
    """이미지 OCR 본문에서 법인 suffix가 붙은 회사명을 보수적으로 찾는다."""
    match = _company_match(text)
    if match is None:
        return None
    return _drop_leading_latin_brand(match.group("company"))


def _company_match(text: str) -> re.Match[str] | None:
    suffix = r"\(주\)|㈜|주식회사|유한회사|Inc\.?|Corp\.?|Co\.,?\s*Ltd\.?"
    return re.search(rf"(?P<company>(?:[A-Za-z0-9&.+-]+\s+)?[가-힣A-Za-z0-9&.+-]{{1,40}}(?:{suffix}))", text)


def _drop_leading_latin_brand(value: str) -> str:
    """'mindsground 마인즈그라운드(주)'처럼 영문 브랜드가 앞에 붙으면 한글 회사명만 남긴다."""
    normalized = re.sub(r"\s+", " ", value).strip()
    tokens = normalized.split()
    for index, token in enumerate(tokens):
        if re.search(r"[가-힣]", token):
            return " ".join(tokens[index:])
    return normalized
