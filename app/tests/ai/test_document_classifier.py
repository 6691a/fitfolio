from typing import Any

import pytest
from dependency_injector import providers

from app.ai.classification.document import LangChainDocumentClassifier
from app.ai.classification.document import langchain as classifier_module
from app.config.containers import Container
from app.schemas.documents import DocumentClassification, DocumentKind, DocumentFormat, ParsedDocument, TextInput
from app.services.document import DocumentService


class FakeStructuredLLM:
    config: Any = None

    async def ainvoke(self, messages, config=None):
        self.__class__.config = config
        return DocumentClassification(
            expected_kind=DocumentKind.RESUME,
            detected_kind=DocumentKind.RESUME,
            is_expected=True,
            confidence=0.91,
            failure_reason=None,
        )


class FakeChatGoogleGenerativeAI:
    def __init__(self, **kwargs) -> None:
        self.kwargs = kwargs

    def with_structured_output(self, schema):
        assert schema is DocumentClassification
        return FakeStructuredLLM()


@pytest.mark.asyncio
async def test_langchain_document_classifier_uses_structured_output(monkeypatch):
    monkeypatch.setattr(classifier_module.settings, "GEMINI_API_KEY", "real-test-key")
    monkeypatch.setattr(classifier_module, "ChatGoogleGenerativeAI", FakeChatGoogleGenerativeAI)

    result = await LangChainDocumentClassifier().classify("이력서 본문", DocumentKind.RESUME)

    assert result.is_expected is True
    assert result.detected_kind == DocumentKind.RESUME


@pytest.mark.asyncio
async def test_langchain_document_classifier_passes_langfuse_handler_to_llm(monkeypatch):
    handler = object()
    monkeypatch.setattr(classifier_module.settings, "GEMINI_API_KEY", "real-test-key")
    monkeypatch.setattr(classifier_module, "ChatGoogleGenerativeAI", FakeChatGoogleGenerativeAI)
    container = Container()
    container.langfuse_handler.override(providers.Object(handler))
    container.wire(modules=[classifier_module])

    try:
        await LangChainDocumentClassifier().classify("이력서 본문", DocumentKind.RESUME)
    finally:
        container.unwire()

    assert FakeStructuredLLM.config["callbacks"] == [handler]
    assert FakeStructuredLLM.config["run_name"] == "document_classification"
    assert FakeStructuredLLM.config["metadata"]["expected_kind"] == DocumentKind.RESUME.value


class FakeRejectingClassifier:
    async def classify(self, text: str, expected_kind: DocumentKind) -> DocumentClassification:
        return DocumentClassification(
            expected_kind=expected_kind,
            detected_kind=DocumentKind.JOB_POSTING,
            is_expected=False,
            confidence=0.88,
            failure_reason="이 문서는 이력서가 아니라 채용공고입니다.",
        )


class FakeDocumentsRepository:
    def __init__(self) -> None:
        self.failed: tuple[int, str] | None = None

    async def mark_failed(self, document_id: int, *, error: str) -> None:
        self.failed = (document_id, error)


@pytest.mark.asyncio
async def test_verify_document_kind_marks_failed_when_llm_rejects_document_kind():
    repository = FakeDocumentsRepository()
    parsed = ParsedDocument(
        original_input=TextInput(
            document_type=DocumentKind.RESUME,
            input_type=DocumentFormat.TEXT,
            text="백엔드 개발자 채용공고",
        ),
        extracted_text="백엔드 개발자 채용공고",
        metadata={},
    )

    service = DocumentService(
        documents_repository=repository,  # type: ignore[arg-type]
        document_classifier=FakeRejectingClassifier(),
    )

    accepted = await service.verify_kind(
        document_id=7,
        expected_kind=DocumentKind.RESUME,
        parsed=parsed,
    )

    assert accepted is False
    assert repository.failed == (7, "이 문서는 이력서가 아니라 채용공고입니다.")


class FakeAcceptingClassifier:
    async def classify(self, text: str, expected_kind: DocumentKind) -> DocumentClassification:
        return DocumentClassification(
            expected_kind=expected_kind,
            detected_kind=expected_kind,
            is_expected=True,
            confidence=0.92,
        )


@pytest.mark.asyncio
async def test_verify_document_kind_passes_and_records_classification():
    repository = FakeDocumentsRepository()
    parsed = ParsedDocument(
        original_input=TextInput(
            document_type=DocumentKind.RESUME,
            input_type=DocumentFormat.TEXT,
            text="이력서 본문",
        ),
        extracted_text="이력서 본문",
        metadata={},
    )
    service = DocumentService(
        documents_repository=repository,  # type: ignore[arg-type]
        document_classifier=FakeAcceptingClassifier(),
    )

    accepted = await service.verify_kind(
        document_id=3,
        expected_kind=DocumentKind.RESUME,
        parsed=parsed,
    )

    assert accepted is True
    assert repository.failed is None
    assert parsed.metadata["document_classification"]["is_expected"] is True
