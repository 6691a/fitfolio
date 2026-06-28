from dataclasses import dataclass, field
from typing import Protocol

import httpx

from app.config.settings import settings
from app.crawlers.utils import save_debug_text
from app.schemas.documents import DocumentKind, JobPostingExtractDebug
from app.security.job_domains import is_allowed_job_domain


class BlockedJobUrlError(Exception):
    pass


class JobUrlFetchError(Exception):
    pass


@dataclass
class JobPostingCrawlResult:
    htmls: list[str] = field(default_factory=list)
    text: str | None = None
    image_texts: list[str] = field(default_factory=list)
    structured_debug: JobPostingExtractDebug | None = None


class JobPostingProtocol(Protocol):
    def can_handle(self, url: str) -> bool:
        """이 크롤러가 해당 URL을 처리할 수 있는지 여부를 반환한다.

        Args:
            url: 처리 가능 여부를 판단할 URL.

        Returns:
            처리 가능하면 True.
        """
        pass

    async def crawl(
        self,
        *,
        client: httpx.AsyncClient,
        final_url: str,
        html: str,
        document_type: DocumentKind,
    ) -> JobPostingCrawlResult:
        """도메인별로 채용공고 페이지를 크롤링해 결과를 반환한다.

        Args:
            client: 재사용할 HTTP 클라이언트.
            final_url: 리다이렉트까지 반영된 최종 URL.
            html: 최초로 받은 페이지 HTML.
            document_type: 문서 종류.

        Returns:
            추출 텍스트/HTML/이미지 텍스트를 담은 JobPostingCrawlResult.
        """
        pass


class JobPostingCrawler:
    def __init__(self, crawlers: list[JobPostingProtocol]) -> None:
        """도메인별 크롤러 목록을 주입받아 보관한다.

        Args:
            crawlers: URL을 처리할 도메인별 크롤러 리스트.
        """
        self._crawlers = crawlers

    async def crawl(self, url: str, document_type: DocumentKind) -> JobPostingCrawlResult:
        """URL을 검증·요청하고 처리 가능한 도메인 크롤러에 위임한다.

        Args:
            url: 크롤링할 채용공고 URL.
            document_type: 문서 종류.

        Returns:
            도메인 크롤러의 결과, 처리기가 없으면 원본 HTML을 담은 결과.

        Raises:
            BlockedJobUrlError: 최초 URL 또는 리다이렉트된 URL이 허용 도메인이 아닐 때.
            JobUrlFetchError: 페이지를 불러오지 못한 경우.
        """
        if not is_allowed_job_domain(url):
            raise BlockedJobUrlError(f"허용되지 않은 도메인입니다: {url}")

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "ko-KR,ko;q=0.9",
        }
        timeout = httpx.Timeout(settings.DOCUMENT_URL_TIMEOUT_MS / 1000)
        async with httpx.AsyncClient(follow_redirects=True, timeout=timeout, headers=headers) as client:
            try:
                resp = await client.get(url)
                resp.raise_for_status()
            except httpx.HTTPError as exc:
                raise JobUrlFetchError(
                    "채용 공고 페이지를 불러오지 못했습니다. "
                    "잠시 후 다시 시도하거나 공고 본문을 직접 복사해 붙여주세요."
                ) from exc

            final_url = str(resp.url)
            if not is_allowed_job_domain(final_url):
                raise BlockedJobUrlError(f"허용되지 않은 도메인으로 이동했습니다: {final_url}")

            html = resp.text
            for crawler in self._crawlers:
                if crawler.can_handle(final_url):
                    return await crawler.crawl(
                        client=client,
                        final_url=final_url,
                        html=html,
                        document_type=document_type,
                    )

            save_debug_text(html, "url-page")
            return JobPostingCrawlResult(htmls=[html])
