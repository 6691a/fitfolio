import json

import fitz
import pytest
from lxml import html as lxml_html

from app.ai.vision import ImageContent
from app.crawlers import job_postings as crawler_module
from app.crawlers import saramin as saramin_module
from app.crawlers import utils as utils_module
from app.crawlers.saramin import SaraminJobPostingCrawler
from app.config.containers import Container
from app.schemas.documents import DocumentFormat, DocumentKind, JobPostingExtractDebug, UrlInput
from app.services.document import DocumentService, InsufficientJobContentError


def _png_bytes(width: int, height: int) -> bytes:
    pix = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, width, height))
    pix.clear_with(220)
    return pix.tobytes("png")


class FakeResponse:
    def __init__(
        self,
        *,
        text: str = "",
        url: str,
        content: bytes | None = None,
        content_type: str = "text/html; charset=UTF-8",
    ) -> None:
        self.text = text
        self.content = content if content is not None else text.encode("utf-8")
        self.url = url
        self.headers = {"content-type": content_type}

    def raise_for_status(self) -> None:
        return None


class FakeAsyncClient:
    def __init__(self, *args, **kwargs) -> None:
        self.calls: list[tuple[str, str, dict | None]] = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None

    async def get(self, url: str, *args, **kwargs) -> FakeResponse:
        self.calls.append(("GET", url, None))
        if "view-detail" in url:
            return FakeResponse(
                url=url,
                text="""
                <html><body>
                  <main>
                    <h1>채용공고 상세</h1>
                    <section>
                      주요업무는 데이터 피드 운영, 데이터 품질 관리, API 연동 테스트입니다.
                      자격요건은 SQL 활용, 서비스 운영 경험, 이해관계자 커뮤니케이션 역량입니다.
                      우대사항은 Python 데이터 처리 경험, 금융 데이터 이해, 장애 대응 경험입니다.
                      이 문장은 최소 추출 길이를 넘기기 위한 실제 공고 본문 설명입니다.
                      지원자는 반복 운영 업무와 신규 데이터 검증 업무를 함께 수행합니다.
                    </section>
                  </main>
                </body></html>
                """,
            )

        return FakeResponse(
            url=url,
            text="""
            <html><body>
              <script>
                var jv_options = {
                  'requestUrl' : '/zf_user/jobs/relay/view-ajax',
                  'view_type' : "search"
                };
              </script>
              <p>사람인 인공지능 기술 기반으로 맞춤 공고를 추천해드리는 서비스입니다.</p>
            </body></html>
            """,
        )

    async def post(self, url: str, *args, **kwargs) -> FakeResponse:
        data = kwargs.get("data")
        self.calls.append(("POST", url, data))
        assert isinstance(data, dict)
        assert data["rec_idx"] == "54239133"
        assert data["rec_seq"] == "0"
        return FakeResponse(
            url=url,
            text="""
            <div class="wrap_jv_cont">
              <div class="jv_cont jv_detail">
                <h2>상세요강</h2>
                <iframe id="iframe_content_0"
                        src="/zf_user/jobs/relay/view-detail?rec_idx=54239133&rec_seq=0"></iframe>
              </div>
            </div>
            """,
        )


@pytest.mark.asyncio
async def test_saramin_url_fetches_ajax_detail_iframe(monkeypatch):
    monkeypatch.setattr(crawler_module.httpx, "AsyncClient", FakeAsyncClient)

    service = DocumentService(
        documents_repository=None,  # type: ignore[arg-type]
        job_posting_crawler=Container().job_posting_crawler(),
    )
    parsed = await service.url_to_text(
        UrlInput(
            document_type=DocumentKind.JOB_POSTING,
            input_type=DocumentFormat.URL,
            url="https://www.saramin.co.kr/zf_user/jobs/relay/view?rec_idx=54239133&view_type=search",
        )
    )

    assert "주요업무는 데이터 피드 운영" in parsed.extracted_text
    assert "자격요건은 SQL 활용" in parsed.extracted_text


class FakeImagePostingAsyncClient(FakeAsyncClient):
    async def get(self, url: str, *args, **kwargs) -> FakeResponse:
        self.calls.append(("GET", url, None))
        if url.endswith("_recruit.png") or "saraminimage.co.kr/recruit/" in url:
            return FakeResponse(
                url=url,
                content=_png_bytes(860, 1200),
                content_type="image/png",
            )

        if "view-detail" in url:
            return FakeResponse(
                url=url,
                text="""
                <html><body>
                  <div class="user_content">
                    <img alt="백엔드개발자_ver.png"
                         src="https://pds.saramin.co.kr/recruit/recruit/202605/27/2f895d_affb-e6fbe5_recruit.png">
                    <p>
                      근무조건과 채용절차 텍스트가 일부 있지만 핵심 상세요강은 이미지에 있습니다.
                      이 문장은 최소 추출 길이를 넘기기 위해 포함한 iframe 텍스트입니다.
                      실제 상세 내용은 이미지 OCR 후보로 저장되어야 합니다.
                    </p>
                  </div>
                </body></html>
                """,
            )

        return await super().get(url, *args, **kwargs)


class FakeSaraminImageCdnAsyncClient(FakeImagePostingAsyncClient):
    async def get(self, url: str, *args, **kwargs) -> FakeResponse:
        self.calls.append(("GET", url, None))
        if "saraminimage.co.kr/recruit/" in url:
            return FakeResponse(
                url=url,
                content=_png_bytes(860, 1200),
                content_type="image/png",
            )

        if "view-detail" in url:
            return FakeResponse(
                url=url,
                text="""
                <html><body>
                  <div class="user_content">
                    <img alt="2026 상반기 InBody GBD 채용"
                         src="https://www.saraminimage.co.kr/recruit/bbs_recruit26/03_inbody_260617_1.png">
                    <p>
                      채용 공고 상세 텍스트 일부입니다. 실제 상세요강은 사람인 이미지 CDN의 이미지에 있습니다.
                      이 문장은 최소 추출 길이를 넘기기 위해 포함한 iframe 텍스트입니다.
                      이미지 기반 공고는 OCR 후보로 이미지 파일이 저장되어야 합니다.
                    </p>
                  </div>
                </body></html>
                """,
            )

        return await super().get(url, *args, **kwargs)

    async def post(self, url: str, *args, **kwargs) -> FakeResponse:
        data = kwargs.get("data")
        self.calls.append(("POST", url, data))
        assert isinstance(data, dict)
        assert data["rec_idx"] == "54148433"
        return FakeResponse(
            url=url,
            text="""
            <div class="wrap_jv_cont">
              <div class="jv_cont jv_summary">
                <dl>
                  <dt>근무지역</dt><dd>서울 강남구, 충남 천안시</dd>
                </dl>
                <p>최저임금계산에 대한 알림</p>
              </div>
              <div class="jv_cont jv_howto">
                <h2 class="jv_title">접수기간 및 방법</h2>
                <dl>
                  <dt>시작일</dt><dd>2026.06.08 14:00</dd>
                  <dt>마감일</dt><dd>2026.06.29 23:59</dd>
                  <dt>지원방법</dt><dd><a>홈페이지 지원</a></dd>
                </dl>
              </div>
              <div class="jv_cont jv_detail">
                <iframe id="iframe_content_0"
                        src="/zf_user/jobs/relay/view-detail?rec_idx=54148433&rec_seq=0"></iframe>
              </div>
            </div>
            """,
        )


async def fake_relevant_image_content(image_bytes, mime, kind):
    return ImageContent(relevant=True, content="이미지에서 추출한 채용공고 상세 내용입니다.")


async def fake_irrelevant_image_content(image_bytes, mime, kind):
    return ImageContent(relevant=False, content="")


@pytest.mark.asyncio
async def test_saramin_url_saves_images_inside_detail_iframe_with_real_extension(monkeypatch, tmp_path):
    monkeypatch.setattr(crawler_module.httpx, "AsyncClient", FakeImagePostingAsyncClient)
    monkeypatch.setattr(utils_module, "DEBUG_IMAGE_DIR", tmp_path)

    service = DocumentService(
        documents_repository=None,  # type: ignore[arg-type]
        job_posting_crawler=Container().job_posting_crawler(),
    )
    try:
        await service.url_to_text(
            UrlInput(
                document_type=DocumentKind.JOB_POSTING,
                input_type=DocumentFormat.URL,
                url="https://www.saramin.co.kr/zf_user/jobs/relay/view?rec_idx=54239133&view_type=search",
            )
        )
    except InsufficientJobContentError:
        pass

    saved_images = [path for path in tmp_path.glob("url-*") if path.suffix in {".png", ".jpg", ".webp", ".gif"}]
    assert saved_images
    assert all(path.suffix == ".png" for path in saved_images)


@pytest.mark.asyncio
async def test_saramin_url_saves_images_from_saramin_image_cdn(monkeypatch, tmp_path):
    monkeypatch.setattr(crawler_module.httpx, "AsyncClient", FakeSaraminImageCdnAsyncClient)
    monkeypatch.setattr(utils_module, "DEBUG_IMAGE_DIR", tmp_path)
    monkeypatch.setattr(saramin_module, "extract_image_content", fake_relevant_image_content)

    service = DocumentService(
        documents_repository=None,  # type: ignore[arg-type]
        job_posting_crawler=Container().job_posting_crawler(),
    )
    try:
        await service.url_to_text(
            UrlInput(
                document_type=DocumentKind.JOB_POSTING,
                input_type=DocumentFormat.URL,
                url="https://www.saramin.co.kr/zf_user/jobs/relay/pop-view?rec_idx=54148433&t_ref=main",
            )
        )
    except InsufficientJobContentError:
        pass

    saved_images = [path for path in tmp_path.glob("url-*") if path.suffix == ".png"]
    assert saved_images
    selected_files = list(tmp_path.glob("url-saramin-selected-*.json"))
    assert len(selected_files) == 1
    payload = json.loads(selected_files[0].read_text(encoding="utf-8"))
    debug = JobPostingExtractDebug.model_validate(payload)
    assert payload["work_location"] == "서울 강남구, 충남 천안시"
    assert payload["application_start_date"] == "2026.06.08 14:00"
    assert payload["application_end_date"] == "2026.06.29 23:59"
    assert payload["application_method"] == "홈페이지 지원"
    assert "application_period" not in payload
    assert debug.source == "saramin"
    assert debug.image_urls[0].src == "https://www.saraminimage.co.kr/recruit/bbs_recruit26/03_inbody_260617_1.png"
    assert debug.image_urls[0].text == "이미지에서 추출한 채용공고 상세 내용입니다."
    assert "이미지에서 추출한 채용공고 상세 내용입니다." in debug.text


class FakeSaraminSelectedAsyncClient(FakeAsyncClient):
    async def get(self, url: str, *args, **kwargs) -> FakeResponse:
        self.calls.append(("GET", url, None))
        if "view-detail" in url:
            return FakeResponse(
                url=url,
                text="""
                <html><body>
                  <header>사람인 공통 헤더와 광고 영역</header>
                  <div class="user_content">
                    <h1>채용공고 상세</h1>
                    <p>백엔드 개발자는 정산 API와 관리자 서비스를 개발합니다.</p>
                    <h2>주요업무</h2>
                    <p>FastAPI 서비스 운영, 데이터 파이프라인 유지보수, 장애 대응 자동화를 담당합니다.</p>
                    <h2>자격요건</h2>
                    <p>Python 백엔드 개발 경험과 SQL 튜닝 경험이 필요합니다.</p>
                    <p>
                      이 문장은 사람인 선택 본문이 최소 추출 길이를 넘기도록 포함된 상세 설명입니다.
                      지원자는 서비스 안정성과 개발 생산성을 함께 개선하는 업무를 수행합니다.
                    </p>
                    <p id="template_address">• 근무지 : <span class="value">서울 강남구 테헤란로 123</span>연봉 6,000만원</p>
                    <p id="template_applyway_date">접수기간 : <span class="value">2026-06-01 09시 ~ 2026-06-30 18시</span></p>
                    <p id="template_applyway_apply_types">접수방법 : <span class="value">사람인 입사지원</span></p>
                  </div>
                  <footer>추천공고와 푸터 링크</footer>
                </body></html>
                """,
            )

        return await super().get(url, *args, **kwargs)


@pytest.mark.asyncio
async def test_saramin_url_extracts_selected_user_content_and_saves_single_debug_file(monkeypatch, tmp_path):
    monkeypatch.setattr(crawler_module.httpx, "AsyncClient", FakeSaraminSelectedAsyncClient)
    monkeypatch.setattr(utils_module, "DEBUG_IMAGE_DIR", tmp_path)

    parsed = await DocumentService(
        documents_repository=None,  # type: ignore[arg-type]
        job_posting_crawler=Container().job_posting_crawler(),
    ).url_to_text(
        UrlInput(
            document_type=DocumentKind.JOB_POSTING,
            input_type=DocumentFormat.URL,
            url="https://www.saramin.co.kr/zf_user/jobs/relay/view?rec_idx=54239133&view_type=search",
        )
    )

    assert "백엔드 개발자는 정산 API와 관리자 서비스를 개발합니다." in parsed.extracted_text
    assert "FastAPI 서비스 운영" in parsed.extracted_text
    assert "사람인 공통 헤더와 광고 영역" not in parsed.extracted_text
    assert "추천공고와 푸터 링크" not in parsed.extracted_text
    structured = parsed.metadata["job_posting_extract"]
    assert structured["source"] == "saramin"
    assert structured["work_location"] == "서울 강남구 테헤란로 123"
    assert structured["application_start_date"] == "2026-06-01 09시"
    assert structured["application_end_date"] == "2026-06-30 18시"
    assert structured["application_method"] == "사람인 입사지원"
    assert "application_period" not in structured

    selected_files = list(tmp_path.glob("url-saramin-selected-*.json"))
    assert len(selected_files) == 1
    payload = json.loads(selected_files[0].read_text(encoding="utf-8"))
    debug = JobPostingExtractDebug.model_validate(payload)
    assert payload["source"] == "saramin"
    assert "백엔드 개발자는 정산 API와 관리자 서비스를 개발합니다." in payload["text"]
    assert payload["work_location"] == "서울 강남구 테헤란로 123"
    assert payload["application_start_date"] == "2026-06-01 09시"
    assert payload["application_end_date"] == "2026-06-30 18시"
    assert payload["application_method"] == "사람인 입사지원"
    assert "application_period" not in payload
    assert debug.source == "saramin"
    assert payload["image_urls"] == []
    assert not list(tmp_path.glob("url-page-*.html"))
    assert not list(tmp_path.glob("url-saramin-ajax-*.html"))
    assert not list(tmp_path.glob("url-iframe-*.html"))
    assert not list(tmp_path.glob("url-saramin-selected-*.html"))


def test_saramin_location_fallback_stops_before_salary_text():
    doc = lxml_html.fromstring(
        """
        <div class="user_content">
          근무지 : 서울 강서구 화곡로31길 79 우장플렉스연봉 6,000만원• 급여 : 연봉 5,000만원
          접수기간 : 2026-05-11 17시 ~ 채용시 접수방법 : 사람인 입사지원
        </div>
        """
    )

    crawler = SaraminJobPostingCrawler()

    assert (
        crawler._saramin_field_from_node_or_text(  # noqa: SLF001
            doc,
            "template_address",
            ("근무지", "근무지역"),
        )
        == "서울 강서구 화곡로31길 79 우장플렉스"
    )
