from pydantic_settings import BaseSettings


class FSettings(BaseSettings):
    API_BASE_URL: str = "http://localhost:8000"
    PARSE_POLL_INTERVAL_SECONDS: int = 10


f_settings = FSettings()
