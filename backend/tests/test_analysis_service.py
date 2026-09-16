import asyncio

import pytest

from app.core.config import Settings
from app.providers.search.base import SearchResult
from app.services.analysis_service import gather_evidence, research_queries
from app.services.live_research_service import LiveResearchResult


def test_research_queries_are_bounded_and_unique() -> None:
    queries = research_queries("RAG security", 3)
    assert len(queries) == 3
    assert queries[0] == "RAG security"
    assert len(set(queries)) == len(queries)


@pytest.mark.asyncio
async def test_web_research_queries_run_concurrently(monkeypatch) -> None:
    active = 0
    peak = 0

    async def fake_research(_self, query: str) -> LiveResearchResult:
        nonlocal active, peak
        active += 1
        peak = max(peak, active)
        await asyncio.sleep(0)
        active -= 1
        return LiveResearchResult(
            [SearchResult(title=query, url=f"https://example.com/{len(query)}", snippet="Evidence", content="Evidence")],
            "test",
        )

    monkeypatch.setattr("app.services.analysis_service.LiveResearchService.research", fake_research)
    result = await gather_evidence("owner", "RAG security", None, False, True, 3, Settings(environment="test"))
    assert peak > 1
    assert result.citations
