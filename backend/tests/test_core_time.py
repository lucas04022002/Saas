from datetime import datetime, timedelta, timezone

from app.core.time import to_utc_iso


def test_naive_datetime_is_assumed_utc_and_emitted_with_z():
    assert to_utc_iso(datetime(2026, 9, 11, 19, 45, 0)) == "2026-09-11T19:45:00Z"


def test_aware_utc_datetime_is_emitted_with_z_not_plus_offset():
    assert to_utc_iso(datetime(2026, 9, 11, 19, 45, 0, tzinfo=timezone.utc)) == "2026-09-11T19:45:00Z"


def test_non_utc_aware_datetime_is_converted_to_utc():
    cest = timezone(timedelta(hours=2))
    assert to_utc_iso(datetime(2026, 9, 11, 21, 45, 0, tzinfo=cest)) == "2026-09-11T19:45:00Z"


def test_none_stays_none():
    assert to_utc_iso(None) is None
