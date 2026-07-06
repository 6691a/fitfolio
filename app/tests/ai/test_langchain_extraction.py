from typing import Any

import pytest
from pydantic import BaseModel

from app.ai.extraction import langchain as extraction_module


class FakeSchema(BaseModel):
    value: str


class FakeStructuredLLM:
    config: Any = None

    async def ainvoke(self, messages, config=None):
        self.__class__.config = config
        return FakeSchema(value="ok")


class FakeChatGoogleGenerativeAI:
    def __init__(self, **kwargs) -> None:
        self.kwargs = kwargs

    def with_structured_output(self, schema):
        assert schema is FakeSchema
        return FakeStructuredLLM()


@pytest.mark.asyncio
async def test_structured_output_passes_trace_config_to_llm(monkeypatch):
    monkeypatch.setattr(extraction_module, "ChatGoogleGenerativeAI", FakeChatGoogleGenerativeAI)

    result = await extraction_module.structured_output(
        FakeSchema,
        "instruction",
        "text",
        {"fallback": True},
    )

    assert result == FakeSchema(value="ok")
    assert FakeStructuredLLM.config["run_name"] == "structured_output"
    assert FakeStructuredLLM.config["metadata"]["schema"] == "FakeSchema"
