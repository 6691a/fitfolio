import streamlit as st

from app.schemas.analyses import AnalysisListItem, InterviewPreparationResult
from streamlit_app.api import create_interview_preparation, delete_analysis, fetch_analyses, fetch_analysis
from streamlit_app.views.analysis import render_fit_result

# 상세 페이지로 넘길 선택 분석 ID를 담아두는 세션 키(라우팅은 main.py가 담당).
SELECTED_ANALYSIS_KEY = "history_selected_analysis_id"

_STATUS_BADGES = {
    "pending": ":gray-badge[대기 중]",
    "started": ":blue-badge[분석 중]",
    "retry": ":orange-badge[재시도 중]",
    "done": ":green-badge[완료]",
    "failed": ":red-badge[실패]",
}


def _analysis_label(item: AnalysisListItem) -> str:
    """분석 카드 제목(이력서 × 공고)을 만든다."""
    resume = item.resume_title or item.resume_name or "이력서"
    job = " ".join(v for v in [item.company_name, item.job_posting_title] if v) or "채용공고"
    return f"{resume} × {job}"


def _render_analysis_cards(items: list[AnalysisListItem]) -> int | None:
    """분석 이력 목록을 카드로 렌더링한다. '결과 보기'를 누른 분석 ID를 반환한다.

    '삭제'를 누르면 그 자리에서 soft delete 후 페이지를 새로고침한다.
    """
    selected: int | None = None
    for item in items:
        with st.container(border=True):
            title_col, score_col = st.columns([4, 1])
            title_col.markdown(f"**{_analysis_label(item)}**")
            if item.overall_score is not None:
                score_col.markdown(f"### {item.overall_score}점")
            badge = _STATUS_BADGES.get(item.status.value, item.status.value)
            st.markdown(f"{badge} · 분석일 {item.created_at.date().isoformat()}")
            _, result_col, delete_col = st.columns([3, 1, 1])
            if result_col.button("결과 보기", key=f"analysis_{item.analysis_id}", width="stretch"):
                selected = item.analysis_id
            if delete_col.button("삭제", key=f"delete_{item.analysis_id}", width="stretch"):
                try:
                    delete_analysis(item.analysis_id)
                except Exception as exc:
                    st.error(str(exc))
                else:
                    st.rerun()
    return selected


def _render_interview_preparation(preparation: InterviewPreparationResult) -> None:
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


def render_analysis_history_list() -> int | None:
    """내 적합도 분석 이력을 최신순 카드로 보여준다.

    Returns:
        선택된 분석 ID. 선택이 없으면 None(라우팅은 호출부에서 처리).
    """
    st.caption("이전에 실행한 적합도 분석 결과를 다시 볼 수 있습니다.")

    try:
        items = fetch_analyses()
    except Exception as exc:
        st.error(str(exc))
        return None

    if not items:
        st.info("아직 실행한 적합도 분석이 없습니다. '분석하기'에서 이력서와 채용공고를 선택해 분석해보세요.")
        return None

    st.caption(f"분석 이력 {len(items)}건 · '결과 보기'를 누르면 상세 결과로 이동합니다.")
    return _render_analysis_cards(items)


def render_analysis_detail(analysis_id: int) -> bool:
    """선택한 적합도 분석의 상세 결과를 렌더링한다.

    Args:
        analysis_id: 표시할 분석 ID.

    Returns:
        '목록으로' 버튼을 눌렀으면 True(라우팅은 호출부에서 처리).
    """
    go_back = st.button("← 목록으로")

    try:
        analysis = fetch_analysis(analysis_id)
    except Exception as exc:
        st.error(str(exc))
        return go_back

    if analysis.status == "failed":
        st.error(analysis.error or "적합도 분석에 실패했습니다.")
    elif analysis.result is None:
        st.info("아직 분석이 진행 중입니다. 잠시 후 다시 확인해주세요.")
    else:
        render_fit_result(analysis.result.model_dump(mode="json"))
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
            _render_interview_preparation(InterviewPreparationResult.model_validate(st.session_state[prep_key]))
    return go_back
