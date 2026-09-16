from datetime import UTC, datetime
from app.providers.search.base import SearchResult
from app.rag.source_quality import authority_score, order_sources


def test_government_and_documentation_sources_rank_higher() -> None:
    assert authority_score("https://agency.gov/report") > authority_score("https://random.example/post")
    assert authority_score("https://docs.python.org/3/") > authority_score("https://random.example/post")
    ordered = order_sources([SearchResult("Blog", "https://random.example", "x"), SearchResult("Agency", "https://agency.gov", "x")])
    assert ordered[0].title == "Agency"


def test_fresh_reputable_source_can_outrank_stale_source_for_current_query() -> None:
    today = datetime.now(UTC).date().isoformat()
    ordered = order_sources([SearchResult("Old agency", "https://agency.gov/report", "official", "2018-01-01"), SearchResult("Current report", "https://reuters.com/update", "current report", today)], "latest update")
    assert ordered[0].title == "Current report"


def test_future_dated_content_is_not_rewarded() -> None:
    ordered = order_sources([SearchResult("Official", "https://agency.gov/report", "official", "2018-01-01"), SearchResult("Future", "https://reuters.com/update", "future", "2099-01-01")], "latest update")
    assert ordered[0].title == "Official"
