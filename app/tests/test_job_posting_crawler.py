import pytest

from app.crawlers import job_postings as crawler_module
from app.crawlers.job_postings import JobPostingCrawler, JobPostingCrawlResult
from app.schemas.documents import DocumentKind


class FakeResponse:
    text = "<html><body>ok</body></html>"
    content = text.encode("utf-8")
    url = "https://www.wanted.co.kr/wd/1"
    headers = {"content-type": "text/html"}

    def raise_for_status(self) -> None:
        return None


class FakeAsyncClient:
    def __init__(self, *args, **kwargs) -> None:
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None

    async def get(self, url: str, *args, **kwargs) -> FakeResponse:
        return FakeResponse()


class FakeProtocolCrawler:
    def __init__(self) -> None:
        self.called_with: tuple[str, str] | None = None

    def can_handle(self, url: str) -> bool:
        return url.endswith("/wd/1")

    async def crawl(self, *, client, final_url, html, document_type) -> JobPostingCrawlResult:
        self.called_with = (final_url, html)
        return JobPostingCrawlResult(text="프로토콜 크롤러 결과 본문입니다.")


@pytest.mark.asyncio
async def test_job_posting_crawler_dispatches_to_protocol_implementation(monkeypatch):
    monkeypatch.setattr(crawler_module.httpx, "AsyncClient", FakeAsyncClient)
    protocol_crawler = FakeProtocolCrawler()

    result = await JobPostingCrawler(crawlers=[protocol_crawler]).crawl(
        "https://www.wanted.co.kr/wd/1",
        DocumentKind.JOB_POSTING,
    )

    assert result.text == "프로토콜 크롤러 결과 본문입니다."
    assert protocol_crawler.called_with == ("https://www.wanted.co.kr/wd/1", "<html><body>ok</body></html>")
