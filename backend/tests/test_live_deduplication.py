from app.providers.search.base import SearchResult
from app.services.live_research_service import deduplicate_content


def test_near_duplicate_web_evidence_is_removed() -> None:
    first = SearchResult("Official", "https://official.example/a", "The company announced a new secure research platform for customers worldwide.", authority_score=6)
    second = SearchResult("Copy", "https://copy.example/b", "The company announced a new secure research platform for customers worldwide.", authority_score=2)
    distinct = SearchResult("Analysis", "https://analysis.example/c", "Independent analysts discussed pricing and adoption risks.", authority_score=4)
    result = deduplicate_content([first, second, distinct])
    assert [item.title for item in result] == ["Official", "Analysis"]
