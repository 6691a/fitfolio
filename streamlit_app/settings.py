from pydantic_settings import BaseSettings


class FSettings(BaseSettings):
    API_BASE_URL: str = "http://localhost:8000"


f_settings = FSettings()
