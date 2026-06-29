import json

import pytest

from app.schemas.documents import DocumentFormat, DocumentKind, JobPostingExtractDebug, UrlInput
from app.crawlers import job_postings as crawler_module
from app.crawlers import utils as utils_module
from app.config.containers import Container
from app.services.document import DocumentService
from app.services.errors import InsufficientJobContentError


class FakeResponse:
    def __init__(self, *, text: str, url: str) -> None:
        self.text = text
        self.content = text.encode("utf-8")
        self.url = url
        self.headers = {"content-type": "text/html; charset=utf-8"}

    def raise_for_status(self) -> None:
        return None


class FakeWantedAsyncClient:
    def __init__(self, *args, **kwargs) -> None:
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None

    async def get(self, url: str, *args, **kwargs) -> FakeResponse:
        return FakeResponse(
            url=url,
            text="""
            <html><body>
              <nav>원티드 사이드바 추천 공고 광고 문구</nav>
              <main class="JobDetail_jobDetail__si4a2">
                <section class="JobContent_descriptionWrapper__RMlfm">
                  <article class="JobDescription_JobDescription__s2Keo">
                    <h2>포지션 상세</h2>
                    <p>FastAPI 백엔드 엔지니어는 데이터 API와 인증 서비스를 개발합니다.</p>
                    <h3>주요업무</h3>
                    <p>서버 환경 구축, WebSocket 스트리밍, RESTful API 리팩토링을 담당합니다.</p>
                    <h3>자격요건</h3>
                    <p>컴퓨터 공학 지식과 2년 이상의 백엔드 실무 경험이 필요합니다.</p>
                    <p>
                      이 포지션은 서비스 안정성과 개발 생산성을 함께 개선하는 역할입니다.
                      채용 공고 본문은 실제 업무 맥락, 협업 방식, 기술 스택, 성장 가능성을 충분히 설명합니다.
                      지원자는 FastAPI 기반 API 개발과 운영 자동화 경험을 바탕으로 제품 개발 전반에 참여합니다.
                    </p>
                  </article>
                </section>
              </main>
              <aside>합격축하금, 추천 채용, 푸터 링크</aside>
            </body></html>
            """,
        )


class FakeWantedNextDataAsyncClient:
    def __init__(self, *args, **kwargs) -> None:
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None

    async def get(self, url: str, *args, **kwargs) -> FakeResponse:
        return FakeResponse(
            url=url,
            text="""
            <html><body>
              <script id="__NEXT_DATA__" type="application/json">
                {
                  "props": {
                    "pageProps": {
                      "initialData": {
                        "position": "FastAPI 백엔드 엔지니어",
                        "intro": "포지션 상세\\n버튼 위에 보이는 기본 소개입니다.",
                        "main_tasks": "주요업무\\nAPI 개발과 WebSocket 스트리밍을 담당합니다.",
                        "requirements": "자격요건\\n2년 이상의 백엔드 실무 경험이 필요합니다.",
                        "preferred_points": "우대사항\\nLitestar, Mojo 등 새로운 환경으로의 이전을 선호하는 성향",
                        "benefits": "혜택 및 복지\\n재택과 원격 근무를 업무 효율을 높이는 무기로 사용합니다.",
                        "hire_rounds": "채용절차\\n서류 전형 후 컬처핏 인터뷰와 직무 역량 인터뷰를 진행합니다."
                      }
                    }
                  }
                }
              </script>
              <article class="JobDescription_JobDescription__s2Keo">
                <h2>포지션 상세</h2>
                <p>버튼 위에 보이는 기본 소개입니다.</p>
                <button>상세 정보 더 보기</button>
              </article>
            </body></html>
            """,
        )


async def fake_job_posting_structured(text, fallback):
    return fallback.model_copy(update={"title": "LLM 정리 포지션", "position": "LLM 정리 포지션"})


async def fake_irrelevant_job_posting_structured(text, fallback):
    return JobPostingExtractDebug(
        source=fallback.source,
        relevant=False,
        failure_reason="채용공고가 아닌 일반 문서입니다.",
        text=text,
    )


@pytest.mark.asyncio
async def test_wanted_url_extracts_selected_job_description_and_saves_debug_file(monkeypatch, tmp_path):
    monkeypatch.setattr(crawler_module.httpx, "AsyncClient", FakeWantedAsyncClient)
    monkeypatch.setattr(utils_module, "DEBUG_IMAGE_DIR", tmp_path)
    monkeypatch.setattr(utils_module, "extract_job_posting_structured", fake_job_posting_structured)

    parsed = await DocumentService(
        documents_repository=None,  # type: ignore[arg-type]
        job_posting_crawler=Container().job_posting_crawler(),
    ).url_to_text(
        UrlInput(
            document_type=DocumentKind.JOB_POSTING,
            input_type=DocumentFormat.URL,
            url="https://www.wanted.co.kr/wd/366125",
        )
    )

    assert "FastAPI 백엔드 엔지니어는 데이터 API와 인증 서비스를 개발합니다." in parsed.extracted_text
    assert "서버 환경 구축, WebSocket 스트리밍" in parsed.extracted_text
    assert "원티드 사이드바 추천 공고 광고 문구" not in parsed.extracted_text
    assert "합격축하금, 추천 채용, 푸터 링크" not in parsed.extracted_text

    debug_files = list(tmp_path.glob("url-wanted-selected-*.html"))
    assert len(debug_files) == 1
    assert "JobDescription_JobDescription" in debug_files[0].read_text(encoding="utf-8")
    selected_json_files = list(tmp_path.glob("url-wanted-selected-*.json"))
    assert len(selected_json_files) == 1
    payload = json.loads(selected_json_files[0].read_text(encoding="utf-8"))
    debug = JobPostingExtractDebug.model_validate(payload)
    assert "application_period" not in payload
    assert debug.source == "wanted"
    assert debug.position == "LLM 정리 포지션"
    assert "FastAPI 백엔드 엔지니어는 데이터 API와 인증 서비스를 개발합니다." in debug.text
    assert debug.html is not None
    assert not list(tmp_path.glob("url-page-*.html"))


@pytest.mark.asyncio
async def test_wanted_url_prefers_next_data_for_hidden_show_more_sections(monkeypatch, tmp_path):
    monkeypatch.setattr(crawler_module.httpx, "AsyncClient", FakeWantedNextDataAsyncClient)
    monkeypatch.setattr(utils_module, "DEBUG_IMAGE_DIR", tmp_path)
    monkeypatch.setattr(utils_module, "extract_job_posting_structured", fake_job_posting_structured)

    parsed = await DocumentService(
        documents_repository=None,  # type: ignore[arg-type]
        job_posting_crawler=Container().job_posting_crawler(),
    ).url_to_text(
        UrlInput(
            document_type=DocumentKind.JOB_POSTING,
            input_type=DocumentFormat.URL,
            url="https://www.wanted.co.kr/wd/366125",
        )
    )

    assert "우대사항" in parsed.extracted_text
    assert "Litestar, Mojo" in parsed.extracted_text
    assert "혜택 및 복지" in parsed.extracted_text
    assert "재택과 원격 근무" in parsed.extracted_text
    assert "채용절차" in parsed.extracted_text
    assert "컬처핏 인터뷰" in parsed.extracted_text
    structured = parsed.metadata["job_posting_extract"]
    assert structured["source"] == "wanted"
    assert structured["position"] == "LLM 정리 포지션"
    assert "우대사항" in structured["text"]
    assert "application_period" not in structured

    assert len(list(tmp_path.glob("url-wanted-next-data-*.json"))) == 1
    selected_json_files = list(tmp_path.glob("url-wanted-selected-*.json"))
    assert len(selected_json_files) == 1
    payload = json.loads(selected_json_files[0].read_text(encoding="utf-8"))
    debug = JobPostingExtractDebug.model_validate(payload)
    assert "application_period" not in payload
    assert debug.source == "wanted"
    assert debug.position == "LLM 정리 포지션"
    assert "우대사항" in debug.text
    assert debug.raw is not None
    assert len(list(tmp_path.glob("url-wanted-selected-*.txt"))) == 1
    assert not list(tmp_path.glob("url-wanted-selected-*.html"))


@pytest.mark.asyncio
async def test_wanted_url_fails_when_llm_says_irrelevant(monkeypatch, tmp_path):
    monkeypatch.setattr(crawler_module.httpx, "AsyncClient", FakeWantedNextDataAsyncClient)
    monkeypatch.setattr(utils_module, "DEBUG_IMAGE_DIR", tmp_path)
    monkeypatch.setattr(
        utils_module,
        "extract_job_posting_structured",
        fake_irrelevant_job_posting_structured,
    )

    try:
        await DocumentService(
            documents_repository=None,  # type: ignore[arg-type]
            job_posting_crawler=Container().job_posting_crawler(),
        ).url_to_text(
            UrlInput(
                document_type=DocumentKind.JOB_POSTING,
                input_type=DocumentFormat.URL,
                url="https://www.wanted.co.kr/wd/366125",
            )
        )
    except InsufficientJobContentError as exc:
        assert "채용공고가 아닌 일반 문서입니다." in str(exc)
    else:
        raise AssertionError("irrelevant job posting should fail")
