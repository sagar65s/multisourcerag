import httpx
import pytest

from app.core.config import Settings
from app.managers.search_provider_manager import SearchProviderManager
from app.providers.search.base import SearchResult
from app.schemas.website import CrawlScope, WebsiteCreate
from app.services import crawler_service
from app.services.crawler_service import crawl_website, discover_website_from_search, resolve_website_input


def test_website_input_accepts_domain_without_scheme() -> None:
    payload = WebsiteCreate(workspace_id="workspace", url="chatgpt.com")
    assert str(payload.url).startswith("https://chatgpt.com")


@pytest.mark.asyncio
async def test_plain_website_name_resolves_to_public_url(monkeypatch) -> None:
    async def fake_search(self, query: str, limit: int):
        assert '"OpenAI ChatGPT"' in query
        return "ddgs", [
            SearchResult(
                title="ChatGPT - Wikipedia",
                url="https://en.wikipedia.org/wiki/ChatGPT",
                snippet="Encyclopedia entry",
                provider="ddgs",
            ),
            SearchResult(
                title="ChatGPT",
                url="https://chatgpt.com/",
                snippet="Official ChatGPT website",
                provider="ddgs",
            )
        ]

    monkeypatch.setattr(SearchProviderManager, "search_with_fallback", fake_search)
    assert await resolve_website_input("OpenAI ChatGPT", Settings()) == "https://chatgpt.com/"


@pytest.mark.asyncio
async def test_search_fallback_indexes_official_domain_results(monkeypatch) -> None:
    async def fake_search(self, query: str, limit: int):
        assert "site:chatgpt.com" in query
        return "ddgs", [
            SearchResult(
                title="ChatGPT",
                url="https://chatgpt.com/overview",
                snippet="ChatGPT helps people write, learn, create, and solve problems.",
                provider="ddgs",
            ),
            SearchResult(
                title="Unrelated",
                url="https://example.com/",
                snippet="Not about the requested website.",
                provider="ddgs",
            ),
        ]

    monkeypatch.setattr(SearchProviderManager, "search_with_fallback", fake_search)
    pages = await discover_website_from_search("https://chatgpt.com/", Settings())
    assert len(pages) == 1
    assert pages[0].retrieval_method == "search_fallback"
    assert "ChatGPT helps people" in pages[0].text
    assert "was not fetched directly" in pages[0].text


@pytest.mark.asyncio
async def test_http_403_uses_public_search_fallback(monkeypatch) -> None:
    response = httpx.Response(403, request=httpx.Request("GET", "https://chatgpt.com/"))

    async def forbidden(*args, **kwargs):
        raise httpx.HTTPStatusError("forbidden", request=response.request, response=response)

    async def allowed_robots(*args, **kwargs):
        parser = crawler_service.RobotFileParser()
        parser.parse([])
        return parser

    async def fallback(*args, **kwargs):
        return [
            crawler_service.ExtractedWebPage(
                url="https://chatgpt.com/overview",
                title="ChatGPT",
                meta_description="Public summary",
                text="Public information about ChatGPT.",
                retrieval_method="search_fallback",
            )
        ]

    monkeypatch.setattr(crawler_service, "_robots", allowed_robots)
    monkeypatch.setattr(crawler_service, "fetch_html", forbidden)
    monkeypatch.setattr(crawler_service, "discover_website_from_search", fallback)
    pages = await crawl_website("https://chatgpt.com", CrawlScope.SINGLE, [], 0, 1, Settings())
    assert pages[0].retrieval_method == "search_fallback"
