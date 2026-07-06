import os

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")
os.environ.setdefault("GEMINI_API_KEY", "test-key")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("UPLOAD_DIR", "data/test-uploads")
os.environ.setdefault("MAX_PDF_BYTES", "20971520")
os.environ.setdefault("STRUCTURED_EXTRACT_MODEL", "gemini-2.5-flash")
os.environ.setdefault("DOCUMENT_CLASSIFIER_MODEL", "gemini-2.5-flash")
os.environ.setdefault("TIME_ZONE", "Asia/Seoul")
os.environ.setdefault("JOB_POSTING_DEFAULT_TIMEZONE", "Asia/Seoul")
os.environ.setdefault("DOCUMENT_MIN_EXTRACTED_CHARS", "200")
os.environ.setdefault("DOCUMENT_MAX_EXTRACTED_CHARS", "80000")
os.environ.setdefault("DOCUMENT_URL_TIMEOUT_MS", "30000")
os.environ.setdefault("DOCUMENT_MIN_IMAGE_PIXELS", "40000")
os.environ.setdefault("DOCUMENT_MIN_IMAGE_BYTES", "5120")
os.environ.setdefault("DOCUMENT_DEBUG_ENABLED", "true")
os.environ.setdefault("DOCUMENT_DEBUG_IMAGE_SUBDIR", "debug_images")
os.environ.setdefault("JOB_IMAGE_MIN_TALL_HEIGHT", "1000")
os.environ.setdefault("JOB_IMAGE_MIN_TALL_RATIO", "2.5")
os.environ.setdefault("SARAMIN_HOST_SUFFIX", "saramin.co.kr")
os.environ.setdefault("SARAMIN_IMAGE_HOST_SUFFIX", "saraminimage.co.kr")
os.environ.setdefault("SARAMIN_RELAY_AJAX_PATH", "/zf_user/jobs/relay/view-ajax")
os.environ.setdefault("WANTED_HOST_SUFFIX", "wanted.co.kr")
os.environ.setdefault("AUTH_SECRET_KEY", "test-secret-for-auth-that-is-long-enough")
os.environ.setdefault("AUTH_ACCESS_TOKEN_EXPIRE_MINUTES", "30")
os.environ.setdefault("AUTH_ALGORITHM", "HS256")
os.environ.setdefault(
    "ALLOWED_JOB_DOMAINS",
    '["saramin.co.kr","wanted.co.kr","jobkorea.co.kr","linkedin.com","jumpit.co.kr","rememberapp.co.kr"]',
)
os.environ.setdefault("API_BASE_URL", "http://localhost:8000")
os.environ.setdefault("PARSE_POLL_INTERVAL_SECONDS", "10")

os.makedirs(
    os.path.join(os.environ["UPLOAD_DIR"], os.environ["DOCUMENT_DEBUG_IMAGE_SUBDIR"]),
    exist_ok=True,
)
