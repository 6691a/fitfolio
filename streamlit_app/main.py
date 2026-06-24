import time

import httpx
import streamlit as st

from app.schemas.documents import DocumentFormat, ParseApplicationAccepted, ParseJobStatus
from streamlit_app.settings import f_settings

st.set_page_config(page_title="Fitfolio", layout="centered")

st.title("Fitfolio")
st.caption("이력서 1개와 채용 공고 1개를 업로드하세요.")

FORMAT_LABELS = {
    DocumentFormat.PDF: "PDF",
    DocumentFormat.IMAGE: "IMAGE",
    DocumentFormat.DOCX: "DOCX",
    DocumentFormat.PPT: "PPT",
}

FILE_UPLOAD_SETTINGS = {
    DocumentFormat.PDF: {
        "extensions": ["pdf"],
    },
    DocumentFormat.IMAGE: {
        "extensions": ["png", "jpg", "jpeg"],
    },
    DocumentFormat.DOCX: {
        "extensions": ["docx"],
    },
    DocumentFormat.PPT: {
        "extensions": ["ppt", "pptx"],
    },
}

JOB_POSTING_FORMAT_OPTIONS = [*FILE_UPLOAD_SETTINGS, DocumentFormat.URL]
JOB_POSTING_FORMAT_LABELS = {**FORMAT_LABELS, DocumentFormat.URL: "URL"}

resume_format = st.radio(
    "이력서 파일 타입",
    list(FILE_UPLOAD_SETTINGS),
    format_func=lambda document_format: FORMAT_LABELS[document_format],
    horizontal=True,
)
resume_settings = FILE_UPLOAD_SETTINGS[resume_format]
resume_file = st.file_uploader(
    "이력서 파일 (1개)",
    type=resume_settings["extensions"],
    accept_multiple_files=False,
    key="resume_file",
)

job_posting_format = st.radio(
    "채용 공고 입력 방식",
    JOB_POSTING_FORMAT_OPTIONS,
    format_func=lambda document_format: JOB_POSTING_FORMAT_LABELS[document_format],
    horizontal=True,
)

job_posting_file = None
job_posting_url = None

if job_posting_format == DocumentFormat.URL:
    job_posting_url = st.text_input("채용 공고 URL").strip()
    st.caption("사람인·원티드·잡코리아·링크드인·점핏·리멤버 링크만 지원합니다.")
else:
    job_posting_settings = FILE_UPLOAD_SETTINGS[job_posting_format]
    job_posting_file = st.file_uploader(
        "채용 공고 파일 (1개)",
        type=job_posting_settings["extensions"],
        accept_multiple_files=False,
        key="job_posting_file",
    )

job_posting_ready = bool(job_posting_url) if job_posting_format == DocumentFormat.URL else job_posting_file is not None
ready = resume_file is not None and job_posting_ready
is_requesting = st.session_state.get("is_requesting", False)

button_slot = st.empty()


def fetch_parse_result(document_id: int) -> dict | None:
    while True:
        status_response = httpx.get(
            f"{f_settings.API_BASE_URL}/documents/parse/{document_id}",
            timeout=30,
        )
        job = ParseJobStatus.model_validate_json(status_response.content)
        if job.status == "done":
            return job.result.model_dump(mode="json") if job.result else None
        if job.status == "failed":
            raise RuntimeError(job.error or "문서 분석에 실패했습니다")
        time.sleep(1)


if button_slot.button("분석 시작", type="primary", disabled=not ready or is_requesting):
    st.session_state["is_requesting"] = True
    st.session_state.pop("analysis_result", None)
    st.session_state.pop("analysis_error", None)
    button_slot.button("분석 중...", type="primary", disabled=True)

    try:
        assert resume_file is not None
        data = {
            "resume_format": resume_format.value,
            "job_posting_format": job_posting_format.value,
        }
        files = {
            "resume_file": (resume_file.name, resume_file.getvalue(), resume_file.type),
        }
        if job_posting_format == DocumentFormat.URL:
            assert job_posting_url is not None
            data["job_posting_url"] = job_posting_url
        else:
            assert job_posting_file is not None
            files["job_posting_file"] = (job_posting_file.name, job_posting_file.getvalue(), job_posting_file.type)

        response = httpx.post(
            f"{f_settings.API_BASE_URL}/documents/parse",
            data=data,
            files=files,
            timeout=30,
        )
        if not response.is_success:
            st.session_state["analysis_error"] = f"업로드 실패: {response.status_code} {response.text}"
        else:
            accepted = ParseApplicationAccepted.model_validate_json(response.content)
            with st.spinner("문서를 분석하는 중입니다..."):
                st.session_state["analysis_result"] = {
                    "resume": fetch_parse_result(accepted.resume_document_id),
                    "job_posting": fetch_parse_result(accepted.job_posting_document_id),
                }
    except Exception as exc:
        st.session_state["analysis_error"] = str(exc)
    finally:
        st.session_state["is_requesting"] = False
        st.rerun()

if analysis_error := st.session_state.get("analysis_error"):
    st.error(analysis_error)

if analysis_result := st.session_state.get("analysis_result"):
    st.subheader("추출 결과")
    st.json(analysis_result)
