import asyncio
import re
from datetime import UTC, datetime

from app.core.config import Settings
from app.loaders.web_loader import extract_html, normalize_url
from app.managers.search_provider_manager import SearchProviderManager
from app.providers.search.base import SearchResult
from app.providers.search.factory import build_search_registry
from app.rag.source_quality import order_sources
from app.core.privacy import redact_secrets
from app.services.reranker_service import _cross_encoder
from app.services.website_fetcher import fetch_html


class LiveResearchResult:
    def __init__(self, results: list[SearchResult], provider: str) -> None: self.results = results; self.provider = provider


async def _enrich(item: SearchResult, settings: Settings) -> SearchResult:
    try:
        final_url, html = await fetch_html(item.url, settings); page = extract_html(final_url, html)
        item.url = final_url; item.title = page.title or item.title; item.content = page.text[:12000]; item.published_at = item.published_at or page.published_at
    except Exception:
        item.content = item.snippet
    return item


def deduplicate_content(items: list[SearchResult]) -> list[SearchResult]:
    kept: list[SearchResult] = []; fingerprints: list[set[str]] = []
    for item in items:
        tokens = set(re.findall(r"[a-z0-9]+", (item.content or item.snippet).casefold()))
        duplicate = False
        for previous in fingerprints:
            union = tokens | previous
            if union and len(tokens & previous) / len(union) >= 0.82:
                duplicate = True; break
        if not duplicate:
            kept.append(item); fingerprints.append(tokens)
    return kept


class LiveResearchService:
    def __init__(self, settings: Settings) -> None: self.settings = settings
    async def research(self, query: str) -> LiveResearchResult:
        provider, raw = await SearchProviderManager(build_search_registry(self.settings)).search_with_fallback(query, self.settings.search_results_limit)
        unique: dict[str, SearchResult] = {}
        for item in raw:
            try: unique.setdefault(normalize_url(item.url), item)
            except Exception: continue
        ordered = order_sources(list(unique.values()), query)
        enriched = await asyncio.gather(*[_enrich(item, self.settings) for item in ordered[: self.settings.live_content_fetch_limit]])
        candidates = deduplicate_content(order_sources([item for item in enriched if (item.content or item.snippet).strip()], query))
        try:
            scores = await asyncio.to_thread(_cross_encoder(self.settings.reranker_model).predict, [(query, item.content or item.snippet) for item in candidates])
            candidates = [item for _, item in sorted(zip(scores, candidates, strict=True), key=lambda pair: float(pair[0]), reverse=True)]
        except Exception: pass
        return LiveResearchResult(candidates[: self.settings.reranked_evidence_limit], provider)


def build_live_context(results: list[SearchResult], start_index: int = 1) -> tuple[str, list[dict]]:
    sections: list[str] = []; citations: list[dict] = []
    for offset, item in enumerate(results, start=start_index):
        source_id = f"S{offset}"; passage, _ = redact_secrets((item.content or item.snippet)[:3500])
        sections.append(f"[{source_id}] Live web source: {item.title}; URL: {item.url}; Date: {item.published_at or 'Not provided'}\nUNTRUSTED WEB EVIDENCE:\n{passage}")
        citations.append({"id": source_id, "source_type": "web", "title": item.title, "url": item.url, "date": item.published_at, "retrieved_at": datetime.now(UTC).date().isoformat(), "passage": passage, "authority": item.authority_score})
    return "\n\n".join(sections), citations
