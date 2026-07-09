import streamlit as st

from streamlit_app.state import clear_auth_state, is_authenticated, sync_auth_cookie
from streamlit_app.views import (
    SELECTED_ANALYSIS_KEY,
    SELECTED_JOB_KEY,
    SELECTED_RESUME_KEY,
    render_analysis_detail,
    render_analysis_history_list,
    render_analyze_page,
    render_job_posting_detail,
    render_job_posting_list,
    render_login_page,
    render_preferences_page,
    render_resume_detail,
    render_resume_list,
    render_signup_page,
)

st.set_page_config(page_title="Fitfolio", layout="centered")
sync_auth_cookie()


def _center_link(page, label: str) -> None:
    """가운데 좁은 컬럼에 페이지 링크를 배치해 보조 액션처럼 보이게 한다.

    Args:
        page: 이동할 st.Page.
        label: 링크에 표시할 문구.
    """
    _, mid, _ = st.columns([1, 2, 1])
    mid.page_link(page, label=label)


def _authenticated_frame() -> None:
    """인증 페이지 공통 프레임: 미로그인 시 로그인으로 보내고 헤더·내비를 렌더링한다."""
    if not is_authenticated():
        st.switch_page(login_page)
    render_authenticated_header()
    render_authenticated_navigation()


def render_authenticated_header() -> None:
    """로그인한 사용자 정보와 로그아웃 버튼을 상단 헤더처럼 렌더링한다."""
    user = st.session_state.get("user", {})
    user_label = user.get("nickname") or user.get("email") or "사용자"
    title_col, user_col, action_col = st.columns([4, 2, 1])
    title_col.title("Fitfolio")
    user_col.caption(f"{user_label}님")
    if action_col.button("로그아웃"):
        clear_auth_state()
        st.switch_page(login_page)
    st.divider()


def render_authenticated_navigation() -> None:
    """인증 후 주요 화면으로 이동하는 버튼들을 항상 같은 위치에 렌더링한다."""
    analyze_col, history_col, search_col, resumes_col, prefs_col = st.columns(5)
    analyze_col.page_link(analyze_page, label="분석하기", width="stretch")
    history_col.page_link(history_page, label="분석 이력", width="stretch")
    search_col.page_link(search_page, label="공고 검색", width="stretch")
    resumes_col.page_link(resumes_page, label="내 이력서 관리", width="stretch")
    prefs_col.page_link(preferences_page, label="관심 설정", width="stretch")
    st.divider()


def render_home_route() -> None:
    """루트(`/`)에서 인증 상태에 따라 URL 페이지로 리다이렉트한다."""
    st.switch_page(analyze_page if is_authenticated() else login_page)


def render_login_route() -> None:
    """로그인 URL 페이지를 렌더링한다."""
    st.title("Fitfolio")
    if is_authenticated():
        st.switch_page(analyze_page)
    render_login_page()
    st.divider()
    _center_link(signup_page, "계정이 없으신가요? 회원가입")


def render_signup_route() -> None:
    """회원가입 URL 페이지를 렌더링한다."""
    st.title("Fitfolio")
    if is_authenticated():
        st.switch_page(analyze_page)
    render_signup_page()
    st.divider()
    _center_link(login_page, "이미 계정이 있으신가요? 로그인")


def render_analyze_route() -> None:
    """분석 URL 페이지를 렌더링한다."""
    _authenticated_frame()
    render_analyze_page()


def render_search_route() -> None:
    """공고 검색 목록 URL 페이지. 행 선택 시 채용공고 상세 페이지로 이동한다."""
    _authenticated_frame()
    selected = render_job_posting_list()
    if selected is not None:
        st.session_state[SELECTED_JOB_KEY] = selected
        st.switch_page(job_detail_page)


def render_job_detail_route() -> None:
    """선택한 채용공고 상세 URL 페이지. 선택이 없으면 목록으로 되돌린다."""
    _authenticated_frame()
    item = st.session_state.get(SELECTED_JOB_KEY)
    if item is None:
        st.switch_page(search_page)
    if render_job_posting_detail(item):
        st.session_state.pop(SELECTED_JOB_KEY, None)
        st.session_state.pop("search_analysis_ids", None)
        st.switch_page(search_page)


def render_history_route() -> None:
    """분석 이력 목록 URL 페이지. 행 선택 시 분석 상세 페이지로 이동한다."""
    _authenticated_frame()
    selected = render_analysis_history_list()
    if selected is not None:
        st.session_state[SELECTED_ANALYSIS_KEY] = selected
        st.switch_page(analysis_detail_page)


def render_analysis_detail_route() -> None:
    """선택한 분석 상세 URL 페이지. 선택이 없으면 목록으로 되돌린다."""
    _authenticated_frame()
    analysis_id = st.session_state.get(SELECTED_ANALYSIS_KEY)
    if analysis_id is None:
        st.switch_page(history_page)
    if render_analysis_detail(analysis_id):
        st.session_state.pop(SELECTED_ANALYSIS_KEY, None)
        st.switch_page(history_page)


def render_preferences_route() -> None:
    """관심 설정 URL 페이지를 렌더링한다."""
    _authenticated_frame()
    render_preferences_page()


def render_resumes_route() -> None:
    """내 이력서 목록 URL 페이지. 행 선택 시 이력서 상세 페이지로 이동한다."""
    _authenticated_frame()
    selected = render_resume_list()
    if selected is not None:
        st.session_state[SELECTED_RESUME_KEY] = selected
        st.switch_page(resume_detail_page)


def render_resume_detail_route() -> None:
    """선택한 이력서 상세 URL 페이지. 선택이 없으면 목록으로 되돌린다."""
    _authenticated_frame()
    document_id = st.session_state.get(SELECTED_RESUME_KEY)
    if document_id is None:
        st.switch_page(resumes_page)
    if render_resume_detail(document_id):
        st.session_state.pop(SELECTED_RESUME_KEY, None)
        st.switch_page(resumes_page)


# 기본(default) 페이지는 url_path 라우트가 없으므로, 루트는 리다이렉트 전용으로 두고
# 실제 페이지는 모두 non-default로 만들어 각자의 URL(/login·/analyze·/search)을 갖게 한다.
home_page = st.Page(render_home_route, title="홈", default=True, visibility="hidden")
# 인증 페이지는 상단 nav에 노출하지 않는다(폼 하단 링크로만 이동). 라우트는 유지된다.
login_page = st.Page(render_login_route, title="로그인", url_path="login", visibility="hidden")
signup_page = st.Page(render_signup_route, title="회원가입", url_path="signup", visibility="hidden")
analyze_page = st.Page(
    render_analyze_route,
    title="분석",
    url_path="analyze",
    visibility="hidden",
)
search_page = st.Page(
    render_search_route,
    title="공고 검색",
    url_path="search",
    visibility="hidden",
)
job_detail_page = st.Page(
    render_job_detail_route,
    title="채용공고 상세",
    url_path="job-posting",
    visibility="hidden",
)
history_page = st.Page(
    render_history_route,
    title="분석 이력",
    url_path="history",
    visibility="hidden",
)
analysis_detail_page = st.Page(
    render_analysis_detail_route,
    title="분석 결과",
    url_path="analysis",
    visibility="hidden",
)
resumes_page = st.Page(
    render_resumes_route,
    title="내 이력서",
    url_path="resumes",
    visibility="hidden",
)
resume_detail_page = st.Page(
    render_resume_detail_route,
    title="이력서 상세",
    url_path="resume",
    visibility="hidden",
)
preferences_page = st.Page(
    render_preferences_route,
    title="관심 설정",
    url_path="preferences",
    visibility="hidden",
)
page = st.navigation(
    [
        home_page,
        login_page,
        signup_page,
        analyze_page,
        history_page,
        analysis_detail_page,
        search_page,
        job_detail_page,
        resumes_page,
        resume_detail_page,
        preferences_page,
    ],
    position="top",
)
page.run()
