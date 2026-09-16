from collections import deque
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser

import httpx

from app.core.config import Settings
from app.loaders.web_loader import ExtractedWebPage, extract_html, normalize_url
from app.schemas.website import CrawlScope
from app.services.website_fetcher import WebsiteFetchError, fetch_html, render_with_playwright
from app.services.github_service import crawl_github_repository, github_repository_parts


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
                final_url, html = await render_with_playwright(current, settings); page = extract_html(final_url, html)
            if page.text.strip():
                pages.append(page)
            else:
                failures.append("The page returned HTML but no readable text")
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code in {403, 429, 503} and settings.enable_playwright_fallback:
                try:
                    final_url, html = await render_with_playwright(current, settings)
                    page = extract_html(final_url, html)
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
        reason = failures[-1] if failures else "No readable public page was returned"
        raise WebsiteFetchError(
            f"{reason}. Confirm the URL opens without login. For a JavaScript-only page, enable Playwright fallback."
        )
    return pages


import httpx
