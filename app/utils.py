import html as html_lib
import re
from datetime import UTC, datetime, timedelta
from urllib.parse import urlsplit, urlunsplit
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

PERMANENT_RECRUITING_ENDS_AT = datetime(9999, 12, 31, 23, 59, 59, tzinfo=UTC)
PERMANENT_RECRUITING_TOKENS = ("상시", "채용시", "수시")


def clean_text(text: str) -> str:
    """연속 공백을 하나로 줄이고 앞뒤 공백을 제거한다.

    Args:
        text: 정리할 텍스트.

    Returns:
        공백이 정리된 텍스트.
    """
    return re.sub(r"\s+", " ", text).strip()


def strip_html_tags(text: str) -> str:
    """HTML 태그를 제거하고 엔티티를 해제한 뒤 공백을 정리한다.

    AI에 넘기기 전 마크업을 걷어내 실제 글자만 남기는 용도다.

    Args:
        text: 태그가 섞여 있을 수 있는 텍스트.

    Returns:
        태그·엔티티가 제거되고 공백이 정리된 텍스트.
    """
    # ponytail: 추출 텍스트용 단순 태그 제거 — 완전한 HTML 파서가 필요해지면 lxml로 교체
    without_tags = re.sub(r"<[^>]+>", " ", text)
    return clean_text(html_lib.unescape(without_tags))


def normalize_url(url: str) -> str:
    """중복 판별용으로 URL을 정규화한다.

    스킴·호스트는 소문자로, fragment는 제거하고 경로 끝 슬래시를 정리한다.

    Args:
        url: 정규화할 URL.

    Returns:
        정규화된 URL.
    """
    parts = urlsplit(url.strip())
    path = parts.path.rstrip("/") or parts.path
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), path, parts.query, ""))


def parse_datetime_to_utc(
    value: datetime | str | None,
    *,
    default_timezone: str,
    allow_permanent: bool = False,
) -> datetime | None:
    """문자열/일시 값을 UTC timezone-aware datetime으로 변환한다.

    Args:
        value: ISO 문자열, 국내 채용공고 날짜 문자열, datetime 또는 None.
        default_timezone: timezone 정보가 없는 값에 적용할 IANA timezone 이름.
        allow_permanent: 상시/채용시/수시 표기를 9999년 종료일로 변환할지 여부.

    Returns:
        UTC timezone-aware datetime 또는 파싱 불가 시 None.
    """
    timezone = ZoneInfo(default_timezone)
    if isinstance(value, datetime):
        return _to_utc(value, timezone)
    if not isinstance(value, str) or not value.strip():
        return None

    normalized = value.strip()
    if allow_permanent and is_permanent_recruiting(normalized):
        return PERMANENT_RECRUITING_ENDS_AT

    parsed = _parse_datetime(normalized, timezone)
    return _to_utc(parsed, timezone) if parsed else None


def serialize_datetime_in_timezone(value: datetime | None, *, timezone: str) -> str | None:
    """응답 직렬화용으로 datetime을 지정 timezone의 ISO 문자열로 변환한다.

    Args:
        value: DB/내부 모델에서 사용하는 datetime. naive 값은 UTC로 간주한다.
        timezone: 응답에 사용할 IANA timezone 이름.

    Returns:
        지정 timezone으로 변환된 ISO 8601 문자열 또는 None.
    """
    if value is None:
        return None
    if value == PERMANENT_RECRUITING_ENDS_AT:
        return value.isoformat().replace("+00:00", "Z")
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(ZoneInfo(resolve_timezone_name(timezone))).isoformat()


def resolve_timezone_name(value: str | None, *, fallback: str = "UTC") -> str:
    """IANA timezone 이름을 검증하고, 유효하지 않으면 fallback을 반환한다.

    Args:
        value: 우선 사용할 timezone 이름.
        fallback: value가 비었거나 유효하지 않을 때 사용할 timezone 이름.

    Returns:
        ZoneInfo가 인식할 수 있는 timezone 이름.
    """
    for candidate in (value, fallback, "UTC"):
        if not isinstance(candidate, str) or not candidate.strip():
            continue
        normalized = candidate.strip()
        try:
            ZoneInfo(normalized)
        except ZoneInfoNotFoundError:
            continue
        return normalized
    return "UTC"


def is_permanent_recruiting(value: str) -> bool:
    """문자열이 상시 채용 계열 표기인지 확인한다."""
    return any(token in value for token in PERMANENT_RECRUITING_TOKENS)


def _parse_datetime(value: str, timezone: ZoneInfo) -> datetime | None:
    """AI ISO 문자열 또는 국내 채용공고 날짜 문자열을 datetime으로 파싱한다."""
    iso_value = value.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(iso_value)
    except ValueError:
        pass

    korean_hour = re.search(
        r"(?P<year>\d{4})[.\-](?P<month>\d{2})[.\-](?P<day>\d{2})\s+"
        r"(?P<hour>\d{1,2})시(?:\s*(?P<minute>\d{1,2})분?)?",
        value,
    )
    if korean_hour:
        hour = int(korean_hour.group("hour"))
        minute = int(korean_hour.group("minute") or 0)
        parsed = datetime(
            int(korean_hour.group("year")),
            int(korean_hour.group("month")),
            int(korean_hour.group("day")),
            0 if hour == 24 else hour,
            minute,
            tzinfo=timezone,
        )
        return parsed + timedelta(days=1) if hour == 24 else parsed

    for fmt in ("%Y.%m.%d %H:%M", "%Y-%m-%d %H:%M", "%Y.%m.%d", "%Y-%m-%d"):
        try:
            parsed = datetime.strptime(value, fmt)
        except ValueError:
            continue
        return parsed.replace(tzinfo=timezone)
    return None


def _to_utc(value: datetime, timezone: ZoneInfo) -> datetime:
    """naive datetime은 기본 timezone으로 간주하고 UTC aware datetime으로 변환한다."""
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone)
    return value.astimezone(UTC)
