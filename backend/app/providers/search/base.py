from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(slots=True)
class SearchResult:
    title: str
    url: str
    snippet: str
    published_at: str | None = None
    provider: str = ""
    authority_score: int = 0
    content: str | None = None


class SearchProvider(ABC):
    name: str
    priority: int
    enabled: bool

    @abstractmethod
    async def search(self, query: str, limit: int) -> list[SearchResult]: ...

