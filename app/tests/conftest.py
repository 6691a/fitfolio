import os

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")
os.environ.setdefault("GEMINI_API_KEY", "test-key")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("AUTH_SECRET_KEY", "test-secret-for-auth-that-is-long-enough")
os.environ.setdefault("AUTH_ACCESS_TOKEN_EXPIRE_MINUTES", "30")
os.environ.setdefault("AUTH_ALGORITHM", "HS256")
