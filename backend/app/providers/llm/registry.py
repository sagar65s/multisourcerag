from app.providers.llm.base import LLMProvider, ProviderDescriptor, ProviderHealth


class LLMProviderRegistry:
    def __init__(self) -> None:
        self._providers: dict[str, LLMProvider] = {}

    def register(self, provider: LLMProvider) -> None:
        self._providers[provider.descriptor.name] = provider

    def ordered(self) -> list[LLMProvider]:
        return sorted((p for p in self._providers.values() if p.descriptor.enabled), key=lambda p: p.descriptor.priority)

    def status(self) -> list[ProviderDescriptor]:
        return [provider.descriptor for provider in sorted(self._providers.values(), key=lambda p: p.descriptor.priority)]

    def mark_failure(self, name: str, rate_limited: bool = False) -> None:
        if name in self._providers:
            self._providers[name].descriptor.health = ProviderHealth.RATE_LIMITED if rate_limited else ProviderHealth.DEGRADED

