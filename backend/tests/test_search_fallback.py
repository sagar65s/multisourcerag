import pytest

from app.managers.search_provider_manager import SearchProviderManager
from app.providers.search.base import SearchProvider, SearchResult
from app.providers.search.registry import SearchProviderRegistry


class FailingProvider(SearchProvider):
    name = "first"; priority = 0; enabled = True
    async def search(self, query: str, limit: int) -> list[SearchResult]: raise TimeoutError


class WorkingProvider(SearchProvider):
    name = "second"; priority = 1; enabled = True
    async def search(self, query: str, limit: int) -> list[SearchResult]: return [SearchResult("Official", "https://example.com", "Evidence", provider=self.name)]


@pytest.mark.asyncio
async def test_search_fallback_is_sequential() -> None:
    registry = SearchProviderRegistry(); registry.register(FailingProvider()); registry.register(WorkingProvider())
    provider, results = await SearchProviderManager(registry).search_with_fallback("query", 5)
    assert provider == "second"
    assert results[0].title == "Official"

