import httpx

from streamlit_app.api import response_error_message
from streamlit_app.views.auth import _validate_login


def test_validate_login_rejects_short_password_before_api_call():
    assert _validate_login("user@example.com", "") == "비밀번호는 8~128자로 입력하세요"


def test_response_error_message_hides_fastapi_validation_payload():
    response = httpx.Response(
        422,
        json={
            "detail": [
                {
                    "type": "string_too_short",
                    "loc": ["body", "password"],
                    "msg": "String should have at least 8 characters",
                    "input": "",
                    "ctx": {"min_length": 8},
                }
            ]
        },
    )

    assert response_error_message(response) == "비밀번호는 8자 이상 입력하세요"
