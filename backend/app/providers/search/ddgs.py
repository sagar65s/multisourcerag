import asyncio

from app.providers.search.base import SearchProvider, SearchResult


class DDGSProvider(SearchProvider):
    name = "ddgs"
    def __init__(self, priority: int) -> None: self.priority = priority; self.enabled = True
    async def search(self, query: str, limit: int) -> list[SearchResult]:
        def execute() -> list[dict]:
            from ddgs import DDGS
            return list(DDGS().text(query, max_results=limit))
        items = await asyncio.to_thread(execute)
        return [SearchResult(title=str(item.get("title") or item.get("href") or "Source"), url=str(item["href"]), snippet=str(item.get("body") or ""), published_at=item.get("date"), provider=self.name) for item in items if item.get("href")]

