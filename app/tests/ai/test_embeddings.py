import asyncio

from app.ai import embeddings


class _FakeEmbeddingSettings:
    GEMINI_API_KEY = "real-key"
    EMBEDDING_MODEL = "models/injected-embedding"
    EMBEDDING_DIM = 3
    EMBEDDING_DOCUMENT_TASK_TYPE = "INJECTED_DOCUMENT"
    EMBEDDING_QUERY_TASK_TYPE = "INJECTED_QUERY"


def test_embed_functions_disabled_for_test_key():
    # conftest가 GEMINI_API_KEY=test-key로 설정 → 네트워크 호출 없이 None.
    assert asyncio.run(embeddings.embed_document("백엔드 개발자")) is None
    assert asyncio.run(embeddings.embed_query("백엔드")) is None
    assert asyncio.run(embeddings.embed_document("   ")) is None


def test_embed_document_uses_embedding_settings(monkeypatch):
    calls = []

    class FakeEmbeddings:
        def __init__(self, **kwargs):
            calls.append(kwargs)

        async def aembed_query(self, text):
            assert text == "백엔드 개발자"
            return [0.1, 0.2]

    monkeypatch.setattr(embeddings.settings, "GEMINI_API_KEY", "real-key")
    monkeypatch.setattr(embeddings.settings, "EMBEDDING_MODEL", "models/custom-embedding")
    monkeypatch.setattr(embeddings.settings, "EMBEDDING_DIM", 2)
    monkeypatch.setattr(embeddings.settings, "EMBEDDING_DOCUMENT_TASK_TYPE", "CUSTOM_DOCUMENT")
    monkeypatch.setattr(embeddings, "GoogleGenerativeAIEmbeddings", FakeEmbeddings)

    result = asyncio.run(embeddings.embed_document("  백엔드 개발자  "))

    assert result == [0.1, 0.2]
    assert calls == [
        {
            "model": "models/custom-embedding",
            "google_api_key": "real-key",
            "task_type": "CUSTOM_DOCUMENT",
            "output_dimensionality": 2,
        }
    ]


def test_gemini_embedding_service_uses_injected_settings(monkeypatch):
    calls = []

    class FakeEmbeddings:
        def __init__(self, **kwargs):
            calls.append(kwargs)

        async def aembed_query(self, text):
            assert text == "검색 본문"
            return [0.4, 0.5, 0.6]

    monkeypatch.setattr(embeddings, "GoogleGenerativeAIEmbeddings", FakeEmbeddings)

    service = embeddings.GeminiEmbeddingService(_FakeEmbeddingSettings())
    result = asyncio.run(service.embed_document(" 검색 본문 "))

    assert result == [0.4, 0.5, 0.6]
    assert calls == [
        {
            "model": "models/injected-embedding",
            "google_api_key": "real-key",
            "task_type": "INJECTED_DOCUMENT",
            "output_dimensionality": 3,
        }
    ]


def test_embed_query_uses_query_task_type(monkeypatch):
    calls = []

    class FakeEmbeddings:
        def __init__(self, **kwargs):
            calls.append(kwargs)

        async def aembed_query(self, text):
            return [0.3]

    monkeypatch.setattr(embeddings.settings, "GEMINI_API_KEY", "real-key")
    monkeypatch.setattr(embeddings.settings, "EMBEDDING_MODEL", "models/custom-embedding")
    monkeypatch.setattr(embeddings.settings, "EMBEDDING_DIM", 1)
    monkeypatch.setattr(embeddings.settings, "EMBEDDING_QUERY_TASK_TYPE", "CUSTOM_QUERY")
    monkeypatch.setattr(embeddings, "GoogleGenerativeAIEmbeddings", FakeEmbeddings)

    result = asyncio.run(embeddings.embed_query("백엔드"))

    assert result == [0.3]
    assert calls[0]["task_type"] == "CUSTOM_QUERY"
