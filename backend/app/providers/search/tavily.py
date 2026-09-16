import httpx

from app.providers.search.base import SearchProvider, SearchResult


class TavilyProvider(SearchProvider):
    name = "tavily"
    def __init__(self, api_key: str, priority: int) -> None: self.api_key = api_key; self.priority = priority; self.enabled = bool(api_key)
    async def search(self, query: str, limit: int) -> list[SearchResult]:
        async with httpx.AsyncClient(timeout=httpx.Timeout(20, connect=7)) as client:
            response = await client.post("https://api.tavily.com/search", json={"api_key": self.api_key, "query": query, "search_depth": "advanced", "max_results": limit, "include_answer": False, "include_raw_content": False})
            response.raise_for_status(); data = response.json()
        return [SearchResult(title=str(item.get("title") or item.get("url") or "Source"), url=str(item["url"]), snippet=str(item.get("content") or ""), published_at=item.get("published_date"), provider=self.name) for item in data.get("results", []) if item.get("url")]

