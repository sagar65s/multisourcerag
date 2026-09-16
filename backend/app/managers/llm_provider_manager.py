from collections.abc import AsyncIterator
from time import monotonic

import httpx

from app.providers.llm.registry import LLMProviderRegistry
from app.providers.llm.base import ProviderHealth
from app.core.provider_state import provider_state
from app.services.provider_telemetry import record_provider_event


class AllProvidersUnavailable(RuntimeError):
    pass


class LLMProviderManager:
    def __init__(self, registry: LLMProviderRegistry) -> None:
        self.registry = registry

    async def stream_with_fallback(self, messages: list[dict[str, str]]) -> AsyncIterator[tuple[str, str]]:
        failures: list[str] = []
        for provider in self.registry.ordered():
            descriptor = provider.descriptor
            allowed, health = provider_state.can_attempt("llm", descriptor.name, descriptor.rpm, descriptor.daily_quota)
            if not allowed:
                descriptor.health = health; failures.append(descriptor.name); continue
            for attempt in range(descriptor.retries + 1):
                emitted = False; output_chars = 0; started = monotonic()
                try:
                    async for chunk in provider.stream(messages):
                        emitted = True; output_chars += len(chunk)
                        yield descriptor.name, chunk
                    provider_state.success("llm", descriptor.name); descriptor.health = ProviderHealth.HEALTHY
                    await record_provider_event("llm", descriptor.name, descriptor.model, "success", int((monotonic() - started) * 1000), output_chars=output_chars)
                    return
                except Exception as exc:
                    failure_health, cooldown = classify_failure(exc)
                    descriptor.health = failure_health; provider_state.failure("llm", descriptor.name, failure_health, cooldown)
                    await record_provider_event("llm", descriptor.name, descriptor.model, "error", int((monotonic() - started) * 1000), type(exc).__name__, failure_health == ProviderHealth.RATE_LIMITED, output_chars)
                    if emitted: raise AllProvidersUnavailable("Generation was interrupted after output began") from exc
                    if attempt < descriptor.retries and failure_health not in {ProviderHealth.RATE_LIMITED, ProviderHealth.QUOTA_EXHAUSTED, ProviderHealth.MISCONFIGURED}: continue
                    break
            failures.append(descriptor.name)
        raise AllProvidersUnavailable(f"No configured AI provider completed the request ({', '.join(failures) or 'none enabled'})")

    async def generate_with_fallback(self, messages: list[dict[str, str]]) -> tuple[str, str]:
        provider_name = ""; parts: list[str] = []
        async for provider_name, chunk in self.stream_with_fallback(messages): parts.append(chunk)
        return provider_name, "".join(parts)


def classify_failure(exc: Exception) -> tuple[ProviderHealth, int]:
    if isinstance(exc, httpx.HTTPStatusError):
        code = exc.response.status_code
        body = exc.response.text.casefold()[:1000]
        if code == 429 and "quota" in body: return ProviderHealth.QUOTA_EXHAUSTED, 3600
        if code == 429: return ProviderHealth.RATE_LIMITED, 60
        if code in {400, 401, 403, 404, 422}: return ProviderHealth.MISCONFIGURED, 300
        if code >= 500: return ProviderHealth.OFFLINE, 45
    text = str(exc).casefold()
    if "context" in text and ("length" in text or "window" in text): return ProviderHealth.DEGRADED, 5
    if isinstance(exc, (httpx.TimeoutException, TimeoutError)): return ProviderHealth.DEGRADED, 30
    return ProviderHealth.DEGRADED, 20
