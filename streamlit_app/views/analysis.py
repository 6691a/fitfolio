import streamlit as st

from streamlit_app.api import create_analysis, fetch_analysis_result, fetch_parse_result


def _bullets(title: str, entries: list) -> None:
    """제목과 리스트(dict/문자열 혼합)를 불릿으로 렌더링한다."""
    if not entries:
        return
    st.markdown(f"**{title}**")
    for entry in entries:
        if isinstance(entry, dict):
            st.markdown("- " + " · ".join(f"{k}: {v}" for k, v in entry.items() if v))
        else:
            st.markdown(f"- {entry}")


def render_analysis_result(
    resume_document_id: int,
    job_posting_document_id: int,
    *,
    state_key_prefix: str = "analysis_result",
) -> None:
    """백엔드 적합도 분석 API를 호출해 결과를 렌더링한다.

    채용공고 파싱 완료를 기다린 뒤 분석 작업을 등록하고, 완료까지 폴링해
    종합 점수·항목별 점수·스킬 매칭·강점/보완점을 표시한다.

    Args:
        resume_document_id: 분석할 이력서 문서 ID.
        job_posting_document_id: 분석할 채용공고 문서 ID.
        state_key_prefix: 화면별 분석 캐시 구분 prefix.
    """
    state_key = f"{state_key_prefix}_{resume_document_id}_{job_posting_document_id}"
    cached = st.session_state.get(state_key)
    if isinstance(cached, dict) and cached.get("result"):
        render_fit_result(cached["result"])
        return

    try:
        if not isinstance(cached, dict) or not cached.get("analysis_id"):
            with st.spinner("채용공고를 분석하는 중입니다..."):
                fetch_parse_result(job_posting_document_id)
            with st.spinner("적합도 분석 작업을 등록하는 중입니다..."):
                analysis_id = create_analysis(resume_document_id, job_posting_document_id)
            cached = {"analysis_id": analysis_id}
            st.session_state[state_key] = cached

        with st.spinner("이력서와 채용공고의 적합도를 분석하는 중입니다..."):
            result = fetch_analysis_result(int(cached["analysis_id"]))
    except Exception as exc:
        st.error(str(exc))
        return

    st.session_state[state_key] = {
        "analysis_id": cached["analysis_id"],
        "result": result,
    }
    render_fit_result(result)


def render_fit_result(result: dict) -> None:
    """적합도 분석 결과 dict를 점수 카드·스킬 매칭·강점/보완점으로 렌더링한다.

    Args:
        result: FitAnalysisResult 직렬화 dict.
    """
    st.subheader("적합도 분석")
    st.metric("종합 적합도", f"{result['overall_score']}점")
    if result.get("summary"):
        st.write(result["summary"])

    skill_col, career_col, education_col = st.columns(3)
    for column, label, key in (
        (skill_col, "기술", "skill"),
        (career_col, "경력", "career"),
        (education_col, "학력/자격", "education"),
    ):
        dimension = result.get(key) or {}
        with column:
            st.metric(label, f"{dimension.get('score', 0)}점")
            if dimension.get("comment"):
                st.caption(dimension["comment"])

    matched = result.get("matched_skills", [])
    missing = result.get("missing_skills", [])
    if matched:
        st.markdown("**매칭된 스킬**: " + ", ".join(matched))
    if missing:
        st.caption("공고가 요구하지만 이력서에 없는 스킬: " + ", ".join(missing))

    strengths_col, gaps_col = st.columns(2)
    with strengths_col:
        _bullets("강점", result.get("strengths", []))
    with gaps_col:
        _bullets("보완할 점", result.get("gaps", []))
