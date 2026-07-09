import streamlit as st

from app.schemas.documents import DocumentFormat
from streamlit_app.api import fetch_resumes, upload_job_posting
from streamlit_app.views.analysis import render_analysis_result

FILE_EXTENSIONS = {
    DocumentFormat.PDF: ["pdf"],
    DocumentFormat.DOCX: ["docx"],
}

JOB_POSTING_FORMAT_OPTIONS = [*FILE_EXTENSIONS, DocumentFormat.URL]


def format_label(document_format: DocumentFormat) -> str:
    """문서 포맷 enum을 selectbox/radio 표시용 라벨로 바꾼다."""
    return document_format.value.upper()


def render_analyze_page() -> None:
    """업로드한 이력서를 선택하고 채용 공고를 올려 분석을 요청하는 페이지."""
    st.caption("업로드한 이력서를 선택하고 채용 공고 1개를 올려 분석하세요.")

    try:
        resumes = fetch_resumes()
    except Exception as exc:
        st.error(str(exc))
        return

    if not resumes:
        st.info("먼저 '내 이력서'에서 이력서를 업로드하세요.")
        return

    resume_labels = {
        f"{item.title or item.name or '제목 미상'} (#{item.document_id}) · {item.created_at.date().isoformat()}": item.document_id
        for item in resumes
    }
    selected_resume_label = st.selectbox("분석할 이력서 선택", list(resume_labels))
    resume_document_id = resume_labels[selected_resume_label]

    job_posting_format = st.radio(
        "채용 공고 입력 방식",
        JOB_POSTING_FORMAT_OPTIONS,
        format_func=format_label,
        horizontal=True,
    )

    job_posting_file = None
    job_posting_url = None

    if job_posting_format == DocumentFormat.URL:
        job_posting_url = st.text_input("채용 공고 URL").strip()
        st.caption("사람인·원티드·잡코리아·링크드인·점핏·리멤버 링크만 지원합니다.")
    else:
        job_posting_file = st.file_uploader(
            "채용 공고 파일 (1개)",
            type=FILE_EXTENSIONS[job_posting_format],
            accept_multiple_files=False,
            key="job_posting_file",
        )

    ready = bool(job_posting_url) if job_posting_format == DocumentFormat.URL else job_posting_file is not None
    is_requesting = bool(st.session_state.get("is_requesting", False))
    is_analyzing = bool(st.session_state.get("is_analyzing", False))

    button_slot = st.empty()

    is_busy = is_requesting or is_analyzing
    button_label = "분석 중..." if is_busy else "분석 시작"
    if button_slot.button(button_label, type="primary", disabled=not ready or is_busy):
        st.session_state["is_requesting"] = True
        st.session_state["is_analyzing"] = False
        st.session_state.pop("analysis_ids", None)
        st.session_state.pop("analysis_error", None)
        st.rerun()

    if is_requesting:
        try:
            with st.spinner("채용공고를 업로드하고 있습니다..."):
                data = {"job_posting_format": job_posting_format.value}
                files = {}
                if job_posting_format == DocumentFormat.URL:
                    assert job_posting_url is not None
                    data["job_posting_url"] = job_posting_url
                else:
                    assert job_posting_file is not None
                    files["job_posting_file"] = (
                        job_posting_file.name,
                        job_posting_file.getvalue(),
                        job_posting_file.type,
                    )

                job_posting_document_id = upload_job_posting(data, files)
            st.session_state["analysis_ids"] = {
                "resume": resume_document_id,
                "job_posting": job_posting_document_id,
            }
            st.session_state["is_analyzing"] = True
        except Exception as exc:
            st.session_state["analysis_error"] = str(exc)
        finally:
            st.session_state["is_requesting"] = False
            st.rerun()

    if analysis_error := st.session_state.get("analysis_error"):
        st.error(analysis_error)

    if analysis_ids := st.session_state.get("analysis_ids"):
        analysis_rendered = render_analysis_result(analysis_ids["resume"], analysis_ids["job_posting"])
        if st.session_state.get("is_analyzing"):
            st.session_state["is_analyzing"] = False
            if analysis_rendered:
                st.rerun()
