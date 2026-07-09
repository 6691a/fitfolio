from app.ai.extraction.errors import StructuredExtractionError
from app.ai.extraction.langchain import structured_output
from app.config.settings import settings
from app.schemas.documents import JobPostingExtractDebug
from app.utils import strip_html_tags


async def extract_job_posting_structured(text: str, fallback: JobPostingExtractDebug) -> JobPostingExtractDebug:
    """채용공고 텍스트를 JobPostingExtractDebug JSON 스키마로 구조화 추출한다.

    Args:
        text: 구조화할 채용공고 원문 텍스트.
        fallback: 추출 실패 시 사용할 보수적 기본 추출 결과.

    Returns:
        구조화된 JobPostingExtractDebug. 결과가 유효하지 않으면 fallback을 반환.

    Raises:
        StructuredExtractionError: 테스트용 키여서 추출이 비활성화된 경우.
    """
    if settings.GEMINI_API_KEY == "test-key":
        raise StructuredExtractionError("structured extraction disabled for test key")

    # AI에는 마크업을 걷어낸 실제 글자만 넘긴다. html/raw는 태그 덩어리라 fallback에서 제외한다.
    clean_text = strip_html_tags(text)
    fallback_payload = fallback.model_dump(mode="json", exclude_none=True, exclude={"html", "raw"})
    if isinstance(fallback_payload.get("text"), str):
        fallback_payload["text"] = strip_html_tags(fallback_payload["text"])

    result = await structured_output(
        JobPostingExtractDebug,
        (
            "다음 텍스트가 채용공고가 맞는지 판단하고, 회사명·직무명·근무지·고용형태·경력요건·"
            "학력요건·주요업무·자격요건·우대사항·혜택/복지를 의미에 맞는 필드로 구분하라. "
            "한국 공고는 '담당 업무 및 자격 요건'처럼 업무와 자격을 한 섹션에 합쳐 적는 경우가 많다. "
            "이때 자격 요건 항목이 실제 수행할 업무를 함께 뜻하면 responsibilities와 qualifications "
            "양쪽에 모두 채워라(필요하면 중복 기재). 업무와 요건이 명확히 구분된 공고만 각각의 필드로 나눠라. "
            "employment_type은 채용 형태 enum(정규직/계약직/인턴/아르바이트/프리랜서/파견직/파트타임/기타) 중 "
            "하나로만 분류하고, 판단 불가/해당 없음이면 기타로 작성하라. "
            "region은 근무지 주소를 보고 시/도 대분류 enum(서울/부산/대구/인천/광주/대전/울산/세종/경기/강원/"
            "충북/충남/전북/전남/경북/경남/제주/기타) 중 하나로 작성하고, 모르면 기타로 작성하라. "
            "채용 시작/종료 일시는 start_date/end_date에 원문 의미가 보존되는 문자열로 작성하라. "
            "공고 언어·사이트·주소·명시된 시간대·통화·국가 단서를 보고 timezone 필드에 "
            "IANA timezone 이름을 추론해 작성하라(예: 한국어/사람인/서울 주소는 Asia/Seoul). "
            "명시적 UTC offset이 있는 ISO 문자열이면 그대로 작성하고 timezone도 가능한 범위에서 채워라. "
            "상시채용/채용시 마감/수시채용이면 end_date='상시채용'으로 작성하라. "
            "domain에는 이 공고의 직군을 정규화한 한 단어(예: 백엔드/프론트엔드/데이터/머신러닝/인프라/DevOps)로 작성하고, "
            "tech_tags에는 요구 기술 스택을 공식 표기로 정규화해 채워라(관심 직군·기술 집계용). 판단 불가면 비워라. "
            "한 공고에 모집부문(직무)이 여러 개면 positions 배열에 각 포지션을 분리해 담아라. 각 포지션의 "
            "업무·자격·기술을 다른 포지션 것과 섞지 말고, 포지션별 domain/tech_tags/responsibilities/qualifications/"
            "preferred_qualifications/career_requirement/education_requirement을 그 포지션 기준으로만 채워라. "
            "모집부문이 하나면 positions에 원소 1개만 넣어라."
        ),
        clean_text,
        fallback_payload,
    )
    if isinstance(result, JobPostingExtractDebug):
        return result

    return fallback
