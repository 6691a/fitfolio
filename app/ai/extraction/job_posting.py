import logging

from app.ai.extraction.errors import StructuredExtractionError
from app.ai.extraction.langchain import structured_output
from app.config.settings import settings
from app.schemas.documents import JobPostingExtractDebug

logger = logging.getLogger(__name__)


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

    result = await structured_output(
        JobPostingExtractDebug,
        "다음 텍스트가 채용공고인지 확인하고 JobPostingExtractDebug JSON으로 정리하라.",
        text,
        fallback.model_dump(mode="json", exclude_none=True),
    )
    if isinstance(result, JobPostingExtractDebug):
        logger.info(
            "AI 구조화 판단: kind=job_posting source=%s relevant=%s title_present=%s images=%d failure_reason=%s",
            result.source,
            result.relevant,
            bool(result.title or result.position),
            len(result.image_urls),
            result.failure_reason or "",
        )
        return result

    logger.info("AI 구조화 판단: kind=job_posting invalid_result=true")
    return fallback
