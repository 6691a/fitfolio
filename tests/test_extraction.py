"""PDF 이미지 추출 머지/필터 로직 self-check. 실행: uv run python tests/test_extraction.py

Gemini는 호출하지 않는다 — extract_image_content를 스텁으로 교체해 머지/크기필터만 검증.
"""

import asyncio
import tempfile
from pathlib import Path

import fitz

from app.ai.vision import ImageContent
from app.schemas.documents import DocumentFormat, DocumentKind, FileInput
from app.services import document as document_module
from app.services.document import DocumentService


def _make_pdf(image_size: int) -> str:
    doc = fitz.open()
    page = doc.new_page()
    pix = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, image_size, image_size))
    pix.clear_with(128)
    page.insert_image(fitz.Rect(0, 0, image_size, image_size), pixmap=pix)
    page.insert_text((50, image_size + 30), "native pdf text")
    path = Path(tempfile.mkdtemp()) / "sample.pdf"
    doc.save(path)
    doc.close()
    return str(path)


def _file_input(path: str) -> FileInput:
    return FileInput(
        document_type=DocumentKind.RESUME,
        input_type=DocumentFormat.PDF,
        file_path=path,
        file_name="sample.pdf",
        content_type="application/pdf",
    )


async def _run(path: str, stub: ImageContent) -> tuple[str, int, int, list[str]]:
    calls = 0

    async def fake_extract(image_bytes, mime, kind, langfuse_handler=None):
        nonlocal calls
        calls += 1
        return stub

    async def fake_resume_structured(text, fallback):
        return fallback

    document_module.extract_image_content = fake_extract
    document_module.extract_resume_structured = fake_resume_structured
    service = DocumentService(documents_repository=None)  # type: ignore[arg-type]
    parsed = await service.pdf_to_text(_file_input(path))
    image_texts = parsed.metadata["resume_extract"].get("image_texts", [])
    return parsed.extracted_text, parsed.metadata["image_text_count"], calls, image_texts


def main() -> None:
    big = _make_pdf(200)  # 200x200 > 100x100 임계 → 비전 호출됨
    medium_logo = _make_pdf(160)  # 160x160 회사 로고류 → 스킵
    small = _make_pdf(50)  # 50x50 < 임계 → 스킵

    # (a) 관련 이미지 → 본문에 합쳐짐
    text, count, calls, image_texts = asyncio.run(_run(big, ImageContent(relevant=True, content="image text")))
    assert calls == 1, f"big image should trigger vision call, got {calls}"
    assert "image text" in text and "native pdf text" in text, text
    assert count == 1, count
    assert image_texts == ["image text"], image_texts

    # (b) 비관련 이미지 → 무시
    text, count, calls, image_texts = asyncio.run(_run(big, ImageContent(relevant=False, content="")))
    assert calls == 1
    assert "image text" not in text and count == 0, (text, count)
    assert image_texts == [], image_texts

    # (c) 로고 크기 이미지 → 비전 호출 자체를 스킵
    text, count, calls, image_texts = asyncio.run(_run(medium_logo, ImageContent(relevant=True, content="logo text")))
    assert calls == 0, f"logo-sized image should be skipped, got {calls} calls"
    assert count == 0 and "logo text" not in text, (text, count)
    assert image_texts == [], image_texts

    # (d) 작은 이미지 → 비전 호출 자체를 스킵
    text, count, calls, image_texts = asyncio.run(_run(small, ImageContent(relevant=True, content="should not appear")))
    assert calls == 0, f"small image should be skipped, got {calls} calls"
    assert count == 0 and "should not appear" not in text, (text, count)
    assert image_texts == [], image_texts

    print("OK: pdf image merge + size filter")


if __name__ == "__main__":
    main()
