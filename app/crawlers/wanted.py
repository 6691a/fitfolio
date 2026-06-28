import json

import httpx
from lxml import html as lxml_html

from app.crawlers.job_postings import JobPostingCrawlResult
from app.crawlers.utils import (
    clean_text,
    is_wanted_url,
    job_posting_structured_payload,
    save_debug_text,
    serialize_node,
)
from app.schemas.documents import DocumentKind, JobPostingExtractDebug


class WantedJobPostingCrawler:
    def can_handle(self, url: str) -> bool:
        """원티드 URL을 처리할 수 있는지 여부를 반환한다.

        Args:
            url: 판단할 URL.

        Returns:
            원티드 도메인이면 True.
        """
        return is_wanted_url(url)

    async def crawl(
        self,
        *,
        client: httpx.AsyncClient,
        final_url: str,
        html: str,
        document_type: DocumentKind,
    ) -> JobPostingCrawlResult:
        """원티드 공고에서 __NEXT_DATA__ 또는 상세 HTML을 추출해 정리한다.

        Args:
            client: 재사용할 HTTP 클라이언트.
            final_url: 최종 URL.
            html: 페이지 HTML.
            document_type: 문서 종류.

        Returns:
            추출 텍스트/HTML과 구조화 디버그를 담은 JobPostingCrawlResult.
        """
        try:
            doc = lxml_html.fromstring(html)
        except Exception:
            save_debug_text(html, "url-page")
            return JobPostingCrawlResult(htmls=[html])

        wanted_next_data = self._extract_wanted_next_data(final_url, doc)
        if wanted_next_data:
            wanted_text, wanted_data = wanted_next_data
            wanted_debug = self._wanted_debug_payload(final_url, wanted_text, wanted_data)
            wanted_debug = await job_posting_structured_payload(wanted_text, wanted_debug)
            save_debug_text(
                json.dumps(wanted_data, ensure_ascii=False, indent=2),
                "url-wanted-next-data",
                "json",
            )
            save_debug_text(
                wanted_debug.model_dump_json(indent=2, exclude_none=True),
                "url-wanted-selected",
                "json",
            )
            save_debug_text(wanted_text, "url-wanted-selected", "txt")
            return JobPostingCrawlResult(text=wanted_text, structured_debug=wanted_debug)

        wanted_html = self._extract_wanted_detail_html(final_url, doc)
        if not wanted_html:
            save_debug_text(html, "url-page")
            return JobPostingCrawlResult(htmls=[html])

        wanted_debug = self._wanted_html_debug_payload(final_url, wanted_html)
        wanted_debug = await job_posting_structured_payload(
            clean_text(lxml_html.fromstring(wanted_html).text_content()),
            wanted_debug,
        )
        save_debug_text(wanted_html, "url-wanted-selected")
        save_debug_text(
            wanted_debug.model_dump_json(indent=2, exclude_none=True),
            "url-wanted-selected",
            "json",
        )
        return JobPostingCrawlResult(htmls=[wanted_html], structured_debug=wanted_debug)

    def _extract_wanted_next_data(self, final_url: str, doc) -> tuple[str, dict] | None:
        """원티드 __NEXT_DATA__ 스크립트에서 공고 본문과 원본 데이터를 추출한다.

        Args:
            final_url: 최종 URL.
            doc: 파싱된 lxml 문서.

        Returns:
            (정리된 본문 텍스트, initialData dict) 튜플, 없으면 None.
        """
        if not is_wanted_url(final_url):
            return None

        raw_json = doc.xpath('string(//script[@id="__NEXT_DATA__"])').strip()
        if not raw_json:
            return None

        try:
            data = json.loads(raw_json)
            initial_data = data["props"]["pageProps"]["initialData"]
        except (KeyError, TypeError, json.JSONDecodeError):
            return None

        if not isinstance(initial_data, dict):
            return None

        text = self._wanted_initial_data_to_text(initial_data)
        return (text, initial_data) if text else None

    def _wanted_initial_data_to_text(self, initial_data: dict) -> str:
        """원티드 initialData의 섹션들을 사람이 읽을 본문 텍스트로 합친다.

        Args:
            initial_data: 원티드 __NEXT_DATA__의 initialData dict.

        Returns:
            섹션 제목과 내용을 이어 붙인 본문 텍스트.
        """
        sections = [
            ("포지션", initial_data.get("position")),
            ("포지션 상세", initial_data.get("intro")),
            ("주요업무", initial_data.get("main_tasks")),
            ("자격요건", initial_data.get("requirements")),
            ("우대사항", initial_data.get("preferred_points")),
            ("혜택 및 복지", initial_data.get("benefits")),
            ("채용절차", initial_data.get("hire_rounds")),
        ]
        parts: list[str] = []
        for title, value in sections:
            if not isinstance(value, str):
                continue
            content = value.strip()
            if not content:
                continue
            parts.append(content if content.startswith(title) else f"{title}\n{content}")
        return "\n\n".join(parts).strip()

    def _wanted_debug_payload(self, final_url: str, selected_text: str, initial_data: dict) -> JobPostingExtractDebug:
        """원티드 initialData로부터 구조화 디버그 payload를 만든다.

        Args:
            final_url: 공고 상세 URL.
            selected_text: 선택된 본문 텍스트.
            initial_data: 원티드 initialData dict.

        Returns:
            제목/포지션/본문을 채운 JobPostingExtractDebug.
        """
        position = initial_data.get("position")
        normalized_position = position if isinstance(position, str) else None
        return JobPostingExtractDebug(
            source="wanted",
            detail_url=final_url,
            title=normalized_position,
            position=normalized_position,
            text=selected_text,
            raw=initial_data,
        )

    def _wanted_html_debug_payload(self, final_url: str, selected_html: str) -> JobPostingExtractDebug:
        """원티드 상세 HTML로부터 구조화 디버그 payload를 만든다.

        Args:
            final_url: 공고 상세 URL.
            selected_html: 선택된 상세 영역 HTML.

        Returns:
            제목/본문/HTML을 채운 JobPostingExtractDebug.
        """
        doc = lxml_html.fromstring(selected_html)
        title = self._wanted_first_heading(doc)
        return JobPostingExtractDebug(
            source="wanted",
            detail_url=final_url,
            title=title,
            position=title,
            text=clean_text(doc.text_content()),
            html=selected_html,
        )

    def _wanted_first_heading(self, doc) -> str | None:
        """문서에서 첫 번째로 비어 있지 않은 제목(h1~h3)을 찾는다.

        Args:
            doc: 파싱된 lxml 문서.

        Returns:
            첫 제목 텍스트, 없으면 None.
        """
        for selector in ("//h1", "//h2", "//h3"):
            values = [clean_text(node.text_content()) for node in doc.xpath(selector)]
            for value in values:
                if value:
                    return value
        return None

    def _extract_wanted_detail_html(self, final_url: str, doc) -> str | None:
        """원티드 상세 영역(JobDescription 등) HTML을 선택해 반환한다.

        Args:
            final_url: 최종 URL.
            doc: 파싱된 lxml 문서.

        Returns:
            상세 영역 HTML 문자열, 없으면 None.
        """
        if not is_wanted_url(final_url):
            return None

        selectors = (
            '//article[contains(@class, "JobDescription_")]',
            '//section[contains(@class, "JobContent_descriptionWrapper")]',
        )
        for selector in selectors:
            matches = doc.xpath(selector)
            if matches:
                return serialize_node(matches[0])
        return None
