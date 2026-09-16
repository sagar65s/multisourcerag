from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import StrEnum
from typing import AsyncIterator


class ProviderHealth(StrEnum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    RATE_LIMITED = "rate_limited"
    QUOTA_EXHAUSTED = "quota_exhausted"
    OFFLINE = "offline"
    MISCONFIGURED = "misconfigured"
    COOLDOWN = "cooldown"


@dataclass(slots=True)
class ProviderDescriptor:
    name: str
    model: str
    priority: int
    enabled: bool
    health: ProviderHealth = ProviderHealth.HEALTHY
    base_url: str | None = None
    api_key_env_name: str | None = None
    timeout_seconds: int = 45
    retries: int = 1
    rpm: int = 0
    daily_quota: int = 0
    context_size: int = 0
    streaming: bool = True
    vision: bool = False
    tools: bool = False


class LLMProvider(ABC):
    descriptor: ProviderDescriptor

    @abstractmethod
    async def stream(self, messages: list[dict[str, str]]) -> AsyncIterator[str]:
        if False:
            yield ""
