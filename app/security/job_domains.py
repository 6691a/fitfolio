from urllib.parse import urlparse

ALLOWED_JOB_DOMAINS = frozenset(
    {
        "saramin.co.kr",
        "wanted.co.kr",
        "jobkorea.co.kr",
        "linkedin.com",
        "jumpit.co.kr",
        "rememberapp.co.kr",
    }
)


def is_allowed_job_domain(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme != "https":
        return False

    host = (parsed.hostname or "").lower()
    if not host:
        return False

    return any(host == domain or host.endswith(f".{domain}") for domain in ALLOWED_JOB_DOMAINS)
