from time import monotonic

from app.core.provider_state import provider_state
from app.providers.llm.base import ProviderHealth
from app.providers.search.base import SearchResult
from app.providers.search.registry import SearchProviderRegistry
from app.services.provider_telemetry import record_provider_event


class SearchProvidersUnavailable(RuntimeError): pass


class SearchProviderManager:
    def __init__(self, registry: SearchProviderRegistry) -> None: self.registry = registry
    async def search_with_fallback(self, query: str, limit: int) -> tuple[str, list[SearchResult]]:
        for provider in self.registry.ordered():
            allowed, _ = provider_state.can_attempt("search", provider.name, getattr(provider, "rpm", 0), getattr(provider, "daily_quota", 0))
            if not allowed: continue
            for attempt in range(2):
                started = monotonic()
                try:
                    results = await provider.search(query, limit)
                    if results:
                        provider_state.success("search", provider.name); await record_provider_event("search", provider.name, None, "success", int((monotonic()-started)*1000)); return provider.name, results
                    await record_provider_event("search", provider.name, None, "empty", int((monotonic()-started)*1000)); break
                except Exception as exc:
                    health = ProviderHealth.RATE_LIMITED if "429" in str(exc) else ProviderHealth.DEGRADED
                    provider_state.failure("search", provider.name, health, 60 if health == ProviderHealth.RATE_LIMITED else 20)
                    await record_provider_event("search", provider.name, None, "error", int((monotonic()-started)*1000), type(exc).__name__, health == ProviderHealth.RATE_LIMITED)
                    if attempt == 0 and health != ProviderHealth.RATE_LIMITED: continue
                    break
        raise SearchProvidersUnavailable("No configured search provider returned results")
