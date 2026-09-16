import inspect

from app.services.website_fetcher import fetch_html


def test_fetcher_uses_direct_browser_compatible_requests() -> None:
    source = inspect.getsource(fetch_html)
    assert "trust_env=False" in source
    assert '"Sec-Fetch-Mode": "navigate"' in source
    assert "MultiSourceAI/" not in source
