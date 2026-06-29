import pytest

from app.ai.extraction import job_posting as jp
from app.schemas.documents import JobPostingExtractDebug


@pytest.mark.asyncio
async def test_extract_sends_only_plain_text_to_ai(monkeypatch):
    captured: dict = {}

    async def fake_structured_output(schema, instruction, text, fallback):
        captured["text"] = text
        captured["fallback"] = fallback
        return JobPostingExtractDebug(source="saramin", text=text)

    monkeypatch.setattr(jp, "structured_output", fake_structured_output)
    monkeypatch.setattr(jp.settings, "GEMINI_API_KEY", "real-key")

    fallback = JobPostingExtractDebug(
        source="saramin",
        text="<div>본문 <span>텍스트</span></div>",
        html="<html><body>...</body></html>",
        raw={"main_tasks": "<b>업무</b>"},
    )
    await jp.extract_job_posting_structured("<p>공고 <b>본문</b></p>", fallback)

    # 태그가 제거된 실제 글자만 AI에 전달된다.
    assert captured["text"] == "공고 본문"
    assert captured["fallback"]["text"] == "본문 텍스트"
    # html/raw(태그 덩어리)는 fallback에서 빠진다.
    assert "html" not in captured["fallback"]
    assert "raw" not in captured["fallback"]
