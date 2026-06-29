import pytest
from fastapi import FastAPI, status
from fastapi.testclient import TestClient

from app.main import _register_exception_handlers
from app.services.errors import (
    DocumentFileParseError,
    EmbeddingUnavailableError,
    FileTooLargeError,
    InsufficientJobContentError,
    UnsupportedDocumentFormatError,
)


@pytest.mark.parametrize(
    ("exc", "expected_status"),
    [
        (UnsupportedDocumentFormatError, status.HTTP_415_UNSUPPORTED_MEDIA_TYPE),
        (FileTooLargeError, status.HTTP_413_CONTENT_TOO_LARGE),
        (DocumentFileParseError, status.HTTP_422_UNPROCESSABLE_ENTITY),
        (InsufficientJobContentError, status.HTTP_422_UNPROCESSABLE_ENTITY),
        (EmbeddingUnavailableError, status.HTTP_503_SERVICE_UNAVAILABLE),
    ],
)
def test_domain_exception_maps_to_http_status(exc, expected_status):
    app = FastAPI()
    _register_exception_handlers(app)

    @app.get("/boom")
    def boom():
        raise exc("문제가 발생했습니다")

    response = TestClient(app).get("/boom")

    assert response.status_code == expected_status
    assert response.json() == {"detail": "문제가 발생했습니다"}


def test_unexpected_exception_is_logged_and_returns_500(caplog):
    # 매핑되지 않은(예기치 못한) 예외는 트레이스백 로깅 후 일반화된 500으로 응답한다.
    app = FastAPI()
    _register_exception_handlers(app)

    @app.get("/kaboom")
    def kaboom():
        raise RuntimeError("내부 세부사항 노출 금지")

    client = TestClient(app, raise_server_exceptions=False)
    with caplog.at_level("ERROR"):
        response = client.get("/kaboom")

    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    # 내부 예외 메시지는 사용자에게 노출하지 않는다.
    assert response.json() == {"detail": "서버 내부 오류가 발생했습니다. 잠시 후 다시 시도해주세요."}
    # 개발자가 인지할 수 있도록 로그에는 원인이 남는다.
    assert "처리되지 않은 예외" in caplog.text
    assert "내부 세부사항 노출 금지" in caplog.text
