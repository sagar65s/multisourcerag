import pytest

from app.core.config import Settings
from app.services import github_service
from app.services.github_service import crawl_github_repository, github_repository_parts


def test_github_repository_url_is_recognized() -> None:
    assert github_repository_parts("https://github.com/openai/openai-python") == (
        "openai",
        "openai-python",
        [],
    )
    assert github_repository_parts("https://example.com/openai/openai-python") is None


@pytest.mark.asyncio
async def test_github_repository_builds_detailed_index(monkeypatch) -> None:
    async def fake_json(url: str, _settings: Settings):
        if url.endswith("/readme"):
            import base64

            return {"content": base64.b64encode(b"# SDK\nInstall and usage details").decode()}
        if url.endswith("/languages"):
            return {"Python": 9000, "Shell": 500}
        if "/git/trees/" in url:
            return {"tree": [{"type": "blob", "path": "src/client.py"}, {"type": "blob", "path": "README.md"}]}
        return {
            "full_name": "openai/openai-python",
            "description": "Official Python library",
            "default_branch": "main",
            "language": "Python",
            "topics": ["sdk", "api"],
            "license": {"spdx_id": "Apache-2.0"},
            "stargazers_count": 99,
            "forks_count": 12,
            "open_issues_count": 3,
            "created_at": "2020-01-01T00:00:00Z",
            "updated_at": "2026-01-01T00:00:00Z",
            "pushed_at": "2026-01-01T00:00:00Z",
        }

    monkeypatch.setattr(github_service, "_json", fake_json)
    pages = await crawl_github_repository("https://github.com/openai/openai-python", Settings())
    assert len(pages) == 1
    assert pages[0].title == "openai/openai-python"
    assert "Official Python library" in pages[0].text
    assert "Apache-2.0" in pages[0].text
    assert "src/client.py" in pages[0].text
    assert "Install and usage details" in pages[0].text

