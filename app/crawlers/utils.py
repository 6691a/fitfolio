import logging
import re
import uuid
from pathlib import Path
from typing import cast
from urllib.parse import parse_qs, urlparse

import fitz
from lxml import html as lxml_html

from app.ai.extraction import StructuredExtractionError, extract_job_posting_structured
from app.config.settings import settings
from app.schemas.documents import JobPostingExtractDebug
from app.security.job_domains import is_allowed_job_domain
from app.utils import clean_text  # 재노출: 크롤러 모듈들이 app.crawlers.utils에서 import

logger = logging.getLogger(__name__)
DEBUG_IMAGE_DIR = settings.UPLOAD_DIR / settings.DOCUMENT_DEBUG_IMAGE_SUBDIR


def save_debug_image(data: bytes, ext: str, tag: str) -> None:
    """디버그가 켜져 있으면 이미지를 디버그 디렉터리에 저장한다.

    Args:
        data: 저장할 이미지 바이트.
        ext: 파일 확장자.
        tag: 파일명 접두 태그.
    """
    if not settings.DOCUMENT_DEBUG_ENABLED:
        return
    path = DEBUG_IMAGE_DIR / f"{tag}-{uuid.uuid4().hex[:8]}.{ext}"
    path.write_bytes(data)
    logger.info("디버그 이미지 저장: %s", path)


def save_debug_text(text: str, tag: str, ext: str = "html") -> None:
    """디버그가 켜져 있으면 텍스트를 디버그 디렉터리에 저장한다.

    Args:
        text: 저장할 텍스트.
        tag: 파일명 접두 태그.
        ext: 파일 확장자(기본 html).
    """
    if not settings.DOCUMENT_DEBUG_ENABLED:
        return
    path = DEBUG_IMAGE_DIR / f"{tag}-{uuid.uuid4().hex[:8]}.{ext}"
    path.write_text(text, encoding="utf-8")
    logger.info("디버그 HTML 저장: %s (len=%d)", path, len(text))


def host_has_suffix(url: str, suffix: str) -> bool:
    """URL의 호스트가 주어진 도메인이거나 그 서브도메인인지 검사한다.

    Args:
        url: 검사할 URL.
        suffix: 비교할 도메인 접미사.

    Returns:
        호스트가 일치하거나 서브도메인이면 True.
    """
    host = (urlparse(url).hostname or "").lower()
    return host == suffix or host.endswith(f".{suffix}")


def is_saramin_url(url: str) -> bool:
    """URL이 사람인 도메인인지 여부를 반환한다.

    Args:
        url: 검사할 URL.

    Returns:
        사람인 도메인이면 True.
    """
    return host_has_suffix(url, settings.SARAMIN_HOST_SUFFIX)


def is_saramin_image_url(url: str) -> bool:
    """URL이 https 사람인 이미지 도메인인지 여부를 반환한다.

    Args:
        url: 검사할 이미지 URL.

    Returns:
        https이고 사람인 이미지 도메인이면 True.
    """
    parsed = urlparse(url)
    return parsed.scheme == "https" and host_has_suffix(url, settings.SARAMIN_IMAGE_HOST_SUFFIX)


def is_allowed_job_asset_url(page_url: str, asset_url: str) -> bool:
    """페이지에서 참조한 자산 URL을 가져와도 되는지 검사한다.

    Args:
        page_url: 자산을 참조한 페이지 URL.
        asset_url: 검사할 자산(이미지 등) URL.

    Returns:
        허용 도메인이거나, 사람인 페이지의 사람인 이미지면 True.
    """
    if is_allowed_job_domain(asset_url):
        return True
    return is_saramin_url(page_url) and is_saramin_image_url(asset_url)


def is_wanted_url(url: str) -> bool:
    """URL이 원티드 도메인인지 여부를 반환한다.

    Args:
        url: 검사할 URL.

    Returns:
        원티드 도메인이면 True.
    """
    return host_has_suffix(url, settings.WANTED_HOST_SUFFIX)


def saramin_rec_idx(url: str) -> str | None:
    """사람인 URL 쿼리에서 rec_idx 값을 꺼낸다.

    Args:
        url: 사람인 공고 URL.

    Returns:
        rec_idx 값, 없으면 None.
    """
    values = parse_qs(urlparse(url).query).get("rec_idx")
    return values[0] if values else None


def saramin_view_type(url: str) -> str:
    """사람인 URL 쿼리에서 view_type 값을 꺼낸다.

    Args:
        url: 사람인 공고 URL.

    Returns:
        view_type 값, 없으면 기본값 'search'.
    """
    values = parse_qs(urlparse(url).query).get("view_type")
    return values[0] if values else "search"


def saramin_request_path(page_html: str) -> str:
    """페이지 HTML에서 사람인 relay ajax 요청 경로를 찾는다.

    Args:
        page_html: 사람인 페이지 HTML.

    Returns:
        찾은 requestUrl, 없으면 기본 relay ajax 경로.
    """
    match = re.search(r"['\"]requestUrl['\"]\s*:\s*['\"]([^'\"]+)['\"]", page_html)
    return match.group(1) if match else settings.SARAMIN_RELAY_AJAX_PATH


def image_extension(content_type: str | None, url: str) -> str:
    """content-type 또는 URL 확장자로부터 이미지 파일 확장자를 결정한다.

    Args:
        content_type: 응답 content-type 헤더(없을 수 있음).
        url: 이미지 URL(확장자 추정용).

    Returns:
        추정한 확장자(jpg/png/webp/gif), 알 수 없으면 'img'.
    """
    normalized = (content_type or "").split(";")[0].strip().lower()
    content_type_extensions = {
        "image/jpeg": "jpg",
        "image/png": "png",
        "image/webp": "webp",
        "image/gif": "gif",
    }
    if normalized in content_type_extensions:
        return content_type_extensions[normalized]

    suffix = Path(urlparse(url).path).suffix.lower().lstrip(".")
    if suffix in {"jpg", "jpeg", "png", "webp", "gif"}:
        return "jpg" if suffix == "jpeg" else suffix
    return "img"


def _image_dimensions(data: bytes) -> tuple[int, int] | None:
    """이미지 바이트에서 (너비, 높이)를 구한다.

    Args:
        data: 이미지 바이트.

    Returns:
        (너비, 높이) 튜플, 디코딩 실패 시 None.
    """
    try:
        pixmap = fitz.Pixmap(data)
    except Exception:
        return None
    return pixmap.width, pixmap.height


def is_job_posting_image_candidate(data: bytes) -> bool:
    """이미지가 채용공고 본문(세로로 긴 통이미지) 후보인지 판단한다.

    Args:
        data: 이미지 바이트.

    Returns:
        OCR 대상으로 삼을 만한 통이미지면 True.
    """
    dimensions = _image_dimensions(data)
    if dimensions is None:
        return len(data) >= settings.DOCUMENT_MIN_IMAGE_BYTES

    width, height = dimensions
    if width <= 0:
        return False
    if height >= settings.JOB_IMAGE_MIN_TALL_HEIGHT:
        return True
    return height / width >= settings.JOB_IMAGE_MIN_TALL_RATIO and height >= 600


def image_debug_summary(data: bytes) -> str:
    """로그용으로 이미지 크기/비율 요약 문자열을 만든다.

    Args:
        data: 이미지 바이트.

    Returns:
        바이트 수와 (가능하면) 너비/높이/비율을 담은 요약 문자열.
    """
    dimensions = _image_dimensions(data)
    if dimensions is None:
        return f"bytes={len(data)} dimensions=unknown"

    width, height = dimensions
    return f"bytes={len(data)} width={width} height={height} ratio={height / width if width else 0:.2f}"


def serialize_node(node) -> str:
    """lxml 노드를 HTML 문자열로 직렬화한다.

    Args:
        node: 직렬화할 lxml 엘리먼트.

    Returns:
        해당 노드의 HTML 문자열.
    """
    return cast(str, lxml_html.tostring(node, encoding="unicode", method="html"))


def remove_label(text: str, labels: tuple[str, ...]) -> str:
    """텍스트 앞머리의 불릿/라벨(예: '근무지:')을 제거한다.

    Args:
        text: 정리할 텍스트.
        labels: 제거할 라벨 후보들.

    Returns:
        라벨이 제거된 값.
    """
    value = clean_text(text)
    value = re.sub(r"^[•\-\s]+", "", value)
    for label in labels:
        value = re.sub(rf"^{re.escape(label)}\s*[:：]?\s*", "", value).strip()
    return value


async def job_posting_structured_payload(text: str, fallback: JobPostingExtractDebug) -> JobPostingExtractDebug:
    """채용공고 구조화 추출을 시도하고 실패 시 폴백을 사용한다.

    Args:
        text: 채용공고 본문 텍스트.
        fallback: 추출 실패 시 사용할 기본 추출 결과.

    Returns:
        구조화된 JobPostingExtractDebug.

    Raises:
        InsufficientJobContentError: 채용공고로 보이지 않을 때.
    """
    try:
        payload = await extract_job_posting_structured(text, fallback)
    except StructuredExtractionError:
        payload = fallback

    if not payload.relevant:
        from app.services.document import InsufficientJobContentError

        raise InsufficientJobContentError(payload.failure_reason or "이 문서는 채용공고로 보이지 않습니다.")
    return payload
