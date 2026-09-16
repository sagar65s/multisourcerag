from app.providers.search.base import SearchResult
from app.services.live_research_service import build_live_context


def test_live_context_redacts_secrets_and_numbers_citations() -> None:
    context, citations = build_live_context([SearchResult("Update", "https://example.com/update", "api_key=secret-value-12345", "2026-08-23", authority_score=5)], start_index=3)
    assert "secret-value" not in context
    assert citations[0]["id"] == "S3"
    assert citations[0]["date"] == "2026-08-23"

