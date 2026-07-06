import base64
import json
from typing import Any

import streamlit as st
import streamlit.components.v1 as components

_AUTH_COOKIE_NAME = "fitfolio_auth"
_AUTH_COOKIE_MAX_AGE_SECONDS = 60 * 60
_DELETE_AUTH_COOKIE_KEY = "_delete_auth_cookie"


def _encode_auth_payload(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), default=str).encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def _decode_auth_payload(value: str | None) -> dict[str, Any] | None:
    if not value:
        return None
    try:
        padding = "=" * (-len(value) % 4)
        payload = json.loads(base64.urlsafe_b64decode(f"{value}{padding}".encode()).decode())
    except (ValueError, TypeError):
        return None
    if (
        isinstance(payload, dict)
        and isinstance(payload.get("access_token"), str)
        and isinstance(payload.get("user"), dict)
    ):
        return payload
    return None


def _set_auth_cookie(payload: dict[str, Any]) -> None:
    value = _encode_auth_payload(payload)
    components.html(
        f"""
        <script>
        document.cookie = "{_AUTH_COOKIE_NAME}={value}; Max-Age={_AUTH_COOKIE_MAX_AGE_SECONDS}; Path=/; SameSite=Lax";
        </script>
        """,
        height=0,
        width=0,
    )


def _delete_auth_cookie() -> None:
    components.html(
        f"""
        <script>
        document.cookie = "{_AUTH_COOKIE_NAME}=; Max-Age=0; Path=/; SameSite=Lax";
        </script>
        """,
        height=0,
        width=0,
    )


def restore_auth_state_from_cookie() -> None:
    """브라우저 새로고침으로 비워진 Streamlit 세션 인증 정보를 쿠키에서 복원한다."""
    if is_authenticated():
        return
    payload = _decode_auth_payload(st.context.cookies.get(_AUTH_COOKIE_NAME))
    if payload is None:
        return
    st.session_state["access_token"] = payload["access_token"]
    st.session_state["user"] = payload["user"]


def sync_auth_cookie() -> None:
    """Streamlit 세션 인증 상태와 브라우저 쿠키를 동기화한다."""
    if st.session_state.pop(_DELETE_AUTH_COOKIE_KEY, False):
        _delete_auth_cookie()
        return
    restore_auth_state_from_cookie()
    if is_authenticated():
        _set_auth_cookie(
            {
                "access_token": st.session_state["access_token"],
                "user": st.session_state["user"],
            }
        )


def auth_headers() -> dict[str, str]:
    """현재 Streamlit 세션의 access token으로 인증 헤더를 만든다.

    Returns:
        로그인 상태면 Authorization 헤더, 아니면 빈 dict.
    """
    token = st.session_state.get("access_token")
    return {"Authorization": f"Bearer {token}"} if token else {}


def is_authenticated() -> bool:
    """현재 Streamlit 세션이 로그인 상태인지 확인한다.

    Returns:
        access token과 사용자 정보가 모두 있으면 True.
    """
    return bool(st.session_state.get("access_token") and st.session_state.get("user"))


def clear_auth_state() -> None:
    """로그아웃 시 인증 정보와 사용자별 임시 상태를 비운다."""
    for key in [
        "access_token",
        "user",
        "analysis_ids",
        "search_analysis_ids",
        "search_selected_job",
        "resumes_selected_document_id",
        "analysis_error",
        "is_requesting",
    ]:
        st.session_state.pop(key, None)
    st.session_state[_DELETE_AUTH_COOKIE_KEY] = True


def store_auth_payload(payload: dict) -> None:
    """인증 API 성공 응답 payload를 Streamlit 세션에 저장한다.

    Args:
        payload: access token과 공개 사용자 정보를 담은 인증 응답 JSON.
    """
    st.session_state["access_token"] = payload["access_token"]
    st.session_state["user"] = payload["user"]
