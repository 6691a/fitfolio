from pydantic_settings import BaseSettings, SettingsConfigDict


class FSettings(BaseSettings):
    API_BASE_URL: str
    PARSE_POLL_INTERVAL_SECONDS: int

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


f_settings = FSettings()
