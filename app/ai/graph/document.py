import logging
from typing import Any, cast

from langgraph.graph import END, START, StateGraph

from app.ai.graph.state import DocumentGraphState, DocumentNextSkill
from app.schemas.documents import DocumentKind

logger = logging.getLogger(__name__)


def _route(state: DocumentGraphState) -> DocumentNextSkill:
    """StateGraph conditional edge용 다음 스킬 이름을 반환한다."""
    return cast(DocumentNextSkill, state.get("next_skill", "finish"))


def build_document_graph(service: Any):
    """기존 DocumentService 기능을 LangGraph 노드로 연결한 문서 처리 그래프를 만든다.

    Args:
        service: DocumentService 인스턴스. 순환 import를 피하려고 런타임 객체로 받는다.

    Returns:
        컴파일된 LangGraph 문서 처리 그래프.
    """

    async def load_document(state: DocumentGraphState) -> DocumentGraphState:
        document_id = state["document_id"]
        document = await service._documents_repository.get(document_id)
        if document is None:
            return {"completed": False, "next_skill": "finish"}

        await service._documents_repository.mark_started(document_id)
        return {
            "document": document,
            "document_input": service._build_document_input(document),
            "next_skill": "parse_document",
        }

    async def parse_document(state: DocumentGraphState) -> DocumentGraphState:
        try:
            parsed = await service.parse(state["document_input"])
        except Exception as exc:
            logger.exception("문서 파싱 실패 document_id=%s", state["document_id"])
            return {"error": str(exc), "next_skill": "persist_failed"}
        return {"parsed": parsed, "next_skill": "classify_document"}

    async def classify_document(state: DocumentGraphState) -> DocumentGraphState:
        parsed = state["parsed"]
        document = state["document"]
        accepted = await service.verify_kind(
            document_id=state["document_id"],
            expected_kind=DocumentKind(document.document_type),
            parsed=parsed,
        )
        if not accepted:
            return {"completed": False, "next_skill": "finish"}
        return {"next_skill": "persist_done"}

    async def persist_done(state: DocumentGraphState) -> DocumentGraphState:
        parsed = state["parsed"]
        await service._documents_repository.mark_done(
            state["document_id"],
            extracted_text=parsed.extracted_text,
            metadata=parsed.metadata,
        )
        await service.store_profile(state["document"], parsed, user_id=state["user_id"])
        return {"completed": True, "next_skill": "finish"}

    async def persist_failed(state: DocumentGraphState) -> DocumentGraphState:
        error = state.get("error") or "문서 파싱에 실패했습니다"
        await service._documents_repository.mark_failed(state["document_id"], error=error)
        return {"completed": False, "next_skill": "finish"}

    builder = StateGraph(DocumentGraphState)  # pyrefly: ignore [bad-specialization]
    builder.add_node("load_document", load_document)
    builder.add_node("parse_document", parse_document)
    builder.add_node("classify_document", classify_document)
    builder.add_node("persist_done", persist_done)
    builder.add_node("persist_failed", persist_failed)
    builder.add_edge(START, "load_document")
    builder.add_conditional_edges(
        "load_document",
        _route,
        {
            "parse_document": "parse_document",
            "finish": END,
            "persist_failed": "persist_failed",
        },
    )
    builder.add_conditional_edges(
        "parse_document",
        _route,
        {
            "classify_document": "classify_document",
            "persist_failed": "persist_failed",
            "finish": END,
        },
    )
    builder.add_conditional_edges(
        "classify_document",
        _route,
        {
            "persist_done": "persist_done",
            "finish": END,
            "persist_failed": "persist_failed",
        },
    )
    builder.add_edge("persist_done", END)
    builder.add_edge("persist_failed", END)
    return builder.compile(name="document_processing")


async def run_document_graph(service: Any, *, document_id: int, user_id: int) -> DocumentGraphState:
    """문서 처리 그래프를 실행한다.

    Args:
        service: DocumentService 인스턴스.
        document_id: 처리할 문서 ID.
        user_id: 문서 업로드 사용자 ID.

    Returns:
        최종 LangGraph state.
    """
    graph = build_document_graph(service)
    state = await graph.ainvoke({"document_id": document_id, "user_id": user_id})
    return cast(DocumentGraphState, state)
