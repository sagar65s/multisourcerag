from app.providers.search.base import SearchProvider


class SearchProviderRegistry:
    def __init__(self) -> None: self._providers: dict[str, SearchProvider] = {}
    def register(self, provider: SearchProvider) -> None: self._providers[provider.name] = provider
    def ordered(self) -> list[SearchProvider]: return sorted((item for item in self._providers.values() if item.enabled), key=lambda item: item.priority)
    def status(self) -> list[dict]: return [{"name": item.name, "enabled": item.enabled, "priority": item.priority, "rpm": getattr(item, "rpm", 0), "daily_quota": getattr(item, "daily_quota", 0), "api_key_env_name": getattr(item, "api_key_env_name", None)} for item in sorted(self._providers.values(), key=lambda item: item.priority)]
