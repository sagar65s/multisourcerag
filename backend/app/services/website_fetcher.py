import asyncio
from urllib.parse import urljoin

import httpx

from app.core.config import Settings
from app.core.ssrf import resolve_public_url, validate_connection_peer, validate_public_url


class WebsiteFetchError(RuntimeError):
    pass


_RETRYABLE_STATUS_CODES = {408, 425, 429, 500, 502, 503, 504}


async def fetch_html(url: str, settings: Settings, allowed_media_types: set[str] | None = None, extra_headers: dict[str, str] | None = None) -> tuple[str, str]:
    target = await resolve_public_url(url); current = target.url
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,text/plain;q=0.8,*/*;q=0.5",
        "Accept-Language": "en-US,en;q=0.9,ta;q=0.7,hi;q=0.6",
        "Cache-Control": "no-cache",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Upgrade-Insecure-Requests": "1",
    }
    if extra_headers:
        headers.update(extra_headers)
    # Direct connections keep SSRF peer validation meaningful and prevent a
    # stale HTTP_PROXY/HTTPS_PROXY environment variable from breaking every URL.
    async with httpx.AsyncClient(
        follow_redirects=False,
        timeout=settings.website_request_timeout_seconds,
        headers=headers,
        trust_env=False,
    ) as client:
        for _ in range(settings.website_redirect_limit + 1):
            target = await resolve_public_url(current); current = target.url
            redirected = False
            for attempt in range(3):
                async with client.stream("GET", current) as response:
                    network_stream = response.extensions.get("network_stream")
                    peer = network_stream.get_extra_info("server_addr") if network_stream and hasattr(network_stream, "get_extra_info") else None
                    if not peer: raise WebsiteFetchError("Website connection peer could not be validated")
                    validate_connection_peer(str(peer[0]), target.addresses)
                    if response.status_code in {301, 302, 303, 307, 308}:
                        location = response.headers.get("location")
                        if not location: raise WebsiteFetchError("Website returned an invalid redirect")
                        current = await validate_public_url(urljoin(current, location))
                        redirected = True
                        break
                    if response.status_code in _RETRYABLE_STATUS_CODES and attempt < 2:
                        retry_after = response.headers.get("retry-after", "")
                        delay = min(float(retry_after), 4.0) if retry_after.isdigit() else 0.75 * (attempt + 1)
                        await response.aclose()
                        await asyncio.sleep(delay)
                        continue
                    response.raise_for_status()
                    media_type = response.headers.get("content-type", "").split(";", 1)[0].casefold()
                    allowed = allowed_media_types or {"text/html", "application/xhtml+xml"}
                    if media_type not in allowed: raise WebsiteFetchError("Website response has an unsupported content type")
                    declared = int(response.headers.get("content-length", "0") or 0)
                    if declared > settings.website_max_response_bytes: raise WebsiteFetchError("Website response is too large")
                    content = bytearray()
                    async for chunk in response.aiter_bytes():
                        content.extend(chunk)
                        if len(content) > settings.website_max_response_bytes: raise WebsiteFetchError("Website response is too large")
                    return current, bytes(content).decode(response.encoding or "utf-8", errors="replace")
            if redirected:
                continue
        raise WebsiteFetchError("Website exceeded the redirect limit")


async def render_with_playwright(url: str, settings: Settings) -> tuple[str, str]:
    if not settings.enable_playwright_fallback:
        raise WebsiteFetchError("JavaScript rendering is disabled")
    from playwright.async_api import async_playwright
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        context = await browser.new_context(service_workers="block")
        page = await context.new_page()
        async def guard(route):
            try:
                await validate_public_url(route.request.url)
                if route.request.resource_type in {"image", "media", "font"}: await route.abort()
                else: await route.continue_()
            except Exception:
                await route.abort()
        await page.route("**/*", guard)
        try:
            await page.goto(await validate_public_url(url), wait_until="domcontentloaded", timeout=settings.website_request_timeout_seconds * 1000)
            final_url = await validate_public_url(page.url)
            html = await page.content()
            if len(html.encode()) > settings.website_max_response_bytes: raise WebsiteFetchError("Rendered website response is too large")
            return final_url, html
        finally:
            await context.close(); await browser.close()
