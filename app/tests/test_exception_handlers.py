import pytest
from fastapi import FastAPI, status
from fastapi.testclient import TestClient

from app.main import _register_exception_handlers
from app.services.document import (
    DocumentFileParseError,
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
