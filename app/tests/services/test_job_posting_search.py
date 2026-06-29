import asyncio
from types import SimpleNamespace

import pytest

from app.ai import embeddings
from app.schemas.documents import DocumentFormat, DocumentKind, ParsedDocument, TextInput
from app.schemas.profiles import JobPostingProfileData
from app.services import document as document_module
from app.services.document import DocumentService
from app.services.errors import EmbeddingUnavailableError
from app.services.profiles import build_job_posting_search_text


def test_build_job_posting_search_text_includes_labeled_fields():
    profile = JobPostingProfileData(
        document_text="본문",
        company_name="무신사",
        title="백엔드 엔지니어",
        location="서울",
        responsibilities=["API 개발", "성능 개선"],
        qualifications=["Python"],
        benefits=[],
    )
    text = build_job_posting_search_text(profile)
    assert "회사명: 무신사" in text
    assert "직무: 백엔드 엔지니어" in text
    assert "주요업무: API 개발, 성능 개선" in text
    assert "자격요건: Python" in text
    assert "혜택" not in text  # 빈 리스트는 제외


class _FakeDocsRepo:
    def __init__(self, existing=None):
        self.existing = existing
        self.created = False
        self.create_url_called = False
        self.found_url = None

    async def find_reusable_by_source_url(self, *, document_type, source_url):
        self.found_url = source_url
        return self.existing

    async def create_url_or_get_reusable(self, *, document_type, source_url):
        self.create_url_called = True
        if self.existing is not None:
            return SimpleNamespace(document=self.existing, created=False)
        return SimpleNamespace(document=SimpleNamespace(id=999), created=True)

    async def create(self, **kwargs):
        self.created = True
        return SimpleNamespace(id=999)


def test_request_parse_url_reuses_existing_done_document():
    repo = _FakeDocsRepo(existing=SimpleNamespace(id=42))
    service = DocumentService(documents_repository=repo)  # type: ignore[arg-type]

    result = asyncio.run(service.request_parse_url(document_type=DocumentKind.JOB_POSTING, url="https://x.com/jobs/7/"))

    assert result == 42
    assert repo.created is False
    assert repo.create_url_called is False
    assert repo.found_url == "https://x.com/jobs/7"  # 정규화됨


def test_request_parse_url_reuses_existing_pending_document():
    repo = _FakeDocsRepo(existing=SimpleNamespace(id=43, status="pending"))
    service = DocumentService(documents_repository=repo)  # type: ignore[arg-type]

    result = asyncio.run(service.request_parse_url(document_type=DocumentKind.JOB_POSTING, url="https://x.com/jobs/7/"))

    assert result == 43
    assert repo.created is False
    assert repo.create_url_called is False


def test_request_parse_url_uses_atomic_create_when_no_reusable_document(monkeypatch):
    delayed_ids = []
    from app.tasks import documents as tasks_module

    monkeypatch.setattr(tasks_module.task_parse_document, "delay", lambda document_id: delayed_ids.append(document_id))
    repo = _FakeDocsRepo(existing=None)
    service = DocumentService(documents_repository=repo)  # type: ignore[arg-type]

    result = asyncio.run(service.request_parse_url(document_type=DocumentKind.JOB_POSTING, url="https://x.com/jobs/7/"))

    assert result == 999
    assert repo.create_url_called is True
    assert repo.created is False
    assert delayed_ids == [999]


class _ConcurrentUrlDocsRepo:
    def __init__(self) -> None:
        self.existing = None
        self.find_calls = 0
        self.create_attempts = 0
        self._both_initial_finds = asyncio.Event()
        self._create_lock = asyncio.Lock()

    async def find_reusable_by_source_url(self, *, document_type, source_url):
        self.find_calls += 1
        if self.find_calls >= 2:
            self._both_initial_finds.set()
        await self._both_initial_finds.wait()
        return self.existing

    async def create_url_or_get_reusable(self, *, document_type, source_url):
        async with self._create_lock:
            if self.existing is not None:
                return SimpleNamespace(document=self.existing, created=False)
            self.create_attempts += 1
            self.existing = SimpleNamespace(id=555, status="pending", source_url=source_url)
            return SimpleNamespace(document=self.existing, created=True)


def test_request_parse_url_concurrent_requests_reuse_same_pending_document(monkeypatch):
    delayed_ids = []
    from app.tasks import documents as tasks_module

    monkeypatch.setattr(tasks_module.task_parse_document, "delay", lambda document_id: delayed_ids.append(document_id))
    repo = _ConcurrentUrlDocsRepo()
    service = DocumentService(documents_repository=repo)  # type: ignore[arg-type]

    async def request_twice():
        return await asyncio.wait_for(
            asyncio.gather(
                service.request_parse_url(document_type=DocumentKind.JOB_POSTING, url="https://x.com/jobs/7/"),
                service.request_parse_url(document_type=DocumentKind.JOB_POSTING, url="https://x.com/jobs/7/"),
            ),
            timeout=1,
        )

    results = asyncio.run(request_twice())

    assert results == [555, 555]
    assert repo.create_attempts == 1
    assert delayed_ids == [555]


class _FakeProfilesRepo:
    def __init__(self, rows):
        self.rows = rows
        self.embedding = None
        self.limit = None

    async def search_job_postings(self, *, embedding, limit):
        self.embedding = embedding
        self.limit = limit
        return self.rows


def test_search_job_postings_maps_rows_to_results(monkeypatch):
    async def fake_embed_query(text):
        return [0.1] * embeddings.EMBEDDING_DIM

    monkeypatch.setattr(document_module, "embed_query", fake_embed_query)
    rows = [
        (SimpleNamespace(document_id=1, company_name="무신사", title="백엔드", source_url="u1"), 0.1),
        (SimpleNamespace(document_id=2, company_name="네이버", title="플랫폼", source_url="u2"), 0.4),
    ]
    service = DocumentService(documents_repository=None, profiles_repository=_FakeProfilesRepo(rows))  # type: ignore[arg-type]

    results = asyncio.run(service.search_job_postings("FastAPI 백엔드", limit=5))

    assert [r.document_id for r in results] == [1, 2]
    assert results[0].company_name == "무신사"
    assert results[0].score == round(1.0 - 0.1, 4)


def test_search_job_postings_raises_when_embedding_unavailable(monkeypatch):
    # 임베딩 실패는 빈 결과로 감추지 않고 503으로 매핑되는 도메인 예외를 던진다.
    async def fake_embed_query(text):
        return None

    monkeypatch.setattr(document_module, "embed_query", fake_embed_query)
    service = DocumentService(documents_repository=None, profiles_repository=_FakeProfilesRepo([]))  # type: ignore[arg-type]

    with pytest.raises(EmbeddingUnavailableError):
        asyncio.run(service.search_job_postings("쿼리"))


class _FakeStoreRepo:
    def __init__(self):
        self.upserted_document_id = None
        self.embedded_document_id = None
        self.embedding: list[float] | None = None

    async def upsert_job_posting_profile(self, *, document_id, profile):
        self.upserted_document_id = document_id
        return SimpleNamespace(document_id=document_id)

    async def set_job_posting_embedding(self, *, document_id, embedding):
        self.embedded_document_id = document_id
        self.embedding = embedding


def test_store_profile_embeds_job_posting(monkeypatch):
    async def fake_embed_document(text):
        return [0.2] * embeddings.EMBEDDING_DIM

    monkeypatch.setattr(document_module, "embed_document", fake_embed_document)
    repo = _FakeStoreRepo()
    service = DocumentService(documents_repository=None, profiles_repository=repo)  # type: ignore[arg-type]

    parsed = ParsedDocument(
        original_input=TextInput(
            document_type=DocumentKind.JOB_POSTING,
            input_type=DocumentFormat.TEXT,
            text="본문",
        ),
        extracted_text="본문",
        metadata={
            "job_posting_extract": {"source": "text", "text": "본문", "company_name": "무신사", "title": "백엔드"}
        },
    )
    document = SimpleNamespace(id=7, document_type="job_posting")

    asyncio.run(service.store_profile(document, parsed))

    assert repo.upserted_document_id == 7
    assert repo.embedded_document_id == 7
    assert repo.embedding is not None
    assert len(repo.embedding) == embeddings.EMBEDDING_DIM
