import streamlit as st

from app.schemas.profiles import ResumeListItem
from streamlit_app.api import fetch_parse_result, fetch_resumes, upload_resume
from streamlit_app.views.analyze import FILE_EXTENSIONS, format_label

ENTRY_LABELS = {
    "company": "회사",
    "organization": "기관",
    "school": "학교",
    "project": "프로젝트",
    "name": "이름",
    "title": "제목",
    "role": "역할",
    "position": "직무",
    "period": "기간",
    "date": "일자",
    "duration": "기간",
    "description": "설명",
    "responsibilities": "담당 업무",
    "achievements": "성과",
    "tech_stack": "기술",
    "technologies": "기술",
    "skills": "기술",
    "degree": "학위",
    "major": "전공",
    "issuer": "발급기관",
}
TITLE_KEYS = ("company", "organization", "school", "project", "name", "title")
SUBTITLE_KEYS = ("role", "position", "degree", "major")
DATE_KEYS = ("period", "date", "duration")
HIDDEN_ENTRY_KEYS = {"employment_type"}

# 상세 페이지로 넘길 선택 이력서 문서 ID를 담아두는 세션 키(라우팅은 main.py가 담당).
SELECTED_RESUME_KEY = "resumes_selected_document_id"


def _render_resume_uploader() -> None:
    """이력서 파일 하나를 업로드해 파싱을 요청하는 상단 폼을 렌더링한다."""
    resume_format = st.radio(
        "이력서 파일 타입",
        list(FILE_EXTENSIONS),
        format_func=format_label,
        horizontal=True,
        key="my_resume_format",
    )
    resume_file = st.file_uploader(
        "이력서 파일 (1개)",
        type=FILE_EXTENSIONS[resume_format],
        accept_multiple_files=False,
        key="my_resume_file",
    )

    is_uploading = st.session_state.get("is_uploading_resume", False)
    button_slot = st.empty()
    if button_slot.button("이력서 업로드", type="primary", disabled=resume_file is None or is_uploading):
        st.session_state["is_uploading_resume"] = True
        st.session_state.pop("resume_upload_error", None)
        button_slot.button("업로드 중...", type="primary", disabled=True)
        try:
            assert resume_file is not None
            document_id = upload_resume(
                {"resume_format": resume_format.value},
                {"resume_file": (resume_file.name, resume_file.getvalue(), resume_file.type)},
            )
            with st.spinner("이력서를 분석하는 중입니다..."):
                fetch_parse_result(document_id)
        except Exception as exc:
            st.session_state["resume_upload_error"] = str(exc)
        finally:
            st.session_state["is_uploading_resume"] = False
            st.rerun()

    if error := st.session_state.get("resume_upload_error"):
        st.error(error)


def _resume_label(item: ResumeListItem) -> str:
    """이력서 목록/선택 UI에 쓸 이름(타이틀 우선, 없으면 지원자 이름)을 만든다."""
    return item.title or item.name or "제목 미상"


def _render_resume_cards(items: list[ResumeListItem]) -> int | None:
    """이력서 목록을 카드로 렌더링한다. '상세 보기'를 누른 이력서의 문서 ID를 반환한다."""
    selected: int | None = None
    for item in items:
        with st.container(border=True):
            st.markdown(f"**{_resume_label(item)}**")
            meta = [value for value in [item.name, item.email] if value]
            meta.append(f"등록일 {item.created_at.date().isoformat()}")
            st.caption(" · ".join(meta))
            if item.career_summary:
                st.write(item.career_summary)
            _, action_col = st.columns([4, 1])
            if action_col.button("상세 보기", key=f"resume_{item.document_id}", width="stretch"):
                selected = item.document_id
    return selected


def _stringify_resume_value(value: object) -> str:
    """이력서 상세 값이 dict/list여도 JSON 원문 대신 읽기 좋은 문자열로 바꾼다."""
    if value is None:
        return ""
    if isinstance(value, list):
        return ", ".join(_stringify_resume_value(item) for item in value if _stringify_resume_value(item))
    if isinstance(value, dict):
        return " · ".join(
            f"{ENTRY_LABELS.get(str(key), str(key))}: {_stringify_resume_value(item)}"
            for key, item in value.items()
            if _stringify_resume_value(item)
        )
    return str(value).strip()


def _first_value(entry: dict, keys: tuple[str, ...]) -> str:
    """지정한 키들 중 처음으로 값이 있는 문자열을 반환한다."""
    for key in keys:
        value = _stringify_resume_value(entry.get(key))
        if value:
            return value
    return ""


def _format_resume_entry(entry: dict | str, *, fallback_title: str) -> tuple[str, list[str]]:
    """이력서 상세 항목을 제목과 설명 줄로 나눠 렌더링하기 좋게 만든다."""
    if not isinstance(entry, dict):
        return _stringify_resume_value(entry) or fallback_title, []

    primary = _first_value(entry, TITLE_KEYS)
    secondary = _first_value(entry, SUBTITLE_KEYS)
    title = " · ".join(part for part in [primary, secondary] if part) or fallback_title

    used_keys = {*TITLE_KEYS, *SUBTITLE_KEYS}
    lines = []
    date_value = _first_value(entry, DATE_KEYS)
    if date_value:
        lines.append(f"기간: {date_value}")
        used_keys.update(DATE_KEYS)
    used_keys.update(HIDDEN_ENTRY_KEYS)

    for key, value in entry.items():
        if key in used_keys:
            continue
        rendered = _stringify_resume_value(value)
        if rendered:
            lines.append(f"{ENTRY_LABELS.get(str(key), str(key))}: {rendered}")
    return title, lines


def _render_resume_entries(title: str, entries: list) -> None:
    """이력서 상세 항목 리스트를 섹션 제목 + 항목별 카드로 렌더링한다."""
    if not entries:
        return
    st.markdown(f"##### {title}")
    for entry in entries:
        entry_title, lines = _format_resume_entry(entry, fallback_title=title)
        with st.container(border=True):
            st.markdown(f"**{entry_title}**")
            if lines and lines[0].startswith("기간: "):
                st.caption(f"🗓 {lines[0].removeprefix('기간: ')}")
                lines = lines[1:]
            if lines:
                st.markdown("\n".join(f"- {line}" for line in lines))


def _render_text_block(title: str, value: str | None) -> None:
    """긴 텍스트 값을 제목이 있는 카드형 블록으로 렌더링한다."""
    if not value:
        return
    with st.container(border=True):
        st.markdown(f"##### {title}")
        st.write(value)


def render_resume_detail(document_id: int) -> bool:
    """선택한 이력서 상세를 렌더링한다.

    Returns:
        '목록으로' 버튼을 눌렀으면 True(라우팅은 호출부에서 처리).
    """
    go_back = st.button("← 목록으로")

    try:
        result = fetch_parse_result(document_id)
    except Exception as exc:
        st.error(str(exc))
        return go_back

    extract = (result or {}).get("metadata", {}).get("resume_extract")
    if not extract:
        st.info("표시할 상세 정보가 없습니다.")
        return go_back

    # 헤더 카드: 타이틀·이름·연락처 배지·링크를 한곳에 모은다(채용공고 상세와 동일한 톤).
    title = extract.get("title")
    name = extract.get("name") or "이름 미상"
    with st.container(border=True):
        if title:
            st.caption(name)
        st.markdown(f"### {title or name}")
        badges = [
            (f"📧 {extract['email']}" if extract.get("email") else None, "blue"),
            (f"📞 {extract['phone']}" if extract.get("phone") else None, "green"),
        ]
        badge_line = " ".join(f":{color}-badge[{text}]" for text, color in badges if text)
        if badge_line:
            st.markdown(badge_line)
        links = [url for url in extract.get("links") or [] if url]
        if links:
            st.markdown(" · ".join(f"🔗 [{url}]({url})" for url in links))

    if skills := [skill for skill in extract.get("skills") or [] if skill]:
        with st.container(border=True):
            st.markdown("##### 🛠 보유 기술")
            st.markdown(" ".join(f":gray-badge[{skill}]" for skill in skills))

    _render_text_block("📝 경력 요약", extract.get("career_summary"))
    _render_text_block("💬 자기소개", extract.get("self_introduction"))

    _render_resume_entries("💼 경력", extract.get("work_experiences", []))
    _render_resume_entries("🚀 프로젝트", extract.get("projects", []))
    _render_resume_entries("🎓 학력", extract.get("education", []))
    _render_resume_entries("🏆 자격증/수상", extract.get("certifications", []))
    _render_resume_entries("📎 기타", extract.get("etc", []))
    return go_back


def render_resume_list() -> int | None:
    """이력서를 업로드하고 목록을 보여준다. 행을 선택하면 그 문서 ID를 반환한다.

    Returns:
        선택된 이력서 문서 ID. 선택이 없으면 None(라우팅은 호출부에서 처리).
    """
    st.caption("내 이력서를 업로드하고, 목록에서 선택해 상세 내용을 볼 수 있습니다.")

    _render_resume_uploader()
    st.divider()

    try:
        items = fetch_resumes()
    except Exception as exc:
        st.error(str(exc))
        return None

    if not items:
        st.info("아직 업로드한 이력서가 없습니다.")
        return None

    st.caption(f"내 이력서 {len(items)}건 · '상세 보기'를 누르면 상세 페이지로 이동합니다.")
    return _render_resume_cards(items)
