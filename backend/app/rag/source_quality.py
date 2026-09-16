from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from urllib.parse import urlsplit

from app.providers.search.base import SearchResult


def authority_score(url: str) -> int:
    parsed = urlsplit(url); host = (parsed.hostname or "").casefold(); path = parsed.path.casefold(); score = 2
    if host.endswith(".gov") or ".gov." in host: score = 8
    elif any(marker in host for marker in ("who.int", "un.org", "europa.eu", "worldbank.org")): score = 8
    elif host.endswith(".edu") or ".edu." in host or host in {"doi.org", "arxiv.org", "pubmed.ncbi.nlm.nih.gov"}: score = 7
    elif host.startswith("docs.") or any(marker in path for marker in ("/docs", "/documentation", "/research", "/newsroom", "/press-release")): score = 6
    elif any(marker in host for marker in ("reuters.com", "apnews.com", "bbc.com", "nature.com", "science.org")): score = 5
    return score


def parse_date(value: str | None) -> datetime | None:
    if not value: return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00")); return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
    except ValueError:
        try:
            parsed = parsedate_to_datetime(value)
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
        except (TypeError, ValueError): return None


def order_sources(results: list[SearchResult], query: str = "") -> list[SearchResult]:
    from app.rag.freshness_detector import freshness_rank
    for item in results: item.authority_score = authority_score(item.url)
    def quality(item: SearchResult) -> tuple[int, int, int, int]:
        fresh = freshness_rank(item.published_at, query)
        return item.authority_score + fresh, item.authority_score, fresh, min(len(item.snippet), 1000)
    return sorted(results, key=quality, reverse=True)
