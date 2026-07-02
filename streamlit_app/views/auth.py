import streamlit as st

from streamlit_app.api import submit_auth


def _validate_login(email: str, password: str) -> str | None:
    """로그인 입력의 백엔드 제한(이메일/비밀번호)을 API 호출 전에 검사한다.

    Args:
        email: 입력한 이메일.
        password: 입력한 비밀번호.

    Returns:
        위반 시 안내 메시지, 문제가 없으면 None.
    """
    if not email.strip():
        return "이메일을 입력하세요"
    if not 8 <= len(password) <= 128:
        return "비밀번호는 8~128자로 입력하세요"
    return None


def _validate_signup(password: str, password_confirm: str) -> str | None:
    """회원가입 입력 중 클라이언트에서만 검사 가능한 비밀번호 확인 일치를 검사한다.

    나머지 형식 검사(이메일·닉네임·비밀번호 길이)는 백엔드 422 응답을
    `api.py:_validation_error_message`가 한국어로 번역해 보여준다.

    Args:
        password: 입력한 비밀번호.
        password_confirm: 확인용 비밀번호.

    Returns:
        위반 시 안내 메시지, 문제가 없으면 None.
    """
    if password != password_confirm:
        return "비밀번호가 일치하지 않습니다"
    return None


def render_login_page() -> None:
    """로그인 폼을 렌더링하고 성공 시 세션에 인증 정보를 저장한다."""
    with st.form("login_form"):
        email = st.text_input("이메일", key="login_email")
        password = st.text_input("비밀번호", type="password", key="login_password")
        submitted = st.form_submit_button("로그인", type="primary")
    if submitted:
        error = _validate_login(email, password)
        if error:
            st.error(error)
            return
        ok, message = submit_auth("login", {"email": email, "password": password})
        if ok:
            st.rerun()
        st.error(message or "로그인에 실패했습니다")


def render_signup_page() -> None:
    """회원가입 폼을 렌더링하고 성공 시 세션에 인증 정보를 저장한다."""
    with st.form("signup_form"):
        email = st.text_input("이메일", key="signup_email")
        nickname = st.text_input("닉네임", key="signup_nickname", help="2~50자로 입력하세요")
        password = st.text_input("비밀번호", type="password", key="signup_password", help="8~128자로 입력하세요")
        password_confirm = st.text_input("비밀번호 확인", type="password", key="signup_password_confirm")
        submitted = st.form_submit_button("회원가입", type="primary")
    if submitted:
        error = _validate_signup(password, password_confirm)
        if error:
            st.error(error)
            return
        ok, message = submit_auth(
            "signup",
            {"email": email, "password": password, "nickname": nickname},
        )
        if ok:
            st.rerun()
        st.error(message or "회원가입에 실패했습니다")
