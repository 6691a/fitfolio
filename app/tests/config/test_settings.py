from app.config.settings import Settings


def test_document_extraction_settings_can_be_loaded_from_env(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")
    monkeypatch.setenv("DOCUMENT_MIN_EXTRACTED_CHARS", "123")
    monkeypatch.setenv("DOCUMENT_MAX_EXTRACTED_CHARS", "456")
    monkeypatch.setenv("DOCUMENT_URL_TIMEOUT_MS", "789")
    monkeypatch.setenv("DOCUMENT_MIN_IMAGE_PIXELS", "100")
    monkeypatch.setenv("JOB_IMAGE_MIN_TALL_HEIGHT", "2000")
    monkeypatch.setenv("JOB_IMAGE_MIN_TALL_RATIO", "3.5")
    monkeypatch.setenv("DOCUMENT_MIN_IMAGE_BYTES", "9000")
    monkeypatch.setenv("DOCUMENT_DEBUG_ENABLED", "false")
    monkeypatch.setenv("DOCUMENT_DEBUG_IMAGE_SUBDIR", "debug_test")
    monkeypatch.setenv("SARAMIN_HOST_SUFFIX", "example-saramin.co.kr")
    monkeypatch.setenv("SARAMIN_IMAGE_HOST_SUFFIX", "example-image.co.kr")
    monkeypatch.setenv("SARAMIN_RELAY_AJAX_PATH", "/custom/ajax")
    monkeypatch.setenv("WANTED_HOST_SUFFIX", "example-wanted.co.kr")
    monkeypatch.setenv("BROWSER_HEADLESS", "false")
    monkeypatch.setenv("EMBEDDING_MODEL", "models/test-embedding")
    monkeypatch.setenv("EMBEDDING_DIM", "512")
    monkeypatch.setenv("EMBEDDING_DOCUMENT_TASK_TYPE", "CUSTOM_DOCUMENT")
    monkeypatch.setenv("EMBEDDING_QUERY_TASK_TYPE", "CUSTOM_QUERY")
    monkeypatch.setenv("JOB_POSTING_DEFAULT_TIMEZONE", "UTC")
    monkeypatch.setenv("TIME_ZONE", "Asia/Tokyo")

    settings = Settings(_env_file=None)

    assert settings.DOCUMENT_MIN_EXTRACTED_CHARS == 123
    assert settings.DOCUMENT_MAX_EXTRACTED_CHARS == 456
    assert settings.DOCUMENT_URL_TIMEOUT_MS == 789
    assert settings.DOCUMENT_MIN_IMAGE_PIXELS == 100
    assert settings.JOB_IMAGE_MIN_TALL_HEIGHT == 2000
    assert settings.JOB_IMAGE_MIN_TALL_RATIO == 3.5
    assert settings.DOCUMENT_MIN_IMAGE_BYTES == 9000
    assert settings.DOCUMENT_DEBUG_ENABLED is False
    assert settings.DOCUMENT_DEBUG_IMAGE_SUBDIR == "debug_test"
    assert settings.SARAMIN_HOST_SUFFIX == "example-saramin.co.kr"
    assert settings.SARAMIN_IMAGE_HOST_SUFFIX == "example-image.co.kr"
    assert settings.SARAMIN_RELAY_AJAX_PATH == "/custom/ajax"
    assert settings.WANTED_HOST_SUFFIX == "example-wanted.co.kr"
    assert settings.BROWSER_HEADLESS is False
    assert settings.EMBEDDING_MODEL == "models/test-embedding"
    assert settings.EMBEDDING_DIM == 512
    assert settings.EMBEDDING_DOCUMENT_TASK_TYPE == "CUSTOM_DOCUMENT"
    assert settings.EMBEDDING_QUERY_TASK_TYPE == "CUSTOM_QUERY"
    assert settings.JOB_POSTING_DEFAULT_TIMEZONE == "UTC"
    assert settings.TIME_ZONE == "Asia/Tokyo"


def test_fastapi_startup_prepares_debug_image_dir(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    from app import main

    monkeypatch.setattr(main.settings, "DOCUMENT_DEBUG_ENABLED", True)
    monkeypatch.setattr(main.settings, "UPLOAD_DIR", tmp_path)
    monkeypatch.setattr(main.settings, "DOCUMENT_DEBUG_IMAGE_SUBDIR", "debug_images")

    with TestClient(main.app):
        pass

    assert (tmp_path / "debug_images").is_dir()


def test_document_service_does_not_export_debug_dir_initializer():
    from app.services import document as document_module

    assert not hasattr(document_module, "ensure_debug_image_dir")


def test_debug_save_does_not_create_debug_dir(tmp_path, monkeypatch):
    from app.services import document as document_module

    debug_dir = tmp_path / "debug_images"
    monkeypatch.setattr(document_module, "_DEBUG_IMAGE_DIR", debug_dir)
    monkeypatch.setattr(document_module.settings, "DOCUMENT_DEBUG_ENABLED", True)

    try:
        document_module.DocumentService._save_debug_text("debug", "sample", "txt")
    except FileNotFoundError:
        pass

    assert not debug_dir.exists()
