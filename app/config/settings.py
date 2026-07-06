from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    GEMINI_API_KEY: str
    REDIS_URL: str
    DATABASE_URL: str
    UPLOAD_DIR: Path
    MAX_PDF_BYTES: int
    STRUCTURED_EXTRACT_MODEL: str
    DOCUMENT_CLASSIFIER_MODEL: str
    TIME_ZONE: str
    JOB_POSTING_DEFAULT_TIMEZONE: str
    DOCUMENT_MIN_EXTRACTED_CHARS: int
    DOCUMENT_MAX_EXTRACTED_CHARS: int
    DOCUMENT_URL_TIMEOUT_MS: int
    DOCUMENT_MIN_IMAGE_PIXELS: int
    DOCUMENT_MIN_IMAGE_BYTES: int
    DOCUMENT_DEBUG_ENABLED: bool
    DOCUMENT_DEBUG_IMAGE_SUBDIR: str
    JOB_IMAGE_MIN_TALL_HEIGHT: int
    JOB_IMAGE_MIN_TALL_RATIO: float
    SARAMIN_HOST_SUFFIX: str
    SARAMIN_IMAGE_HOST_SUFFIX: str
    SARAMIN_RELAY_AJAX_PATH: str
    WANTED_HOST_SUFFIX: str
    AUTH_SECRET_KEY: str
    AUTH_ACCESS_TOKEN_EXPIRE_MINUTES: int
    AUTH_ALGORITHM: str
    # 채용공고 URL/이미지 HTTP 요청을 허용할 도메인. env 오버라이드는 JSON 배열로(예: '["saramin.co.kr"]').
    ALLOWED_JOB_DOMAINS: frozenset[str]

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
