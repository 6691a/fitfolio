from typing import Any

import pytest
from dependency_injector import providers

from app.ai import vision as vision_module
from app.ai.vision import ImageContent, extract_image_content
from app.config.containers import Container
from app.schemas.documents import DocumentKind


class FakeStructuredVisionLLM:
    config: Any = None

    async def ainvoke(self, messages, config=None):
        self.__class__.config = config
        return ImageContent(relevant=True, content="이미지 텍스트")


class FakeChatGoogleGenerativeAI:
    def __init__(self, **kwargs) -> None:
        self.kwargs = kwargs

    def with_structured_output(self, schema):
        assert schema is ImageContent
        return FakeStructuredVisionLLM()


@pytest.mark.asyncio
async def test_extract_image_content_passes_langfuse_handler_to_llm(monkeypatch):
    handler = object()
    monkeypatch.setattr(vision_module, "ChatGoogleGenerativeAI", FakeChatGoogleGenerativeAI)
    container = Container()
    container.langfuse_handler.override(providers.Object(handler))
    container.wire(modules=[vision_module])

    try:
        result = await extract_image_content(b"fake-image", "image/png", DocumentKind.JOB_POSTING)
    finally:
        container.unwire()

    assert result == ImageContent(relevant=True, content="이미지 텍스트")
    assert FakeStructuredVisionLLM.config["callbacks"] == [handler]
    assert FakeStructuredVisionLLM.config["run_name"] == "image_content_extraction"
    assert FakeStructuredVisionLLM.config["metadata"]["document_kind"] == DocumentKind.JOB_POSTING.value
