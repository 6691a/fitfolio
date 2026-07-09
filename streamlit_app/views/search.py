from datetime import datetime

import streamlit as st

from app.schemas.documents import EmploymentType, Region
from app.schemas.profiles import JobPostingListItem
from streamlit_app.api import fetch_job_postings, fetch_parse_result, fetch_resumes
from streamlit_app.views.analysis import render_analysis_result

PERMANENT_RECRUITING_YEAR = 9999

SORT_OPTIONS = {"등록일순": "created_at", "시작일순": "start_date", "종료일순": "end_date"}
ORDER_OPTIONS = {"내림차순": "desc", "오름차순": "asc"}
ALL_OPTION = "전체"
EMPLOYMENT_OPTIONS = [ALL_OPTION, *(member.value for member in EmploymentType)]
REGION_OPTIONS = [ALL_OPTION, *(member.value for member in Region)]

# 상세 페이지로 넘길 선택 공고를 담아두는 세션 키(라우팅은 main.py가 담당).
SELECTED_JOB_KEY = "search_selected_job"


def _format_date(value: object) -> str:
    """datetime을 날짜로 표시하되, 9999년(상시채용)은 '상시채용'으로 바꾼다."""
    if not isinstance(value, datetime):
        return ""
    if value.year == PERMANENT_RECRUITING_YEAR:
        return "상시채용"
    return value.date().isoformat()


def _render_job_posting_cards(items: list[JobPostingListItem]) -> JobPostingListItem | None:
    """채용공고 목록을 카드로 렌더링한다. '상세 보기'를 누른 공고를 반환한다."""
    selected: JobPostingListItem | None = None
    for item in items:
        with st.container(border=True):
            title = " · ".join(v for v in [item.company_name, item.title] if v) or "채용공고"
            st.markdown(f"**{title}**")
            meta = [
                value
                for value in [
                    item.region.value if item.region else None,
                    item.employment_type.value if item.employment_type else None,
                    " ~ ".join(filter(None, [_format_date(item.start_date), _format_date(item.end_date)])) or None,
                ]
                if value
            ]
            if meta:
                st.caption(" · ".join(meta))
            if item.score is not None:
                st.caption(f"관련도 {item.score}")
            link_col, action_col = st.columns([4, 1])
            if item.source_url:
                link_col.markdown(f"[공고 원본 링크]({item.source_url})")
            if action_col.button("상세 보기", key=f"job_{item.document_id}", width="stretch"):
                selected = item
    return selected


def render_job_posting_list() -> JobPostingListItem | None:
    """검색어·필터·정렬로 채용공고 목록을 조회한다. 행을 선택하면 그 공고를 반환한다.

    Returns:
        선택된 채용공고. 선택이 없으면 None(라우팅은 호출부에서 처리).
    """
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
        items = fetch_job_postings(params)
    except Exception as exc:
        st.error(str(exc))
        return None

    if not items:
        st.info("조건에 맞는 채용공고가 없습니다.")
        return None

    st.caption(f"{len(items)}건 · '상세 보기'를 누르면 상세 페이지로 이동합니다.")
    return _render_job_posting_cards(items)


def _render_sections(sections: list[tuple[str, list]]) -> None:
    """(제목, 항목들) 목록에서 비어있지 않은 섹션만 전체 너비 카드로 세로 배치한다."""
    for title, entries in sections:
        if not entries:
            continue
        with st.container(border=True):
            st.markdown(f"##### {title}")
            st.markdown("\n".join(f"- {entry}" for entry in entries))


def _render_positions(positions: list[dict]) -> None:
    """여러 모집부문(포지션)을 각각 카드로 분리해 렌더링한다.

    한 공고 안에 직무가 여럿이면 업무·자격·우대를 union으로 뭉치지 않고 포지션별로 나눠 보여준다.

    Args:
        positions: 채용공고 프로필의 포지션 dict 목록.
    """
    st.caption(
        f"이 공고에는 모집부문이 {len(positions)}개 있습니다. "
        "적합도 분석은 선택한 이력서에 가장 맞는 포지션을 자동으로 골라 채점합니다."
    )
    for index, position in enumerate(positions, start=1):
        with st.container(border=True):
            st.markdown(f"##### 📌 {position.get('title') or f'포지션 {index}'}")
            chips = [f":blue-badge[{position['domain']}]"] if position.get("domain") else []
            chips += [f":gray-badge[{tag}]" for tag in (position.get("tech_tags") or [])]
            if chips:
                st.markdown(" ".join(chips))
            for label, key in (
                ("💼 주요 업무", "responsibilities"),
                ("✅ 자격 요건", "qualifications"),
                ("⭐ 우대 사항", "preferred_qualifications"),
            ):
                entries = position.get(key) or []
                if entries:
                    st.markdown(f"**{label}**")
                    st.markdown("\n".join(f"- {entry}" for entry in entries))


def render_job_posting_detail(item: JobPostingListItem) -> bool:
    """선택한 채용공고 상세를 렌더링한다.

    Returns:
        '목록으로' 버튼을 눌렀으면 True(라우팅은 호출부에서 처리).
    """
    go_back = st.button("← 목록으로")

    period = " ~ ".join(filter(None, [_format_date(item.start_date), _format_date(item.end_date)]))
    badges = [
        (item.region.value if item.region else None, "blue"),
        (item.employment_type.value if item.employment_type else None, "violet"),
        (item.location, "gray"),
        (f"🗓 {period}" if period else None, "green"),
    ]

    with st.container(border=True):
        if item.company_name:
            st.caption(item.company_name)
        st.markdown(f"### {item.title or item.company_name or '채용공고 상세'}")
        badge_line = " ".join(f":{color}-badge[{text}]" for text, color in badges if text)
        if badge_line:
            st.markdown(badge_line)
        if item.source_url:
            st.link_button("공고 원본 보기 ↗", item.source_url)

    try:
        job = (fetch_parse_result(item.document_id) or {}).get("metadata", {}).get("job_posting_extract") or {}
    except Exception as exc:
        st.error(str(exc))
        job = {}
    positions = job.get("positions") or []
    if len(positions) >= 2:
        _render_positions(positions)
        # 복지/혜택은 공고 전체 공통이라 포지션 밖에서 한 번만 보여준다.
        _render_sections([("🎁 복지/혜택", job.get("benefits", []))])
    else:
        _render_sections(
            [
                ("💼 주요 업무", job.get("responsibilities", [])),
                ("✅ 자격 요건", job.get("qualifications", [])),
                ("⭐ 우대 사항", job.get("preferred_qualifications", [])),
                ("🎁 복지/혜택", job.get("benefits", [])),
            ]
        )

    st.divider()
    _render_analyze_action(item.document_id)
    return go_back


def _render_analyze_action(job_posting_document_id: int) -> None:
    """내 이력서를 골라 이 공고와 적합도 분석을 실행하는 영역."""
    st.markdown("#### 내 이력서로 분석하기")
    try:
        resumes = fetch_resumes()
    except Exception as exc:
        st.error(str(exc))
        return

    if not resumes:
        st.info("분석하려면 먼저 '내 이력서'에서 이력서를 업로드하세요.")
        return

    resume_labels = {
        f"{item.title or item.name or '제목 미상'} (#{item.document_id})": item.document_id for item in resumes
    }
    selected_resume = st.selectbox("분석할 이력서 선택", list(resume_labels), key="search_resume")

    if st.button("이 이력서로 분석", type="primary", key="search_analyze"):
        st.session_state["search_analysis_ids"] = {
            "resume": resume_labels[selected_resume],
            "job_posting": job_posting_document_id,
        }

    ids = st.session_state.get("search_analysis_ids")
    if ids and ids["job_posting"] == job_posting_document_id:
        render_analysis_result(ids["resume"], ids["job_posting"])
