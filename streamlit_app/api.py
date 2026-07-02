import time

import httpx

from app.schemas.documents import ParseJobAccepted, ParseJobStatus
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
        detail = response.json().get("detail")
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


def submit_auth(path: str, payload: dict[str, str]) -> tuple[bool, str | None]:
    """인증 API에 요청을 보내고 성공 시 세션에 저장한다.

    Args:
        path: `/auth` 아래 경로(login/signup).
        payload: 요청 JSON payload.

    Returns:
        (성공 여부, 실패 메시지).
    """
    try:
        response = httpx.post(f"{f_settings.API_BASE_URL}/auth/{path}", json=payload, timeout=30)
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
    response = httpx.post(
        f"{f_settings.API_BASE_URL}/documents/resumes",
        data=data,
        files=files,
        headers=auth_headers(),
        timeout=30,
    )
    if not response.is_success:
        raise RuntimeError(f"업로드 실패: {response.status_code} {response.text}")
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
    response = httpx.post(
        f"{f_settings.API_BASE_URL}/documents/job-postings",
        data=data,
        files=files or None,
        headers=auth_headers(),
        timeout=30,
    )
    if not response.is_success:
        raise RuntimeError(f"업로드 실패: {response.status_code} {response.text}")
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
    response = httpx.get(
        f"{f_settings.API_BASE_URL}/documents/resumes",
        params={"limit": limit},
        headers=auth_headers(),
        timeout=30,
    )
    if not response.is_success:
        raise RuntimeError(f"조회 실패: {response.status_code} {response.text}")
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
        status_response = httpx.get(
            f"{f_settings.API_BASE_URL}/documents/parse/{document_id}",
            headers=auth_headers(),
            timeout=60,
        )
        job = ParseJobStatus.model_validate_json(status_response.content)
        if job.status == "done":
            return job.result.model_dump(mode="json") if job.result else None
        if job.status == "failed":
            raise RuntimeError(job.error or "문서 분석에 실패했습니다")
        time.sleep(f_settings.PARSE_POLL_INTERVAL_SECONDS)


def fetch_job_postings(params: dict) -> list[JobPostingListItem]:
    """채용공고 목록 API를 호출해 결과를 반환한다.

    Args:
        params: 쿼리 파라미터(q/employment_type/location/sort/order/limit).

    Returns:
        조회된 채용공고 목록.

    Raises:
        RuntimeError: API가 실패 응답을 준 경우.
    """
    response = httpx.get(
        f"{f_settings.API_BASE_URL}/documents/job-postings",
        params=params,
        headers=auth_headers(),
        timeout=30,
    )
    if not response.is_success:
        raise RuntimeError(f"조회 실패: {response.status_code} {response.text}")
    return [JobPostingListItem.model_validate(item) for item in response.json()]
