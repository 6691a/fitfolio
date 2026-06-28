from urllib.parse import urlparse

from app.config.settings import settings


def is_allowed_job_domain(url: str) -> bool:
    """채용공고 URL이 허용 도메인(https)에 속하는지 검사한다.

    Args:
        url: 검사할 채용공고 URL.

    Returns:
        scheme가 https이고 호스트가 허용 도메인이거나 그 서브도메인이면 True.
    """
    parsed = urlparse(url)
    if parsed.scheme != "https":
        return False

    host = (parsed.hostname or "").lower()
    if not host:
        return False

    return any(host == domain or host.endswith(f".{domain}") for domain in settings.ALLOWED_JOB_DOMAINS)
