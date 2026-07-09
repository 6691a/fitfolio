import streamlit as st

from streamlit_app.api import fetch_preferences, save_preferences


def render_preferences_page() -> None:
    """관심 직무·기술을 조회·수정하는 폼을 렌더링한다.

    폼은 최근 분석 이력에서 자동 추출한 제안값으로 미리 채워지며, 사용자가 수정·저장하면
    저장값이 우선한다. 저장 전에는 새 분석에 따라 제안값이 계속 갱신된다.
    저장된 값은 이후 적합도 분석·면접 질문 답변의 강조점·톤 개인화에 쓰인다.
    """
    st.subheader("관심 직무 · 기술")
    st.caption("최근 분석한 채용공고에서 자동으로 추출했습니다. 필요하면 수정해서 저장하세요.")

    if st.session_state.pop("preferences_saved", False):
        st.success("관심 설정이 저장되었습니다.")

    try:
        current = fetch_preferences()
    except Exception as exc:
        st.error(str(exc))
        return

    # 저장값(사용자 수정본)이 있으면 그것, 없으면 자동 추출 제안값으로 미리 채운다.
    jobs_value = current.interest_jobs or current.suggested_jobs or ""
    skills_value = current.interest_skills or current.suggested_skills or ""

    with st.form("preferences_form"):
        interest_jobs = st.text_area(
            "관심 직무",
            value=jobs_value,
            placeholder="예: 백엔드 개발자, 데이터 엔지니어",
        )
        interest_skills = st.text_area(
            "관심 기술/역량",
            value=skills_value,
            placeholder="예: Python, FastAPI, AWS",
        )
        notes = st.text_area(
            "강조하고 싶은 점·답변 톤 등 (자유)",
            value=current.notes or "",
            placeholder="예: 데이터 파이프라인 경험을 강조하고, 답변은 간결하게",
        )
        submitted = st.form_submit_button("저장", width="stretch")

    if submitted:
        try:
            save_preferences(interest_jobs, interest_skills, notes)
        except Exception as exc:
            st.error(str(exc))
        else:
            st.session_state["preferences_saved"] = True
            st.rerun()
