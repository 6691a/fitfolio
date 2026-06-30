import time

import httpx
import streamlit as st

from app.schemas.documents import (
    DocumentFormat,
    EmploymentType,
    ParseApplicationAccepted,
    ParseJobStatus,
    Region,
)
from app.schemas.profiles import JobPostingListItem
from streamlit_app.settings import f_settings

PERMANENT_RECRUITING_YEAR = 9999

SORT_OPTIONS = {"등록일순": "created_at", "시작일순": "start_date", "종료일순": "end_date"}
ORDER_OPTIONS = {"내림차순": "desc", "오름차순": "asc"}
ALL_OPTION = "전체"
EMPLOYMENT_OPTIONS = [ALL_OPTION, *(member.value for member in EmploymentType)]
REGION_OPTIONS = [ALL_OPTION, *(member.value for member in Region)]

st.set_page_config(page_title="Fitfolio", layout="centered")

st.title("Fitfolio")

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


def fetch_parse_result(document_id: int) -> dict | None:
    """문서 파싱이 끝날 때까지 상태를 폴링해 결과를 가져온다.

    Args:
        document_id: 상태를 폴링할 문서 ID.

    Returns:
        파싱 완료 시 추출 결과 dict, 결과가 없으면 None.

    Raises:
        RuntimeError: 문서 파싱이 실패 상태로 끝난 경우.
    """
    while True:
        status_response = httpx.get(
            f"{f_settings.API_BASE_URL}/documents/parse/{document_id}",
            timeout=60,
        )
        job = ParseJobStatus.model_validate_json(status_response.content)
        if job.status == "done":
            return job.result.model_dump(mode="json") if job.result else None
        if job.status == "failed":
            raise RuntimeError(job.error or "문서 분석에 실패했습니다")
        time.sleep(f_settings.PARSE_POLL_INTERVAL_SECONDS)


def render_analyze_tab() -> None:
    """이력서·채용공고를 업로드해 분석을 요청하고 결과를 보여주는 탭."""
    st.caption("이력서 1개와 채용 공고 1개를 업로드하세요.")

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

    job_posting_ready = (
        bool(job_posting_url) if job_posting_format == DocumentFormat.URL else job_posting_file is not None
    )
    ready = resume_file is not None and job_posting_ready
    is_requesting = st.session_state.get("is_requesting", False)

    button_slot = st.empty()

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


def _fetch_job_postings(params: dict) -> list[JobPostingListItem]:
    """채용공고 목록 API를 호출해 결과를 반환한다.

    Args:
        params: 쿼리 파라미터(q/employment_type/location/sort/order/limit).

    Returns:
        조회된 채용공고 목록.

    Raises:
        RuntimeError: API가 실패 응답을 준 경우.
    """
    response = httpx.get(f"{f_settings.API_BASE_URL}/documents/job-postings", params=params, timeout=30)
    if not response.is_success:
        raise RuntimeError(f"조회 실패: {response.status_code} {response.text}")
    return [JobPostingListItem.model_validate(item) for item in response.json()]


def _format_date(value: str | None) -> str:
    """ISO 일시 문자열을 날짜로 표시하되, 9999년(상시채용)은 '상시채용'으로 바꾼다."""
    if not value:
        return ""
    if value.startswith(str(PERMANENT_RECRUITING_YEAR)):
        return "상시채용"
    return value[:10]


def render_search_tab() -> None:
    """업로드된 채용공고를 목록으로 보여주고 검색·필터·정렬하는 탭."""
    st.caption("업로드된 채용공고 목록입니다. 검색·필터·정렬을 적용할 수 있습니다.")

    query = st.text_input("검색어 (회사명·기술스택 등)", key="jp_query", placeholder="예: FastAPI, 무신사, 백엔드")

    region_col, employment_col = st.columns(2)
    region = region_col.selectbox("지역 (시/도)", REGION_OPTIONS, key="jp_region")
    employment_type = employment_col.selectbox("채용 형태", EMPLOYMENT_OPTIONS, key="jp_employment")

    sort_col, order_col, limit_col = st.columns([2, 2, 1])
    sort_label = sort_col.selectbox("정렬 기준", list(SORT_OPTIONS), key="jp_sort")
    order_label = order_col.selectbox("정렬 방향", list(ORDER_OPTIONS), key="jp_order")
    limit = limit_col.number_input("개수", min_value=1, max_value=200, value=50, key="jp_limit")

    params: dict = {"sort": SORT_OPTIONS[sort_label], "order": ORDER_OPTIONS[order_label], "limit": int(limit)}
    if query.strip():
        params["q"] = query.strip()
    if region != ALL_OPTION:
        params["region"] = region
    if employment_type != ALL_OPTION:
        params["employment_type"] = employment_type

    try:
        items = _fetch_job_postings(params)
    except Exception as exc:
        st.error(str(exc))
        return

    if not items:
        st.info("조건에 맞는 채용공고가 없습니다.")
        return

    has_score = any(item.score is not None for item in items)
    st.caption(f"{len(items)}건")
    table = []
    for item in items:
        payload = item.model_dump(mode="json")
        row: dict[str, object] = {
            "회사명": item.company_name or "",
            "공고명": item.title or "",
            "지역": item.region.value if item.region else "",
            "채용형태": item.employment_type.value if item.employment_type else "",
            "시작일": _format_date(payload.get("start_date")),
            "종료일": _format_date(payload.get("end_date")),
            "링크": item.source_url or "",
        }
        if has_score:
            row["관련도"] = item.score
        table.append(row)

    st.dataframe(
        table,
        use_container_width=True,
        hide_index=True,
        column_config={"링크": st.column_config.LinkColumn("링크")},
    )


analyze_tab, search_tab = st.tabs(["분석", "공고 검색"])
with analyze_tab:
    render_analyze_tab()
with search_tab:
    render_search_tab()
