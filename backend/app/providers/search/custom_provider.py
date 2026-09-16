import httpx

from app.providers.search.base import SearchProvider, SearchResult


class CustomSearchProvider(SearchProvider):
    def __init__(self, name: str, priority: int, base_url: str, api_key: str, method: str = "POST", query_parameter: str = "query", timeout: int = 20, rpm: int = 0, daily_quota: int = 0, api_key_env_name: str | None = None) -> None:
        self.name = name; self.priority = priority; self.base_url = base_url; self.api_key = api_key; self.method = method.upper(); self.query_parameter = query_parameter; self.timeout = timeout; self.rpm = rpm; self.daily_quota = daily_quota; self.api_key_env_name = api_key_env_name; self.enabled = bool(api_key or api_key_env_name is None)

    async def search(self, query: str, limit: int) -> list[SearchResult]:
        headers = {"Accept": "application/json"}
        if self.api_key: headers["Authorization"] = f"Bearer {self.api_key}"
        async with httpx.AsyncClient(timeout=httpx.Timeout(self.timeout, connect=min(7, self.timeout))) as client:
            if self.method == "GET": response = await client.get(self.base_url, params={self.query_parameter: query, "limit": limit}, headers=headers)
            else: response = await client.post(self.base_url, json={self.query_parameter: query, "limit": limit}, headers=headers)
            response.raise_for_status(); data = response.json()
        raw = data.get("results", data.get("items", [])) if isinstance(data, dict) else []
        return [SearchResult(title=str(item.get("title") or item.get("name") or item.get("url") or "Source"), url=str(item["url"]), snippet=str(item.get("snippet") or item.get("content") or item.get("description") or ""), published_at=item.get("published_at") or item.get("date"), provider=self.name) for item in raw[:limit] if isinstance(item, dict) and item.get("url")]
