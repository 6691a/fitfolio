import streamlit as st

from streamlit_app.api import fetch_parse_result


def _extract(document_id: int, key: str) -> dict:
    """문서 파싱 결과 metadata에서 구조화 추출 dict(resume/job_posting)를 꺼낸다."""
    return (fetch_parse_result(document_id) or {}).get("metadata", {}).get(key) or {}


def _matched_skills(skills: list[str], job_text: str) -> list[str]:
    """보유 스킬 중 채용공고 본문에 등장하는 것만 부분일치(대소문자 무시)로 고른다."""
    lowered = job_text.lower()
    return [skill for skill in skills if skill and skill.lower() in lowered]


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


def render_analysis_result(resume_document_id: int, job_posting_document_id: int) -> None:
    """선택한 이력서와 채용공고 파싱 결과로 스킬 매칭·요약 분석을 렌더링한다.

    Args:
        resume_document_id: 분석할 이력서 문서 ID.
        job_posting_document_id: 분석할 채용공고 문서 ID.
    """
    with st.spinner("문서를 분석하는 중입니다..."):
        try:
            resume = _extract(resume_document_id, "resume_extract")
            job = _extract(job_posting_document_id, "job_posting_extract")
        except Exception as exc:
            st.error(str(exc))
            return

    skills: list[str] = resume.get("skills", [])
    job_text = " ".join(
        [
            job.get("title") or "",
            job.get("position") or "",
            *job.get("qualifications", []),
            *job.get("preferred_qualifications", []),
            *job.get("responsibilities", []),
        ]
    )
    matched = _matched_skills(skills, job_text)

    st.subheader("적합도 분석")
    # ponytail: 실제 적합도 채점 백엔드가 없어 프런트에서 스킬 부분일치로만 매칭한다.
    if skills:
        st.metric("공고와 매칭된 보유 스킬", f"{len(matched)} / {len(skills)}")
        st.markdown("**매칭된 스킬**: " + (", ".join(matched) if matched else "없음"))
        unmatched = [skill for skill in skills if skill not in matched]
        if unmatched:
            st.caption("매칭되지 않은 보유 스킬: " + ", ".join(unmatched))
    else:
        st.info("이력서에서 추출된 스킬이 없어 매칭을 계산할 수 없습니다.")

    resume_col, job_col = st.columns(2)
    with resume_col:
        st.markdown("#### 이력서")
        if resume.get("name"):
            st.markdown(f"**{resume['name']}**")
        if resume.get("career_summary"):
            st.write(resume["career_summary"])
        if skills:
            st.markdown("**보유 기술**: " + ", ".join(skills))
    with job_col:
        st.markdown("#### 채용공고")
        header = " · ".join(v for v in [job.get("company_name"), job.get("title") or job.get("position")] if v)
        if header:
            st.markdown(f"**{header}**")
        requirement = " / ".join(v for v in [job.get("career_requirement"), job.get("education_requirement")] if v)
        if requirement:
            st.caption(requirement)
        _bullets("자격 요건", job.get("qualifications", []))
        _bullets("우대 사항", job.get("preferred_qualifications", []))
        _bullets("주요 업무", job.get("responsibilities", []))
