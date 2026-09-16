from app.loaders.web_loader import build_content_preview, extract_html, normalize_url


def test_normalize_url_removes_fragment_and_default_port() -> None:
    assert normalize_url("HTTPS://Example.COM:443/docs/#intro") == "https://example.com/docs"


def test_extract_html_removes_scripts_and_separates_links() -> None:
    page = extract_html("https://example.com/", """<html><head><title>Example Product</title><meta name='description' content='Private research'><meta property='article:published_time' content='2026-08-23'></head><body><nav>Noise</nav><main><h1>Secure RAG</h1><p>Evidence first.</p><a href='/docs'>Docs</a><a href='https://other.test/news'>News</a><script>secret()</script></main></body></html>""")
    assert page.title == "Example Product"
    assert page.meta_description == "Private research"
    assert "Evidence first" in page.text
    assert "secret()" not in page.text
    assert page.internal_links == ["https://example.com/docs"]
    assert page.external_links == ["https://other.test/news"]
    assert page.published_at == "2026-08-23"


def test_extract_html_keeps_safe_spa_fallback_and_structured_data() -> None:
    page = extract_html(
        "https://app.example.com/",
        """<html><head><title>Rendered App</title><meta name='description' content='A deployed research dashboard'><script type='application/ld+json'>{"@type":"SoftwareApplication","name":"MultiSource"}</script></head><body><div id='root'></div><noscript>Research reports and document analysis</noscript></body></html>""",
    )
    assert "A deployed research dashboard" in page.text
    assert "Research reports and document analysis" in page.text
    assert "SoftwareApplication" in page.text


def test_build_content_preview_summarizes_extracted_pages() -> None:
    page = extract_html(
        "https://example.com/",
        "<html><head><meta name='description' content='Product documentation'></head><body><main><h1>Features</h1><p>Upload documents and analyze websites.</p></main></body></html>",
    )
    preview = build_content_preview([page])
    assert "Product documentation" in preview
    assert "Upload documents and analyze websites" in preview
