import json
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlsplit, urlunsplit

from bs4 import BeautifulSoup


@dataclass(slots=True)
class ExtractedWebPage:
    url: str
    title: str
    meta_description: str | None
    text: str
    headings: list[str] = field(default_factory=list)
    internal_links: list[str] = field(default_factory=list)
    external_links: list[str] = field(default_factory=list)
    published_at: str | None = None
    retrieval_method: str = "direct"


def build_content_preview(pages: list[ExtractedWebPage], limit: int = 1400) -> str:
    parts: list[str] = []
    for page in pages[:4]:
        if page.meta_description:
            parts.append(page.meta_description)
        if page.text:
            parts.append(page.text[:700])
    compact = " ".join(" ".join(part.split()) for part in parts if part.strip())
    return compact[:limit].rstrip()


def normalize_url(url: str) -> str:
    parsed = urlsplit(url)
    host = (parsed.hostname or "").casefold()
    port = parsed.port
    netloc = host if not port or (parsed.scheme == "http" and port == 80) or (parsed.scheme == "https" and port == 443) else f"{host}:{port}"
    path = parsed.path or "/"
    if path != "/": path = path.rstrip("/")
    return urlunsplit((parsed.scheme.casefold(), netloc, path, parsed.query, ""))


def extract_html(url: str, html: str) -> ExtractedWebPage:
    soup = BeautifulSoup(html, "html.parser")
    structured_text: list[str] = []
    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        try:
            payload = json.loads(script.get_text(" ", strip=True))
            compact = json.dumps(payload, ensure_ascii=False)
            if compact:
                structured_text.append(compact[:6000])
        except (TypeError, ValueError):
            continue
    fallback_text = [
        item.get_text(" ", strip=True)
        for item in soup.find_all("noscript")
        if item.get_text(" ", strip=True)
    ]
    navigation_text = [
        item.get_text(" ", strip=True)
        for item in soup.find_all(["nav", "footer"])
        if item.get_text(" ", strip=True)
    ][:12]
    for element in soup(["script", "style", "noscript", "svg", "canvas", "form", "nav", "footer"]):
        element.decompose()
    title = soup.title.get_text(" ", strip=True) if soup.title else urlsplit(url).hostname or url
    meta = soup.find("meta", attrs={"name": lambda value: value and value.casefold() == "description"})
    description = meta.get("content", "").strip() if meta else None
    date_element = soup.find("meta", attrs={"property": lambda value: value and value.casefold() in {"article:published_time", "article:modified_time"}}) or soup.find("meta", attrs={"name": lambda value: value and value.casefold() in {"date", "publish_date", "last-modified"}}) or soup.find("time", datetime=True)
    published_at = (date_element.get("content") or date_element.get("datetime") or "").strip() if date_element else None
    headings = [item.get_text(" ", strip=True) for item in soup.find_all(["h1", "h2", "h3"]) if item.get_text(" ", strip=True)][:80]
    base_host = urlsplit(url).hostname
    internal: set[str] = set(); external: set[str] = set()
    for anchor in soup.find_all("a", href=True):
        candidate = normalize_url(urljoin(url, anchor["href"]))
        parsed = urlsplit(candidate)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname: continue
        (internal if parsed.hostname == base_host else external).add(candidate)
    main = soup.find("main") or soup.find("article") or soup.body or soup
    visible_text = "\n\n".join(line.strip() for line in main.get_text("\n", strip=True).splitlines() if line.strip())
    supporting = [description or "", *navigation_text, *fallback_text, *structured_text]
    text = "\n\n".join(dict.fromkeys(part.strip() for part in [visible_text, *supporting] if part.strip()))
    return ExtractedWebPage(url=url, title=title[:300], meta_description=description[:1000] if description else None, text=text, headings=headings, internal_links=sorted(internal), external_links=sorted(external), published_at=published_at[:100] if published_at else None)
