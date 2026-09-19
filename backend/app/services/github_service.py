import base64
import json
import re
from urllib.parse import quote, urlsplit

import httpx

from app.core.config import Settings
from app.loaders.web_loader import ExtractedWebPage, normalize_url
from app.services.website_fetcher import WebsiteFetchError, fetch_html


SAFE_PART = re.compile(r"^[A-Za-z0-9_.-]{1,100}$")


def github_repository_parts(url: str) -> tuple[str, str, list[str]] | None:
    parsed = urlsplit(url)
    if (parsed.hostname or "").casefold() not in {"github.com", "www.github.com"}:
        return None
    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) < 2 or not SAFE_PART.fullmatch(parts[0]) or not SAFE_PART.fullmatch(parts[1].removesuffix(".git")):
        return None
    return parts[0], parts[1].removesuffix(".git"), parts[2:]


def _headers(settings: Settings) -> dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if settings.github_token:
        headers["Authorization"] = f"Bearer {settings.github_token}"
    return headers


async def _json(url: str, settings: Settings) -> dict | list:
    _, text = await fetch_html(url, settings, {"application/json", "application/vnd.github+json"}, _headers(settings))
    try:
        return json.loads(text)
    except ValueError as exc:
        raise WebsiteFetchError("GitHub returned invalid repository data") from exc


async def crawl_github_repository(url: str, settings: Settings) -> list[ExtractedWebPage]:
    parsed = github_repository_parts(url)
    if parsed is None:
        raise WebsiteFetchError("This is not a supported GitHub repository URL")
    owner, repository, tail = parsed
    canonical = f"https://github.com/{owner}/{repository}"

    if len(tail) >= 3 and tail[0] == "blob":
        branch = tail[1]
        path = "/".join(tail[2:])
        raw_url = f"https://raw.githubusercontent.com/{quote(owner)}/{quote(repository)}/{quote(branch)}/{quote(path, safe='/')}"
        _, text = await fetch_html(raw_url, settings, {"text/plain", "text/markdown", "application/octet-stream"})
        return [ExtractedWebPage(url=normalize_url(url), title=f"{repository}/{path}", meta_description=f"GitHub file from {owner}/{repository}", text=text[:240_000], headings=[path], retrieval_method="github_api")]

    api_root = f"https://api.github.com/repos/{quote(owner)}/{quote(repository)}"
    metadata = await _json(api_root, settings)
    if not isinstance(metadata, dict) or not metadata.get("full_name"):
        raise WebsiteFetchError("GitHub repository metadata was unavailable")

    readme_text = ""
    try:
        readme = await _json(f"{api_root}/readme", settings)
        if isinstance(readme, dict) and readme.get("content"):
            readme_text = base64.b64decode(str(readme["content"]), validate=False).decode("utf-8", errors="replace")[:180_000]
    except (WebsiteFetchError, httpx.HTTPError, ValueError):
        pass

    languages: dict = {}
    try:
        language_payload = await _json(f"{api_root}/languages", settings)
        if isinstance(language_payload, dict):
            languages = language_payload
    except (WebsiteFetchError, httpx.HTTPError):
        pass

    paths: list[str] = []
    default_branch = str(metadata.get("default_branch") or "main")
    try:
        tree = await _json(f"{api_root}/git/trees/{quote(default_branch)}?recursive=1", settings)
        if isinstance(tree, dict):
            paths = [str(item.get("path")) for item in tree.get("tree", []) if isinstance(item, dict) and item.get("type") == "blob" and item.get("path")][:300]
    except (WebsiteFetchError, httpx.HTTPError):
        pass

    topics = ", ".join(str(item) for item in metadata.get("topics", [])[:30]) or "Not provided"
    language_summary = ", ".join(f"{name}: {amount} bytes" for name, amount in list(languages.items())[:20]) or str(metadata.get("language") or "Not provided")
    license_data = metadata.get("license") if isinstance(metadata.get("license"), dict) else {}
    details = [
        f"Repository: {metadata.get('full_name')}",
        f"Description: {metadata.get('description') or 'Not provided'}",
        f"Homepage: {metadata.get('homepage') or 'Not provided'}",
        f"Default branch: {default_branch}",
        f"Primary language: {metadata.get('language') or 'Not provided'}",
        f"Languages: {language_summary}",
        f"Topics: {topics}",
        f"License: {license_data.get('spdx_id') or license_data.get('name') or 'Not provided'}",
        f"Stars: {metadata.get('stargazers_count', 0)}",
        f"Forks: {metadata.get('forks_count', 0)}",
        f"Open issues: {metadata.get('open_issues_count', 0)}",
        f"Created: {metadata.get('created_at') or 'Not provided'}",
        f"Updated: {metadata.get('updated_at') or 'Not provided'}",
        f"Last pushed: {metadata.get('pushed_at') or 'Not provided'}",
    ]
    if paths:
        details.extend(["Repository files:", *paths])
    if readme_text:
        details.extend(["README:", readme_text])
    description = str(metadata.get("description") or f"Public GitHub repository {owner}/{repository}")
    return [
        ExtractedWebPage(
            url=canonical,
            title=str(metadata.get("full_name")),
            meta_description=description[:1000],
            text="\n".join(details),
            headings=["Repository details", "Languages", "Repository files", "README"],
            internal_links=[canonical, f"{canonical}/tree/{default_branch}"],
            external_links=[str(metadata.get("homepage"))] if metadata.get("homepage") else [],
            published_at=str(metadata.get("updated_at") or "")[:100] or None,
            retrieval_method="github_api",
        )
    ]
