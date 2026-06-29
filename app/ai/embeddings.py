import logging
from typing import Protocol

from langchain_google_genai import GoogleGenerativeAIEmbeddings

from app.config.settings import settings

logger = logging.getLogger(__name__)

EMBEDDING_DIM = settings.EMBEDDING_DIM


class EmbeddingSettings(Protocol):
    GEMINI_API_KEY: str
    EMBEDDING_MODEL: str
    EMBEDDING_DIM: int
    EMBEDDING_DOCUMENT_TASK_TYPE: str
    EMBEDDING_QUERY_TASK_TYPE: str


class GeminiEmbeddingService:
    def __init__(self, config: EmbeddingSettings = settings) -> None:
        """Gemini 임베딩 설정을 주입받아 보관한다.

        Args:
            config: 임베딩 모델/차원/task type/API key 설정 객체.
        """
        self._settings = config

    async def embed_document(self, text: str) -> list[float] | None:
        """저장용 문서 텍스트를 임베딩 벡터로 변환한다.

        Args:
            text: 임베딩할 채용공고 검색 텍스트.

        Returns:
            설정된 차원의 임베딩 벡터. 테스트 키이거나 비어 있거나 실패하면 None.
        """
        return await self._embed(text, task_type=self._settings.EMBEDDING_DOCUMENT_TASK_TYPE)

    async def embed_query(self, text: str) -> list[float] | None:
        """검색 질의 텍스트를 임베딩 벡터로 변환한다.

        Args:
            text: 임베딩할 검색어.

        Returns:
            설정된 차원의 임베딩 벡터. 테스트 키이거나 비어 있거나 실패하면 None.
        """
        return await self._embed(text, task_type=self._settings.EMBEDDING_QUERY_TASK_TYPE)

    async def _embed(self, text: str, *, task_type: str) -> list[float] | None:
        """Gemini 임베딩을 호출해 벡터를 받아온다(fail-soft)."""
        if self._settings.GEMINI_API_KEY == "test-key":
            return None
        clean = text.strip()
        if not clean:
            return None
        try:
            embeddings = GoogleGenerativeAIEmbeddings(
                model=self._settings.EMBEDDING_MODEL,
                google_api_key=self._settings.GEMINI_API_KEY,
                task_type=task_type,
                output_dimensionality=self._settings.EMBEDDING_DIM,
            )
            return await embeddings.aembed_query(clean)
        except Exception as exc:
            logger.warning("임베딩 실패: model=%s error=%s", self._settings.EMBEDDING_MODEL, exc)
            return None


_default_service = GeminiEmbeddingService()


async def embed_document(text: str) -> list[float] | None:
    """기본 GeminiEmbeddingService로 저장용 문서 텍스트를 임베딩한다.

    Args:
        text: 임베딩할 채용공고 검색 텍스트.

    Returns:
        설정된 차원의 임베딩 벡터. 테스트 키이거나 비어 있거나 실패하면 None.
    """
    return await _default_service.embed_document(text)


async def embed_query(text: str) -> list[float] | None:
    """기본 GeminiEmbeddingService로 검색 질의 텍스트를 임베딩한다.

    Args:
        text: 임베딩할 검색어.

    Returns:
        설정된 차원의 임베딩 벡터. 테스트 키이거나 비어 있거나 실패하면 None.
    """
    return await _default_service.embed_query(text)
