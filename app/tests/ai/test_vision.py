from typing import Any

import pytest

from app.ai import vision as vision_module
from app.ai.vision import ImageContent, extract_image_content
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
async def test_extract_image_content_passes_trace_config_to_llm(monkeypatch):
    monkeypatch.setattr(vision_module, "ChatGoogleGenerativeAI", FakeChatGoogleGenerativeAI)

    result = await extract_image_content(b"fake-image", "image/png", DocumentKind.JOB_POSTING)

    assert result == ImageContent(relevant=True, content="이미지 텍스트")
    assert FakeStructuredVisionLLM.config["run_name"] == "image_content_extraction"
    assert FakeStructuredVisionLLM.config["metadata"]["document_kind"] == DocumentKind.JOB_POSTING.value
