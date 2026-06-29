from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    GEMINI_API_KEY: str
    REDIS_URL: str
    DATABASE_URL: str
    UPLOAD_DIR: Path = Path("data/uploads")
    MAX_PDF_BYTES: int = 20 * 1024 * 1024
    STRUCTURED_EXTRACT_MODEL: str = "gemini-2.5-flash"
    DOCUMENT_CLASSIFIER_MODEL: str = "gemini-2.5-flash"
    EMBEDDING_MODEL: str = "models/gemini-embedding-001"
    EMBEDDING_DIM: int = 1024
    EMBEDDING_DOCUMENT_TASK_TYPE: str = "RETRIEVAL_DOCUMENT"
    EMBEDDING_QUERY_TASK_TYPE: str = "RETRIEVAL_QUERY"
    TIME_ZONE: str = "Asia/Seoul"
    JOB_POSTING_DEFAULT_TIMEZONE: str = "Asia/Seoul"
    # Langfuse 트레이싱. 키가 비면 핸들러가 None이 되어 트레이싱이 꺼진다.
    LANGFUSE_PUBLIC_KEY: str = ""
    LANGFUSE_SECRET_KEY: str = ""
    LANGFUSE_BASE_URL: str = "http://localhost:3000"
    DOCUMENT_MIN_EXTRACTED_CHARS: int = 200
    DOCUMENT_MAX_EXTRACTED_CHARS: int = 80_000
    DOCUMENT_URL_TIMEOUT_MS: int = 30_000
    DOCUMENT_MIN_IMAGE_PIXELS: int = 200 * 200
    DOCUMENT_MIN_IMAGE_BYTES: int = 5 * 1024
    DOCUMENT_DEBUG_ENABLED: bool = True
    DOCUMENT_DEBUG_IMAGE_SUBDIR: str = "debug_images"
    JOB_IMAGE_MIN_TALL_HEIGHT: int = 1_000
    JOB_IMAGE_MIN_TALL_RATIO: float = 2.5
    SARAMIN_HOST_SUFFIX: str = "saramin.co.kr"
    SARAMIN_IMAGE_HOST_SUFFIX: str = "saraminimage.co.kr"
    SARAMIN_RELAY_AJAX_PATH: str = "/zf_user/jobs/relay/view-ajax"
    WANTED_HOST_SUFFIX: str = "wanted.co.kr"
    BROWSER_HEADLESS: bool = True  # False면 실제 브라우저 창이 뜸(로컬 디버깅용, docker 안에선 화면 없어 의미 없음)
    # 채용공고 URL/이미지 HTTP 요청을 허용할 도메인. env 오버라이드는 JSON 배열로(예: '["saramin.co.kr"]').
    ALLOWED_JOB_DOMAINS: frozenset[str] = frozenset(
        {
            "saramin.co.kr",
            "wanted.co.kr",
            "jobkorea.co.kr",
            "linkedin.com",
            "jumpit.co.kr",
            "rememberapp.co.kr",
        }
    )

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
