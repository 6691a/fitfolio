import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.ai import vision
from app.ai.classification.document import langchain as classifier_langchain
from app.ai.extraction import langchain as extraction_langchain
from app.config.containers import Container
from app.config.settings import settings
from app.controllers import analyses
from app.controllers import auth
from app.controllers import documents
from app.services.errors import (
    AuthConflictError,
    AnalysisNotReadyError,
    DocumentFileParseError,
    FileTooLargeError,
    InsufficientJobContentError,
    InvalidCredentialsError,
    InvalidTokenError,
    ProfileNotReadyError,
    ResumeNotFoundError,
    UnsupportedDocumentFormatError,
)

logger = logging.getLogger(__name__)

# 서비스가 던지는 도메인 예외 → HTTP 상태 매핑. 컨트롤러/서비스는 HTTPException을 직접 만들지 않는다.
_DOMAIN_EXCEPTION_STATUS: dict[type[Exception], int] = {
    UnsupportedDocumentFormatError: status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
    FileTooLargeError: status.HTTP_413_CONTENT_TOO_LARGE,
    DocumentFileParseError: status.HTTP_422_UNPROCESSABLE_ENTITY,
    InsufficientJobContentError: status.HTTP_422_UNPROCESSABLE_ENTITY,
    AuthConflictError: status.HTTP_409_CONFLICT,
    InvalidCredentialsError: status.HTTP_401_UNAUTHORIZED,
    InvalidTokenError: status.HTTP_401_UNAUTHORIZED,
    ProfileNotReadyError: status.HTTP_409_CONFLICT,
    AnalysisNotReadyError: status.HTTP_409_CONFLICT,
    ResumeNotFoundError: status.HTTP_404_NOT_FOUND,
}


def _register_exception_handlers(app: FastAPI) -> None:
    """도메인 예외와 예기치 못한 예외를 일관된 HTTP 응답으로 변환하는 핸들러를 등록한다.

    코딩된(예상 가능한) 실패는 도메인 예외 → 매핑된 4xx/5xx로 응답하고, 그 외 예기치 못한
    예외만 500으로 처리한다. 모든 경로에서 원인을 로깅해 개발자가 인지·수정할 수 있게 한다.

    Args:
        app: 핸들러를 등록할 FastAPI 애플리케이션.
    """

    async def handle_domain_error(request: Request, exc: Exception) -> JSONResponse:
        """등록된 도메인 예외를 매핑된 상태코드의 JSON 응답으로 바꾸고 로깅한다.

        5xx(서버 책임)는 error로, 4xx(클라이언트 입력)는 info로 남겨 노이즈를 분리한다.

        Args:
            request: 현재 요청.
            exc: 발생한 도메인 예외.

        Returns:
            `{"detail": ...}` 형태의 JSONResponse.
        """
        status_code = _DOMAIN_EXCEPTION_STATUS[type(exc)]
        location = f"{request.method} {request.url.path}"
        if status_code >= status.HTTP_500_INTERNAL_SERVER_ERROR:
            logger.error("도메인 예외 %s -> %d: %s", location, status_code, exc)
        else:
            logger.info("도메인 예외 %s -> %d: %s", location, status_code, exc)
        return JSONResponse(status_code=status_code, content={"detail": str(exc)})

    async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        """매핑되지 않은 예기치 못한 예외를 트레이스백과 함께 로깅하고 500으로 응답한다.

        Args:
            request: 현재 요청.
            exc: 발생한 예외.

        Returns:
            일반화된 `{"detail": ...}` 500 JSONResponse.
        """
        logger.exception("처리되지 않은 예외 %s %s", request.method, request.url.path)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "서버 내부 오류가 발생했습니다. 잠시 후 다시 시도해주세요."},
        )

    for exc_type in _DOMAIN_EXCEPTION_STATUS:
        app.add_exception_handler(exc_type, handle_domain_error)
    app.add_exception_handler(Exception, handle_unexpected_error)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """앱 수명주기 동안 디버그 이미지 디렉터리를 준비한다.

    Args:
        app: FastAPI 애플리케이션 인스턴스.

    Yields:
        앱이 요청을 처리하는 동안 제어를 넘긴다(반환값 없음).
    """
    if settings.DOCUMENT_DEBUG_ENABLED:
        (settings.UPLOAD_DIR / settings.DOCUMENT_DEBUG_IMAGE_SUBDIR).mkdir(parents=True, exist_ok=True)
    yield


container = Container()
container.wire(modules=[analyses, auth, documents, classifier_langchain, extraction_langchain, vision])

app = FastAPI(title="Fitfolio", lifespan=lifespan)
# pyrefly: ignore [missing-attribute]
app.container = container
_register_exception_handlers(app)
app.include_router(auth.router)
app.include_router(documents.router)
app.include_router(analyses.router)
