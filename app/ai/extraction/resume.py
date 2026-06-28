import logging

from app.ai.extraction.errors import StructuredExtractionError
from app.ai.extraction.langchain import structured_output
from app.config.settings import settings
from app.schemas.documents import ResumeExtractDebug

logger = logging.getLogger(__name__)


async def extract_resume_structured(text: str, fallback: ResumeExtractDebug) -> ResumeExtractDebug:
    """이력서 텍스트를 ResumeExtractDebug JSON 스키마로 구조화 추출한다.

    Args:
        text: 구조화할 이력서 원문 텍스트.
        fallback: 추출 실패 시 사용할 보수적 기본 추출 결과.

    Returns:
        구조화된 ResumeExtractDebug. 결과가 유효하지 않으면 fallback을 반환.

    Raises:
        StructuredExtractionError: 테스트용 키여서 추출이 비활성화된 경우.
    """
    if settings.GEMINI_API_KEY == "test-key":
        raise StructuredExtractionError("structured extraction disabled for test key")

    result = await structured_output(
        ResumeExtractDebug,
        "다음 텍스트가 이력서/자기소개서/포트폴리오인지 확인하고 ResumeExtractDebug JSON으로 정리하라.",
        text,
        fallback.model_dump(mode="json", exclude_none=True),
    )
    if isinstance(result, ResumeExtractDebug):
        logger.info(
            "AI 구조화 판단: kind=resume relevant=%s name_present=%s skills=%d image_texts=%d failure_reason=%s",
            result.relevant,
            bool(result.name),
            len(result.skills),
            len(result.image_texts),
            result.failure_reason or "",
        )
        return result

    logger.info("AI 구조화 판단: kind=resume invalid_result=true")
    return fallback
