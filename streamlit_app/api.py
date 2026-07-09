import time
from typing import Any

import httpx

from app.schemas.analyses import AnalysisAccepted, AnalysisListItem, AnalysisStatus, InterviewPreparationResult
from app.schemas.documents import ParseJobAccepted, ParseJobStatus
from app.schemas.preferences import PreferencesOut
from app.schemas.profiles import JobPostingListItem, ResumeListItem
from streamlit_app.settings import f_settings
from streamlit_app.state import auth_headers, store_auth_payload

FIELD_LABELS = {
    "email": "이메일",
    "password": "비밀번호",
    "nickname": "닉네임",
}


def response_error_message(response: httpx.Response) -> str:
    """API 실패 응답에서 사용자에게 보여줄 메시지를 만든다.

    Args:
        response: 실패한 HTTP 응답.

    Returns:
        detail 필드 또는 상태코드 기반 메시지.
    """
    try:
        payload = response.json()
        detail = payload.get("detail") if isinstance(payload, dict) else None
    except ValueError:
        detail = None
    if isinstance(detail, list):
        messages = [_validation_error_message(error) for error in detail]
        return "\n".join(message for message in messages if message) or f"요청 실패: {response.status_code}"
    return str(detail or f"요청 실패: {response.status_code}")


def _validation_error_message(error: object) -> str:
    """FastAPI/Pydantic 검증 오류 한 건을 사용자용 한국어 문장으로 바꾼다.

    Args:
        error: FastAPI 422 detail 항목.

    Returns:
        사용자에게 보여줄 검증 오류 메시지.
    """
    if not isinstance(error, dict):
        return str(error)

    field = str((error.get("loc") or [""])[-1])
    label = FIELD_LABELS.get(field, field or "입력값")
    error_type = error.get("type")
    ctx = error.get("ctx") or {}

    if error_type == "string_too_short":
        min_length = ctx.get("min_length")
        return f"{label}는 {min_length}자 이상 입력하세요" if min_length else f"{label}를 더 길게 입력하세요"
    if error_type == "string_too_long":
        max_length = ctx.get("max_length")
        return f"{label}는 {max_length}자 이하로 입력하세요" if max_length else f"{label}를 더 짧게 입력하세요"
    if error_type in {"missing", "value_error.missing"}:
        return f"{label}을 입력하세요"
    if error_type in {"value_error", "value_error.email", "string_pattern_mismatch"} and field == "email":
        return "올바른 이메일을 입력하세요"

    return str(error.get("msg") or f"{label} 값이 올바르지 않습니다")


def _api_url(path: str) -> str:
    """API base URL과 path를 결합한다."""
    return f"{f_settings.API_BASE_URL}{path}"


def _request(method: str, path: str, *, timeout: float = 30, **kwargs: Any) -> httpx.Response:
    """인증 헤더를 붙여 API를 호출하고 실패 응답은 사용자용 RuntimeError로 변환한다."""
    headers = {**auth_headers(), **kwargs.pop("headers", {})}
    response = httpx.request(method, _api_url(path), headers=headers, timeout=timeout, **kwargs)
    if not response.is_success:
        raise RuntimeError(response_error_message(response))
    return response


def submit_auth(path: str, payload: dict[str, str]) -> tuple[bool, str | None]:
    """인증 API에 요청을 보내고 성공 시 세션에 저장한다.

    Args:
        path: `/auth` 아래 경로(login/signup).
        payload: 요청 JSON payload.

    Returns:
        (성공 여부, 실패 메시지).
    """
    try:
        response = httpx.post(_api_url(f"/auth/{path}"), json=payload, timeout=30)
    except Exception as exc:
        return False, str(exc)
    if not response.is_success:
        return False, response_error_message(response)
    store_auth_payload(response.json())
    return True, None


def upload_resume(data: dict[str, str], files: dict) -> int:
    """이력서 파일 하나를 업로드해 파싱 작업을 등록한다.

    Args:
        data: multipart form 필드(resume_format).
        files: multipart file 필드(resume_file).

    Returns:
        등록된 이력서 문서 ID.

    Raises:
        RuntimeError: API가 실패 응답을 준 경우.
    """
    response = _request(
        "POST",
        "/documents/resumes",
        data=data,
        files=files,
        timeout=30,
    )
    return ParseJobAccepted.model_validate_json(response.content).document_id


def upload_job_posting(data: dict[str, str], files: dict) -> int:
    """채용공고 하나를 업로드해 파싱 작업을 등록한다.

    Args:
        data: multipart form 필드(job_posting_format, job_posting_url/text).
        files: multipart file 필드(job_posting_file, 없으면 빈 dict).

    Returns:
        등록된 채용공고 문서 ID.

    Raises:
        RuntimeError: API가 실패 응답을 준 경우.
    """
    response = _request(
        "POST",
        "/documents/job-postings",
        data=data,
        files=files or None,
        timeout=30,
    )
    return ParseJobAccepted.model_validate_json(response.content).document_id


def fetch_resumes(limit: int = 50) -> list[ResumeListItem]:
    """현재 사용자의 이력서 목록 API를 호출해 결과를 반환한다.

    Args:
        limit: 최대 결과 수.

    Returns:
        조회된 이력서 목록.

    Raises:
        RuntimeError: API가 실패 응답을 준 경우.
    """
    response = _request(
        "GET",
        "/documents/resumes",
        params={"limit": limit},
        timeout=30,
    )
    return [ResumeListItem.model_validate(item) for item in response.json()]


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
        status_response = _request(
            "GET",
            f"/documents/parse/{document_id}",
            timeout=60,
        )
        job = ParseJobStatus.model_validate_json(status_response.content)
        if job.status == "done":
            return job.result.model_dump(mode="json") if job.result else None
        if job.status == "failed":
            raise RuntimeError(job.error or "문서 분석에 실패했습니다")
        time.sleep(f_settings.PARSE_POLL_INTERVAL_SECONDS)


def create_analysis(resume_document_id: int, job_posting_document_id: int) -> int:
    """이력서×채용공고 적합도 분석 작업을 등록한다.

    Args:
        resume_document_id: 분석할 이력서 문서 ID.
        job_posting_document_id: 분석할 채용공고 문서 ID.

    Returns:
        등록된 분석 ID.

    Raises:
        RuntimeError: API가 실패 응답을 준 경우(파싱 미완료 409 등).
    """
    response = _request(
        "POST",
        "/analyses",
        json={
            "resume_document_id": resume_document_id,
            "job_posting_document_id": job_posting_document_id,
        },
        timeout=30,
    )
    return AnalysisAccepted.model_validate_json(response.content).analysis_id


def fetch_analysis_result(analysis_id: int) -> dict:
    """적합도 분석이 끝날 때까지 상태를 폴링해 결과를 가져온다.

    Args:
        analysis_id: 상태를 폴링할 분석 ID.

    Returns:
        분석 완료 시 FitAnalysisResult dict.

    Raises:
        RuntimeError: 분석이 실패 상태로 끝났거나 완료 응답에 결과가 없는 경우.
    """
    while True:
        analysis = fetch_analysis(analysis_id)
        if analysis.status == "done":
            if analysis.result is None:
                raise RuntimeError("분석 결과가 비어 있습니다")
            return analysis.result.model_dump(mode="json")
        if analysis.status == "failed":
            raise RuntimeError(analysis.error or "적합도 분석에 실패했습니다")
        time.sleep(f_settings.PARSE_POLL_INTERVAL_SECONDS)


def fetch_analyses(limit: int = 50) -> list[AnalysisListItem]:
    """현재 사용자의 적합도 분석 이력 목록을 조회한다.

    Args:
        limit: 최대 결과 수.

    Returns:
        분석 이력 목록(최신순).

    Raises:
        RuntimeError: API가 실패 응답을 준 경우.
    """
    response = _request(
        "GET",
        "/analyses",
        params={"limit": limit},
        timeout=30,
    )
    return [AnalysisListItem.model_validate(item) for item in response.json()]


def delete_analysis(analysis_id: int) -> None:
    """적합도 분석 이력 한 건을 삭제한다(soft delete).

    Args:
        analysis_id: 삭제할 분석 ID.

    Raises:
        RuntimeError: API가 실패 응답을 준 경우.
    """
    _request(
        "DELETE",
        f"/analyses/{analysis_id}",
        timeout=30,
    )


def fetch_analysis(analysis_id: int) -> AnalysisStatus:
    """적합도 분석 한 건의 현재 상태·결과를 조회한다(폴링 없음).

    Args:
        analysis_id: 조회할 분석 ID.

    Returns:
        분석 상태(완료면 결과 포함).

    Raises:
        RuntimeError: API가 실패 응답을 준 경우.
    """
    response = _request(
        "GET",
        f"/analyses/{analysis_id}",
        timeout=30,
    )
    return AnalysisStatus.model_validate_json(response.content)


def create_interview_preparation(analysis_id: int) -> InterviewPreparationResult:
    """완료된 적합도 분석을 기준으로 면접 질문/답변 예시를 생성한다.

    Args:
        analysis_id: 면접 준비를 생성할 분석 ID.

    Returns:
        생성되었거나 캐시된 면접 준비 결과.

    Raises:
        RuntimeError: API가 실패 응답을 준 경우.
    """
    response = _request(
        "POST",
        f"/analyses/{analysis_id}/interview-prep",
        timeout=60,
    )
    return InterviewPreparationResult.model_validate_json(response.content)


def submit_analysis_feedback(analysis_id: int, rating: float, note: str) -> None:
    """완료된 적합도 분석에 별점·메모 피드백을 남긴다.

    Args:
        analysis_id: 피드백을 남길 분석 ID.
        rating: 별점(0.5~5.0).
        note: 자유 피드백 메모.

    Raises:
        RuntimeError: API가 실패 응답을 준 경우.
    """
    _request(
        "POST",
        f"/analyses/{analysis_id}/feedback",
        json={"rating": rating, "note": note},
        timeout=30,
    )


def fetch_preferences() -> PreferencesOut:
    """현재 사용자의 개인화 프로필을 조회한다.

    Returns:
        개인화 프로필(설정 전이면 모든 필드가 None).

    Raises:
        RuntimeError: API가 실패 응답을 준 경우.
    """
    response = _request(
        "GET",
        "/me/preferences",
        timeout=30,
    )
    return PreferencesOut.model_validate_json(response.content)


def save_preferences(interest_jobs: str, interest_skills: str, notes: str) -> None:
    """현재 사용자의 관심 직무·기술 수정본을 저장한다(빈 문자열은 None으로 보낸다).

    Args:
        interest_jobs: 관심 직무(사용자 수정본).
        interest_skills: 관심 기술/역량(사용자 수정본).
        notes: 자유 기타 메모.

    Raises:
        RuntimeError: API가 실패 응답을 준 경우.
    """
    _request(
        "PUT",
        "/me/preferences",
        json={
            "interest_jobs": interest_jobs or None,
            "interest_skills": interest_skills or None,
            "notes": notes or None,
        },
        timeout=30,
    )


def fetch_job_postings(params: dict) -> list[JobPostingListItem]:
    """채용공고 목록 API를 호출해 결과를 반환한다.

    Args:
        params: 쿼리 파라미터(q/employment_type/location/sort/order/limit).

    Returns:
        조회된 채용공고 목록.

    Raises:
        RuntimeError: API가 실패 응답을 준 경우.
    """
    response = _request(
        "GET",
        "/documents/job-postings",
        params=params,
        timeout=30,
    )
    return [JobPostingListItem.model_validate(item) for item in response.json()]
