import pytest
from fastapi import HTTPException

from app.core.ssrf import resolve_public_url, validate_connection_peer, validate_public_url


@pytest.mark.asyncio
@pytest.mark.parametrize("url", ["file:///etc/passwd", "http://127.0.0.1", "http://169.254.169.254/latest/meta-data", "http://localhost", "ftp://example.com", "data:text/plain,hello", "javascript:alert(1)"])
async def test_blocks_unsafe_urls(url: str) -> None:
    with pytest.raises(HTTPException):
        await validate_public_url(url)


@pytest.mark.asyncio
async def test_mixed_public_private_dns_answer_is_blocked(monkeypatch) -> None:
    monkeypatch.setattr("app.core.ssrf.socket.getaddrinfo", lambda *_args, **_kwargs: [(2, 1, 6, "", ("93.184.216.34", 443)), (2, 1, 6, "", ("10.0.0.4", 443))])
    with pytest.raises(HTTPException):
        await resolve_public_url("https://example.com/path")


@pytest.mark.asyncio
async def test_public_url_is_canonical_and_fragment_removed(monkeypatch) -> None:
    monkeypatch.setattr("app.core.ssrf.socket.getaddrinfo", lambda *_args, **_kwargs: [(2, 1, 6, "", ("93.184.216.34", 443))])
    result = await resolve_public_url("HTTPS://Example.COM./docs#secret")
    assert result.url == "https://example.com/docs"
    assert result.addresses == frozenset({"93.184.216.34"})


def test_dns_rebinding_peer_must_match_validated_address() -> None:
    validate_connection_peer("93.184.216.34", frozenset({"93.184.216.34"}))
    with pytest.raises(HTTPException):
        validate_connection_peer("127.0.0.1", frozenset({"93.184.216.34"}))


@pytest.mark.asyncio
async def test_invalid_hostname_label_is_rejected_before_dns() -> None:
    with pytest.raises(HTTPException):
        await resolve_public_url("https://bad_host.example/")
