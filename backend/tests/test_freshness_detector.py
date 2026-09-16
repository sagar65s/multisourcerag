from datetime import UTC, datetime

from app.rag.freshness_detector import freshness_rank, requires_freshness


def test_detects_explicit_and_volatile_freshness_intent() -> None:
    assert requires_freshness("What happened today?")
    assert requires_freshness("Who is the CEO of this company?")
    assert not requires_freshness("Explain binary search")


def test_current_query_penalizes_missing_and_old_dates() -> None:
    now = datetime(2026, 8, 23, tzinfo=UTC)
    assert freshness_rank("2026-08-22", "latest update", now) > freshness_rank("2020-01-01", "latest update", now)
    assert freshness_rank(None, "latest update", now) == 0
    assert freshness_rank("2027-01-01", "latest update", now) == 0
