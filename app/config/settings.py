from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str
    GEMINI_API_KEY: str
    UPLOAD_DIR: Path = Path("data/uploads")
    MAX_PDF_BYTES: int = 20 * 1024 * 1024
    REDIS_URL: str = "redis://redis:6379/0"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
