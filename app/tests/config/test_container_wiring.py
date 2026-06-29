import pytest

from app.config.containers import Container
from app.ai.classification.document import LangChainDocumentClassifier
from app.crawlers.job_postings import JobPostingCrawler
from app.schemas.documents import DocumentFormat, DocumentKind, UrlInput
from app.services.document import DocumentService


def test_container_injects_job_posting_crawler_into_document_service():
    service = Container().document_service()

    assert isinstance(service._job_posting_crawler, JobPostingCrawler)  # noqa: SLF001


def test_container_provides_langchain_document_classifier():
    classifier = Container().document_classifier()

    assert isinstance(classifier, LangChainDocumentClassifier)


def test_container_provides_cache():
    from redis.asyncio import Redis

    assert isinstance(Container().cache().client, Redis)


@pytest.mark.asyncio
async def test_document_service_url_parse_requires_container_injected_crawler():
    service = DocumentService(documents_repository=None)  # type: ignore[arg-type]

    with pytest.raises(RuntimeError, match="Container.job_posting_crawler"):
        await service.url_to_text(
            UrlInput(
                document_type=DocumentKind.JOB_POSTING,
                input_type=DocumentFormat.URL,
                url="https://www.wanted.co.kr/wd/1",
            )
        )
