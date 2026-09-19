from collections import deque
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser

import httpx

from app.core.config import Settings
from app.loaders.web_loader import ExtractedWebPage, extract_html, normalize_url
from app.managers.search_provider_manager import SearchProviderManager, SearchProvidersUnavailable
from app.providers.search.base import SearchResult
from app.providers.search.factory import build_search_registry
from app.schemas.website import CrawlScope
from app.services.website_fetcher import WebsiteFetchError, fetch_html, render_with_playwright
from app.services.github_service import crawl_github_repository, github_repository_parts


def _normalized_host(value: str) -> str:
    host = (urlsplit(value).hostname or "").casefold().rstrip(".")
    return host.removeprefix("www.")


async def discover_website_from_search(url: str, settings: Settings, limit: int = 8) -> list[ExtractedWebPage]:
    """Build an honest, citable fallback from public search summaries.

    Some public sites deliberately return 403 to automated clients.  We do not
    bypass that control.  Instead, we index search-visible summaries and label
    them so answers never imply that the protected page was fetched directly.
    """

    normalized = normalize_url(url)
    host = _normalized_host(normalized)
    if not host:
        raise WebsiteFetchError("Website hostname is invalid")
    query = f'site:{host} "{host}" official website overview features about'
    try:
        provider, results = await SearchProviderManager(build_search_registry(settings)).search_with_fallback(query, max(4, min(limit * 2, 16)))
    except SearchProvidersUnavailable as exc:
        raise WebsiteFetchError("Direct access was blocked and public search was unavailable") from exc

    official: list[tuple[SearchResult, str]] = []
    related: list[tuple[SearchResult, str]] = []
    seen: set[str] = set()
    for result in results:
        try:
            candidate = normalize_url(result.url)
        except (TypeError, ValueError):
            continue
        parsed = urlsplit(candidate)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname or candidate in seen:
            continue
        seen.add(candidate)
        candidate_host = _normalized_host(candidate)
        if candidate_host == host or candidate_host.endswith(f".{host}"):
            official.append((result, candidate))
        elif host in f"{result.title} {result.snippet} {result.url}".casefold():
            related.append((result, candidate))

    selected = (official or related)[:limit]
    pages: list[ExtractedWebPage] = []
    for position, (result, candidate) in enumerate(selected, start=1):
        title = " ".join(str(result.title or candidate).split())[:300]
        snippet = " ".join(str(result.snippet or "").split())
        if not title and not snippet:
            continue
        same_site = _normalized_host(candidate) == host or _normalized_host(candidate).endswith(f".{host}")
        evidence_kind = "official-domain search result" if same_site else "public search result mentioning this website"
        text = (
            f"Website requested: {normalized}\n"
            f"Website domain: {host}\n"
            f"Evidence type: {evidence_kind}. The protected page was not fetched directly.\n"
            f"Result title: {title}\n"
            f"Result URL: {candidate}\n"
            f"Public search summary: {snippet or 'No summary was provided.'}"
        )
        pages.append(
            ExtractedWebPage(
                url=candidate,
                title=title or host,
                meta_description=snippet[:1000] or f"Public information about {host}",
                text=text,
                headings=[title or f"Search result {position}"],
                internal_links=[candidate] if same_site else [],
                external_links=[] if same_site else [candidate],
                published_at=result.published_at,
                retrieval_method="search_fallback",
            )
        )
    if not pages:
        raise WebsiteFetchError("Direct access was blocked and public search returned no relevant website information")
    return pages


async def _robots(base_url: str, settings: Settings) -> RobotFileParser:
    parsed = urlsplit(base_url); robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"; parser = RobotFileParser(); parser.set_url(robots_url)
    try:
        _, text = await fetch_html(robots_url, settings, {"text/plain", "text/html", "application/octet-stream"})
        parser.parse(text.splitlines())
    except Exception:
        parser.parse([])
    return parser


async def crawl_website(url: str, scope: CrawlScope, selected_urls: list[str], max_depth: int, max_pages: int, settings: Settings) -> list[ExtractedWebPage]:
    start = normalize_url(url); origin = urlsplit(start).hostname; hard_limit = min(max_pages, settings.website_hard_max_pages)
    if github_repository_parts(start):
        try:
            return await crawl_github_repository(start, settings)
        except (WebsiteFetchError, httpx.HTTPError, ValueError):
            # Public API limits or transient GitHub API failures fall back to
            # the normal secure HTML crawler below.
            pass
    robots = await _robots(start, settings)
    initial = [(start, 0)] if scope != CrawlScope.SELECTED else [(normalize_url(item), 0) for item in [url, *selected_urls]]
    queue = deque(initial); visited: set[str] = set(); pages: list[ExtractedWebPage] = []; failures: list[str] = []
    while queue and len(pages) < hard_limit:
        current, depth = queue.popleft()
        if current in visited or urlsplit(current).hostname != origin: continue
        visited.add(current)
        if not robots.can_fetch("MultiSourceAIResearchBot", current):
            failures.append("The website's robots.txt does not allow this page to be indexed")
            continue
        try:
            final_url, html = await fetch_html(current, settings)
            page = extract_html(final_url, html)
            if len(page.text) < 180 and settings.enable_playwright_fallback:
                final_url, html = await render_with_playwright(current, settings); page = extract_html(final_url, html); page.retrieval_method = "browser"
            if page.text.strip():
                pages.append(page)
            else:
                failures.append("The page returned HTML but no readable text")
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code in {403, 429, 503} and settings.enable_playwright_fallback:
                try:
                    final_url, html = await render_with_playwright(current, settings)
                    page = extract_html(final_url, html); page.retrieval_method = "browser"
                    if page.text.strip():
                        pages.append(page)
                        if scope == CrawlScope.SINGLE:
                            break
                        continue
                except Exception as browser_exc:
                    failures.append((str(browser_exc).strip() or f"Website returned HTTP {exc.response.status_code}")[:180])
                    continue
            failures.append(f"Website returned HTTP {exc.response.status_code}")
            continue
        except (httpx.TimeoutException, TimeoutError):
            failures.append("Website request timed out")
            continue
        except (httpx.HTTPError, WebsiteFetchError, ValueError) as exc:
            failures.append((str(exc).strip() or "Website connection failed")[:180])
            continue
        if scope == CrawlScope.FULL and depth < max_depth:
            for link in page.internal_links:
                if link not in visited: queue.append((link, depth + 1))
        if scope == CrawlScope.SINGLE: break
    if not pages:
        try:
            return await discover_website_from_search(start, settings, hard_limit)
        except WebsiteFetchError as fallback_error:
            reason = failures[-1] if failures else "No readable public page was returned"
            raise WebsiteFetchError(f"{reason}. {fallback_error}") from fallback_error
    return pages


import httpx
