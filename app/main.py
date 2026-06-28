from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.config.containers import Container
from app.config.settings import settings
from app.controllers import documents
from app.services.document import (
    DocumentFileParseError,
    FileTooLargeError,
    InsufficientJobContentError,
    UnsupportedDocumentFormatError,
)

# 서비스가 던지는 도메인 예외 → HTTP 상태 매핑. 컨트롤러/서비스는 HTTPException을 직접 만들지 않는다.
_DOMAIN_EXCEPTION_STATUS: dict[type[Exception], int] = {
    UnsupportedDocumentFormatError: status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
    FileTooLargeError: status.HTTP_413_CONTENT_TOO_LARGE,
    DocumentFileParseError: status.HTTP_422_UNPROCESSABLE_ENTITY,
    InsufficientJobContentError: status.HTTP_422_UNPROCESSABLE_ENTITY,
}


def _register_exception_handlers(app: FastAPI) -> None:
    """도메인 예외를 일관된 HTTP 응답으로 변환하는 전역 핸들러를 등록한다.

    Args:
        app: 핸들러를 등록할 FastAPI 애플리케이션.
    """

    async def handle_domain_error(request: Request, exc: Exception) -> JSONResponse:
        """등록된 도메인 예외를 매핑된 상태코드의 JSON 응답으로 바꾼다.

        Args:
            request: 현재 요청(미사용).
            exc: 발생한 도메인 예외.

        Returns:
            `{"detail": ...}` 형태의 JSONResponse.
        """
        return JSONResponse(status_code=_DOMAIN_EXCEPTION_STATUS[type(exc)], content={"detail": str(exc)})

    for exc_type in _DOMAIN_EXCEPTION_STATUS:
        app.add_exception_handler(exc_type, handle_domain_error)


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
container.wire(modules=[documents])

app = FastAPI(title="Fitfolio", lifespan=lifespan)
# pyrefly: ignore [missing-attribute]
app.container = container
_register_exception_handlers(app)
app.include_router(documents.router)
