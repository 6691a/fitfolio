import logging
import re
from urllib.parse import urljoin

import httpx
from lxml import html as lxml_html

from app.ai.vision import extract_image_content
from app.crawlers.job_postings import JobPostingCrawlResult
from app.crawlers.utils import (
    clean_text,
    image_debug_summary,
    image_extension,
    is_allowed_job_asset_url,
    is_job_posting_image_candidate,
    is_saramin_url,
    job_posting_structured_payload,
    remove_label,
    saramin_rec_idx,
    saramin_request_path,
    saramin_view_type,
    save_debug_image,
    save_debug_text,
    serialize_node,
)
from app.schemas.documents import DocumentKind, JobPostingExtractDebug, JobPostingImage
from app.security.job_domains import is_allowed_job_domain

logger = logging.getLogger(__name__)


class SaraminJobPostingCrawler:
    def can_handle(self, url: str) -> bool:
        """사람인 URL을 처리할 수 있는지 여부를 반환한다.

        Args:
            url: 판단할 URL.

        Returns:
            사람인 도메인이면 True.
        """
        return is_saramin_url(url)

    async def crawl(
        self,
        *,
        client: httpx.AsyncClient,
        final_url: str,
        html: str,
        document_type: DocumentKind,
    ) -> JobPostingCrawlResult:
        """사람인 공고에서 relay ajax/iframe/이미지를 따라가 본문을 수집한다.

        Args:
            client: 재사용할 HTTP 클라이언트.
            final_url: 최종 URL.
            html: 페이지 HTML.
            document_type: 문서 종류.

        Returns:
            수집한 HTML/이미지 텍스트와 구조화 디버그를 담은 JobPostingCrawlResult.
        """
        htmls = [html]
        image_texts: list[str] = []
        structured_debug: JobPostingExtractDebug | None = None
        saved_primary_debug_html = False

        try:
            doc = lxml_html.fromstring(html)
        except Exception:
            save_debug_text(html, "url-page")
            return JobPostingCrawlResult(htmls=htmls)

        extra_docs = [doc]
        saramin_ajax_html = await self._fetch_saramin_relay_ajax(client, final_url, html)
        if saramin_ajax_html:
            htmls.append(saramin_ajax_html)
            try:
                extra_docs.append(lxml_html.fromstring(saramin_ajax_html))
            except Exception:
                pass

        saramin_selected = False
        for current_doc in extra_docs:
            for iframe in current_doc.iter("iframe"):
                isrc = iframe.get("src")
                if not isrc:
                    continue
                iabs = urljoin(final_url, isrc)
                if not is_allowed_job_domain(iabs):
                    continue
                try:
                    iresp = await client.get(iabs)
                    iresp.raise_for_status()
                    ihtml = iresp.text
                    try:
                        iframe_doc = lxml_html.fromstring(ihtml)
                    except Exception:
                        iframe_doc = None

                    selected_html = (
                        self._extract_saramin_detail_html(iabs, iframe_doc) if iframe_doc is not None else None
                    )
                    if selected_html:
                        htmls = [selected_html]
                        selected_payload = self._saramin_selected_debug_payload(iabs, selected_html, extra_docs)
                        selected_payload = await job_posting_structured_payload(
                            clean_text(lxml_html.fromstring(selected_html).text_content()),
                            selected_payload,
                        )
                        structured_debug = selected_payload
                        saved_primary_debug_html = True
                        saramin_selected = True
                        try:
                            extra_docs = [lxml_html.fromstring(selected_html)]
                        except Exception:
                            extra_docs = []
                        break

                    htmls.append(ihtml)
                    if not saved_primary_debug_html:
                        save_debug_text(ihtml, "url-iframe")
                    if iframe_doc is not None:
                        extra_docs.append(iframe_doc)
                except httpx.HTTPError:
                    continue
            if saramin_selected:
                break

        await self._extract_image_texts(client, final_url, extra_docs, document_type, image_texts, structured_debug)

        if not saved_primary_debug_html:
            save_debug_text(html, "url-page")
        if structured_debug is not None:
            save_debug_text(
                structured_debug.model_dump_json(indent=2, exclude_none=True),
                f"url-{structured_debug.source}-selected",
                "json",
            )

        return JobPostingCrawlResult(
            htmls=htmls,
            image_texts=image_texts,
            structured_debug=structured_debug,
        )

    async def _extract_image_texts(
        self,
        client: httpx.AsyncClient,
        final_url: str,
        docs: list,
        document_type: DocumentKind,
        image_texts: list[str],
        structured_debug: JobPostingExtractDebug | None,
    ) -> None:
        """문서들의 이미지를 받아 통이미지 후보면 비전으로 텍스트를 추출한다.

        추출 결과는 image_texts와 structured_debug에 누적된다(부수 효과).

        Args:
            client: 재사용할 HTTP 클라이언트.
            final_url: 자산 URL 기준이 되는 최종 URL.
            docs: 이미지를 찾을 lxml 문서 리스트.
            document_type: 문서 종류.
            image_texts: 추출 텍스트를 누적할 리스트(수정됨).
            structured_debug: 이미지 텍스트를 반영할 디버그 payload(있으면 수정됨).
        """
        for current_doc in docs:
            for img in current_doc.iter("img"):
                src = img.get("src") or img.get("data-src") or img.get("data-original")
                if not src or src.startswith("data:"):
                    continue
                iabs = urljoin(final_url, src)
                if not is_allowed_job_asset_url(final_url, iabs):
                    continue
                try:
                    imgresp = await client.get(iabs)
                    imgresp.raise_for_status()
                    image_bytes = imgresp.content
                except httpx.HTTPError:
                    continue
                if not is_job_posting_image_candidate(image_bytes):
                    logger.info(
                        "이미지 OCR 스킵: source=url reason=not_tall_job_image url=%s %s",
                        iabs,
                        image_debug_summary(image_bytes),
                    )
                    continue
                ext = image_extension(imgresp.headers.get("content-type"), iabs)
                save_debug_image(image_bytes, ext, "url")
                mime = imgresp.headers.get("content-type", "image/png").split(";")[0]
                result = await extract_image_content(image_bytes, mime, document_type)
                if result.relevant and result.content:
                    image_texts.append(result.content)
                    if structured_debug is not None:
                        self._add_job_image_text(structured_debug, iabs, img.get("alt") or "", result.content)

    def _add_job_image_text(
        self,
        payload: JobPostingExtractDebug,
        src: str,
        alt: str,
        text: str,
    ) -> None:
        """이미지에서 뽑은 텍스트를 디버그 payload에 추가/병합한다.

        Args:
            payload: 갱신할 구조화 디버그 payload(수정됨).
            src: 이미지 절대 URL.
            alt: 이미지 alt 텍스트.
            text: 이미지에서 추출한 텍스트.
        """
        for image in payload.image_urls:
            if image.src == src:
                image.text = text
                break
        else:
            payload.image_urls.append(JobPostingImage(src=src, alt=alt, text=text))

        if text not in payload.text:
            payload.text = f"{payload.text}\n\n이미지 추출 텍스트\n{text}".strip()

    def _extract_saramin_detail_html(self, final_url: str, doc) -> str | None:
        """사람인 상세 영역(user_content 등) HTML을 선택해 반환한다.

        Args:
            final_url: 최종 URL.
            doc: 파싱된 lxml 문서.

        Returns:
            상세 영역 HTML 문자열, 없으면 None.
        """
        if not is_saramin_url(final_url):
            return None

        selectors = (
            '//div[contains(concat(" ", normalize-space(@class), " "), " user_content ")]',
            '//main[contains(concat(" ", normalize-space(@class), " "), " job-posting ")]',
        )
        for selector in selectors:
            matches = doc.xpath(selector)
            if matches:
                return serialize_node(matches[0])
        return None

    def _saramin_selected_debug_payload(
        self, detail_url: str, selected_html: str, context_docs: list | None = None
    ) -> JobPostingExtractDebug:
        """사람인 상세 HTML과 보조 문서들로부터 구조화 디버그 payload를 만든다.

        Args:
            detail_url: 공고 상세 URL.
            selected_html: 선택된 상세 영역 HTML.
            context_docs: 근무지·접수기간 등 필드 보강에 쓸 보조 문서들.

        Returns:
            제목/근무지/접수기간/지원방법/이미지 등을 채운 JobPostingExtractDebug.
        """
        doc = lxml_html.fromstring(selected_html)
        field_docs = [doc, *(context_docs or [])]
        application_period = self._first_saramin_application_period(field_docs)
        image_urls: list[JobPostingImage] = []
        for img in doc.iter("img"):
            src = img.get("src") or img.get("data-src") or img.get("data-original")
            if not src or src.startswith("data:"):
                continue
            image_urls.append(JobPostingImage(src=urljoin(detail_url, src), alt=img.get("alt") or ""))

        title = self._saramin_first_heading(doc)
        return JobPostingExtractDebug(
            source="saramin",
            detail_url=detail_url,
            title=title,
            position=title,
            text=clean_text(doc.text_content()),
            work_location=self._first_saramin_location(field_docs),
            application_start_date=application_period.get("start_date"),
            application_end_date=application_period.get("end_date"),
            application_method=self._first_saramin_application_method(field_docs),
            image_urls=image_urls,
            html=selected_html,
        )

    def _saramin_first_heading(self, doc) -> str | None:
        """문서에서 첫 번째로 비어 있지 않은 제목(h1/h2/strong)을 찾는다.

        Args:
            doc: 파싱된 lxml 문서.

        Returns:
            첫 제목 텍스트, 없으면 None.
        """
        for selector in ("//h1", "//h2", "//strong"):
            values = [clean_text(node.text_content()) for node in doc.xpath(selector)]
            for value in values:
                if value:
                    return value
        return None

    def _first_saramin_field(self, docs: list, element_id: str, labels: tuple[str, ...]) -> str | None:
        """여러 문서에서 id/라벨로 사람인 필드 값을 처음 찾는 것을 반환한다.

        Args:
            docs: 탐색할 lxml 문서 리스트.
            element_id: 우선 탐색할 엘리먼트 id.
            labels: 텍스트 폴백 탐색에 쓸 라벨 후보들.

        Returns:
            처음 찾은 필드 값, 없으면 None.
        """
        for doc in docs:
            value = self._saramin_field_from_node_or_text(doc, element_id, labels)
            if value:
                return value
        return None

    def _first_saramin_location(self, docs: list) -> str | None:
        """사람인 근무지 정보를 필드 또는 요약 영역에서 찾는다.

        Args:
            docs: 탐색할 lxml 문서 리스트.

        Returns:
            근무지 문자열, 없으면 None.
        """
        value = self._first_saramin_field(docs, "template_address", ("근무지", "근무지역"))
        if value:
            return value

        for doc in docs:
            location = self._saramin_summary_location_from_doc(doc)
            if location:
                return location
        return None

    def _saramin_summary_location_from_doc(self, doc) -> str | None:
        """사람인 요약(jv_summary) 영역 텍스트에서 근무지를 정규식으로 찾는다.

        Args:
            doc: 파싱된 lxml 문서.

        Returns:
            근무지 문자열, 없으면 None.
        """
        summary_nodes = doc.xpath('//*[contains(concat(" ", normalize-space(@class), " "), " jv_summary ")]')
        candidates = summary_nodes or [doc]
        for node in candidates:
            text = clean_text(node.text_content())
            match = re.search(
                r"(?:근무지역|근무지)\s*[:：]?\s*(.+?)(?=최저임금|조회수|홈페이지접속|공유하기|신고하기|접수기간|지원방법|$)",
                text,
            )
            if match:
                value = clean_text(match.group(1))
                if value:
                    return value
        return None

    def _first_saramin_application_period(self, docs: list) -> dict[str, str | None]:
        """여러 문서에서 사람인 접수기간(시작/마감일)을 처음 찾아 반환한다.

        Args:
            docs: 탐색할 lxml 문서 리스트.

        Returns:
            start_date/end_date 키를 가진 dict(없으면 둘 다 None).
        """
        for doc in docs:
            value = self._saramin_field_from_node_or_text(doc, "template_applyway_date", ("접수기간",))
            if value:
                return self._saramin_period_value_to_dates(value)

            dates = self._saramin_application_dates_from_doc(doc)
            if dates["start_date"] or dates["end_date"]:
                return dates
        return {"start_date": None, "end_date": None}

    def _saramin_period_value_to_dates(self, value: str) -> dict[str, str | None]:
        """'시작 ~ 마감' 형식의 접수기간 문자열을 시작/마감일로 분리한다.

        Args:
            value: 접수기간 원문 문자열.

        Returns:
            start_date/end_date 키를 가진 dict('~'가 없으면 end_date만 채움).
        """
        if "~" not in value:
            return {"start_date": None, "end_date": value}

        start, end = value.split("~", 1)
        return {"start_date": clean_text(start), "end_date": clean_text(end)}

    def _saramin_application_dates_from_doc(self, doc) -> dict[str, str | None]:
        """사람인 지원방법(jv_howto) 영역에서 시작일/마감일을 추출한다.

        Args:
            doc: 파싱된 lxml 문서.

        Returns:
            start_date/end_date 키를 가진 dict(없으면 둘 다 None).
        """
        date_nodes = doc.xpath('//*[contains(concat(" ", normalize-space(@class), " "), " jv_howto ")]')
        candidates = date_nodes or [doc]
        for node in candidates:
            text = clean_text(node.text_content())
            start = self._saramin_labeled_datetime(text, "시작일")
            end = self._saramin_labeled_datetime(text, "마감일")
            if start or end:
                return {"start_date": start, "end_date": end}
        return {"start_date": None, "end_date": None}

    def _saramin_labeled_datetime(self, text: str, label: str) -> str | None:
        """라벨(시작일/마감일) 뒤의 날짜·시각 또는 상시채용 표기를 찾는다.

        Args:
            text: 검색할 텍스트.
            label: 찾을 라벨(예: 시작일/마감일).

        Returns:
            매칭된 날짜/표기 문자열, 없으면 None.
        """
        match = re.search(
            rf"{re.escape(label)}\s*([0-9]{{4}}[.\-][0-9]{{2}}[.\-][0-9]{{2}}\s+[0-9]{{1,2}}:[0-9]{{2}}|채용시|상시채용)",
            text,
        )
        return match.group(1).strip() if match else None

    def _first_saramin_application_method(self, docs: list) -> str | None:
        """여러 문서에서 사람인 지원/접수 방법을 처음 찾아 반환한다.

        Args:
            docs: 탐색할 lxml 문서 리스트.

        Returns:
            지원방법 문자열, 없으면 None.
        """
        for doc in docs:
            value = self._saramin_field_from_node_or_text(
                doc,
                "template_applyway_apply_types",
                ("접수방법", "지원방법"),
            )
            if value:
                return value

            method = self._saramin_application_method_from_doc(doc)
            if method:
                return method
        return None

    def _saramin_application_method_from_doc(self, doc) -> str | None:
        """사람인 지원방법(jv_howto) 영역 텍스트에서 지원방법을 정규식으로 찾는다.

        Args:
            doc: 파싱된 lxml 문서.

        Returns:
            지원방법 문자열, 없으면 None.
        """
        method_nodes = doc.xpath('//*[contains(concat(" ", normalize-space(@class), " "), " jv_howto ")]')
        candidates = method_nodes or [doc]
        for node in candidates:
            text = clean_text(node.text_content())
            match = re.search(
                r"지원방법\s*[:：]?\s*(.+?)(?=마감일|접수양식|제출서류|전형절차|유의사항|$)",
                text,
            )
            if match:
                value = clean_text(match.group(1))
                if value:
                    return value
        return None

    def _saramin_field_from_node_or_text(self, doc, element_id: str, labels: tuple[str, ...]) -> str | None:
        """id 엘리먼트에서, 없으면 라벨 기반 정규식으로 사람인 필드 값을 찾는다.

        Args:
            doc: 파싱된 lxml 문서.
            element_id: 우선 탐색할 엘리먼트 id.
            labels: 텍스트 폴백에서 찾을 라벨 후보들.

        Returns:
            찾은 필드 값, 없으면 None.
        """
        matches = doc.xpath(f'//*[@id="{element_id}"]')
        if matches:
            value_nodes = matches[0].xpath('.//*[contains(concat(" ", normalize-space(@class), " "), " value ")]')
            raw_value = value_nodes[0].text_content() if value_nodes else matches[0].text_content()
            value = remove_label(raw_value, labels)
            return value or None

        text = clean_text(doc.text_content())
        label_pattern = "|".join(re.escape(label) for label in labels)
        stop_labels = (
            "고용형태",
            "연봉",
            "급여",
            "근무일시",
            "근무지",
            "근무지역",
            "지도보기",
            "접수기간",
            "시작일",
            "마감일",
            "지원방법",
            "접수방법",
            "접수양식",
            "제출서류",
            "전형절차",
            "유의사항",
        )
        stop_pattern = "|".join(re.escape(label) for label in stop_labels if label not in labels)
        match = re.search(
            rf"(?:{label_pattern})\s*[:：]\s*(.+?)(?=(?:{stop_pattern})\s*[:：]?|$)",
            text,
        )
        if not match:
            return None
        return clean_text(match.group(1)) or None

    async def _fetch_saramin_relay_ajax(self, client: httpx.AsyncClient, final_url: str, page_html: str) -> str | None:
        """사람인 relay ajax 엔드포인트를 호출해 추가 상세 HTML을 가져온다.

        Args:
            client: 재사용할 HTTP 클라이언트.
            final_url: 사람인 공고 최종 URL.
            page_html: relay 경로를 찾기 위한 페이지 HTML.

        Returns:
            ajax 응답 HTML, 조건 미충족이거나 실패 시 None.
        """
        if not is_saramin_url(final_url):
            return None

        rec_idx = saramin_rec_idx(final_url)
        if not rec_idx:
            return None

        ajax_url = urljoin(final_url, saramin_request_path(page_html))
        if not is_allowed_job_domain(ajax_url):
            return None

        try:
            response = await client.post(
                ajax_url,
                data={"rec_idx": rec_idx, "rec_seq": "0", "view_type": saramin_view_type(final_url)},
                headers={
                    "Referer": final_url,
                    "X-Requested-With": "XMLHttpRequest",
                    "Origin": "https://www.saramin.co.kr",
                },
            )
            response.raise_for_status()
        except httpx.HTTPError:
            return None

        return response.text
