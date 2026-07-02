import streamlit as st


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


def store_auth_payload(payload: dict) -> None:
    """인증 API 성공 응답 payload를 Streamlit 세션에 저장한다.

    Args:
        payload: access token과 공개 사용자 정보를 담은 인증 응답 JSON.
    """
    st.session_state["access_token"] = payload["access_token"]
    st.session_state["user"] = payload["user"]
