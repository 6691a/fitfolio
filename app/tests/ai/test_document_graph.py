from types import SimpleNamespace

import pytest

from app.ai.graph.document import run_document_graph
from app.schemas.documents import DocumentFormat, DocumentKind, ParsedDocument, TextInput


class FakeDocumentsRepository:
    def __init__(self, document) -> None:
        self.document = document
        self.started: list[int] = []
        self.done: list[tuple[int, str, dict]] = []

    async def get(self, document_id: int):
        assert document_id == self.document.id
        return self.document

    async def mark_started(self, document_id: int) -> None:
        self.started.append(document_id)

    async def mark_done(self, document_id: int, *, extracted_text: str, metadata: dict) -> None:
        self.done.append((document_id, extracted_text, metadata))


class FakeDocumentService:
    def __init__(self) -> None:
        self.document = SimpleNamespace(
            id=7,
            document_type=DocumentKind.RESUME.value,
            format=DocumentFormat.TEXT.value,
            extracted_text="이력서 본문",
        )
        self._documents_repository = FakeDocumentsRepository(self.document)
        self.events: list[str] = []

    def _build_document_input(self, document):
        self.events.append("build_input")
        return TextInput(
            document_type=DocumentKind.RESUME,
            input_type=DocumentFormat.TEXT,
            text=document.extracted_text,
        )

    async def parse(self, document_input):
        self.events.append("parse")
        return ParsedDocument(
            original_input=document_input,
            extracted_text="파싱된 이력서",
            metadata={"resume_extract": {"name": "홍길동", "text": "파싱된 이력서"}},
        )

    async def verify_kind(self, *, document_id: int, expected_kind: DocumentKind, parsed: ParsedDocument) -> bool:
        self.events.append("classify")
        assert document_id == 7
        assert expected_kind == DocumentKind.RESUME
        parsed.metadata["document_classification"] = {"is_expected": True}
        return True

    async def store_profile(self, document, parsed: ParsedDocument, user_id: int) -> None:
        self.events.append("store_profile")
        assert document.id == 7
        assert user_id == 1


@pytest.mark.asyncio
async def test_document_graph_runs_existing_parse_classify_and_store_skills():
    service = FakeDocumentService()

    state = await run_document_graph(service, document_id=7, user_id=1)

    assert service.events == ["build_input", "parse", "classify", "store_profile"]
    assert service._documents_repository.started == [7]
    assert service._documents_repository.done == [
        (
            7,
            "파싱된 이력서",
            {
                "resume_extract": {"name": "홍길동", "text": "파싱된 이력서"},
                "document_classification": {"is_expected": True},
            },
        )
    ]
    assert state["completed"] is True
    assert state["next_skill"] == "finish"
