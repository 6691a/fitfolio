from app.security.job_domains import is_allowed_job_domain


def test_allows_exact_domain():
    assert is_allowed_job_domain("https://saramin.co.kr/mock/job-posting") is True


def test_allows_subdomain():
    assert is_allowed_job_domain("https://www.saramin.co.kr/mock/job-posting") is True


def test_rejects_suffix_spoofing():
    assert is_allowed_job_domain("https://saramin.co.kr.evil.com/mock/job-posting") is False


def test_rejects_unlisted_domain():
    assert is_allowed_job_domain("https://example.com/mock/job-posting") is False


def test_rejects_http_scheme():
    assert is_allowed_job_domain("http://saramin.co.kr/mock/job-posting") is False


def test_rejects_missing_host():
    assert is_allowed_job_domain("not-a-url") is False
