from datetime import UTC, datetime

from app.utils import normalize_url, parse_datetime_to_utc, strip_html_tags


def test_strip_html_tags_removes_tags_and_entities():
    assert strip_html_tags("<p>주요 <b>업무</b> 개발</p>") == "주요 업무 개발"
    assert strip_html_tags("A&amp;B") == "A&B"


def test_normalize_url_lowercases_host_and_strips_trailing_slash_and_fragment():
    assert normalize_url("HTTPS://Www.Example.com/Job/123/#frag") == "https://www.example.com/Job/123"
    assert normalize_url("https://x.com/a?b=1") == "https://x.com/a?b=1"


def test_parse_datetime_to_utc_converts_korean_recruiting_time_with_timezone():
    assert parse_datetime_to_utc("2026-05-27 08시", default_timezone="Asia/Seoul") == datetime(
        2026, 5, 26, 23, 0, tzinfo=UTC
    )
    assert parse_datetime_to_utc("2026-06-26 24시", default_timezone="Asia/Seoul") == datetime(
        2026, 6, 26, 15, 0, tzinfo=UTC
    )


def test_parse_datetime_to_utc_uses_configurable_default_timezone_for_naive_values():
    assert parse_datetime_to_utc("2026-06-01 09:00", default_timezone="UTC") == datetime(2026, 6, 1, 9, 0, tzinfo=UTC)
