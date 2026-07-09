import streamlit as st

from app.schemas.analyses import InterviewPreparationResult
from streamlit_app.api import (
    create_analysis,
    create_interview_preparation,
    fetch_analysis_result,
    fetch_parse_result,
    submit_analysis_feedback,
)


def _stars(rating: float) -> str:
    """별점(0.5 단위)을 ★/½/☆ 문자열로 만든다."""
    full = int(rating)
    half = 1 if rating - full >= 0.5 else 0
    return "★" * full + "½" * half + "☆" * (5 - full - half)


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
) -> bool:
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
        render_fit_result(cached["result"], analysis_id=cached.get("analysis_id"))
        return True

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
        return False

    st.session_state[state_key] = {
        "analysis_id": cached["analysis_id"],
        "result": result,
    }
    render_fit_result(result, analysis_id=int(cached["analysis_id"]))
    return True


def render_fit_result(result: dict, *, analysis_id: int | None = None) -> None:
    """적합도 분석 결과 dict를 점수 카드·스킬 매칭·강점/보완점으로 렌더링한다.

    Args:
        result: FitAnalysisResult 직렬화 dict.
        analysis_id: 값이 있으면 별점 피드백 위젯을 함께 렌더링한다.
    """
    st.subheader("적합도 분석")
    if result.get("matched_position"):
        st.caption(
            f"이 공고의 여러 모집부문 중 이력서에 가장 맞는 포지션 기준으로 분석했습니다: **{result['matched_position']}**"
        )
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

    if analysis_id is not None:
        render_feedback_widget(analysis_id)
        render_interview_preparation_widget(analysis_id)


def render_feedback_widget(analysis_id: int) -> None:
    """분석 결과에 별점(0.5~5.0)과 메모 피드백을 남기는 위젯을 렌더링한다.

    남긴 피드백은 다음 분석·면접 답변 개인화에 반영된다.

    Args:
        analysis_id: 피드백을 남길 분석 ID.
    """
    st.divider()
    success_key = f"feedback_success_{analysis_id}"
    if st.session_state.pop(success_key, False):
        st.success("피드백이 저장되었습니다. 다음 분석에 반영됩니다.")

    st.markdown("**이 분석이 도움이 되었나요?** (다음 답변 개인화에 반영돼요)")
    rating = st.slider(
        "별점",
        min_value=0.5,
        max_value=5.0,
        value=3.0,
        step=0.5,
        key=f"feedback_rating_{analysis_id}",
    )
    st.caption(f"{_stars(rating)} ({rating})")
    note = st.text_input(
        "무엇이 좋았거나 아쉬웠는지 (선택)",
        key=f"feedback_note_{analysis_id}",
        placeholder="예: 강점을 더 구체적으로, 톤은 더 간결하게",
    )
    if st.button("피드백 보내기", key=f"feedback_submit_{analysis_id}", width="stretch"):
        try:
            submit_analysis_feedback(analysis_id, rating, note)
        except Exception as exc:
            st.error(str(exc))
        else:
            st.session_state[success_key] = True
            st.rerun()


def render_interview_preparation(preparation: InterviewPreparationResult) -> None:
    """면접 준비 질문/답변 결과를 렌더링한다."""
    st.subheader("면접 준비")
    st.caption(preparation.summary)

    def render_questions(questions) -> None:
        for index, item in enumerate(questions, start=1):
            with st.expander(f"Q{index}. {item.question}", expanded=index == 1):
                st.markdown(f"**답변 예시**  \n{item.answer}")
                st.caption(f"의도: {item.intent} · 근거: {item.source}")

    general_tab, professional_tab = st.tabs(["일반 면접", "직무 면접"])
    with general_tab:
        render_questions(preparation.general_questions)
    with professional_tab:
        render_questions(preparation.professional_questions)


def render_interview_preparation_widget(analysis_id: int) -> None:
    """완료된 분석 기준 면접 질문 준비 버튼과 결과를 렌더링한다."""
    prep_key = f"interview_preparation_{analysis_id}"
    loading_key = f"interview_preparation_loading_{analysis_id}"
    success_key = f"interview_preparation_success_{analysis_id}"

    if st.session_state.pop(success_key, False):
        st.success("면접 질문이 준비되었습니다.")

    is_loading = bool(st.session_state.get(loading_key))
    button_label = "면접 질문 다시 불러오기" if prep_key in st.session_state else "면접 질문 준비하기"
    if st.button(
        button_label,
        key=f"prepare_interview_{analysis_id}",
        disabled=is_loading,
        width="stretch",
    ):
        st.session_state[loading_key] = True
        st.session_state.pop(success_key, None)
        st.rerun()

    if is_loading:
        try:
            with st.spinner("면접 질문을 준비하고 있습니다..."):
                preparation = create_interview_preparation(analysis_id)
        except Exception as exc:
            st.error(str(exc))
        else:
            st.session_state[prep_key] = preparation.model_dump(mode="json")
            st.session_state[success_key] = True
        finally:
            st.session_state[loading_key] = False
            st.rerun()

    if prep_key in st.session_state:
        render_interview_preparation(InterviewPreparationResult.model_validate(st.session_state[prep_key]))
