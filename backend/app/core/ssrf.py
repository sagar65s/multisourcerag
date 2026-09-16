import ipaddress
import re
import socket
from dataclasses import dataclass
from urllib.parse import urlsplit, urlunsplit

from fastapi import HTTPException, status


def _is_blocked(ip: str) -> bool:
    address = ipaddress.ip_address(ip)
    return any(
        (
            address.is_private,
            address.is_loopback,
            address.is_link_local,
            address.is_multicast,
            address.is_reserved,
            address.is_unspecified,
        )
    )


@dataclass(frozen=True, slots=True)
class ResolvedPublicURL:
    url: str
    addresses: frozenset[str]


async def resolve_public_url(url: str) -> ResolvedPublicURL:
    if len(url) > 2048 or any(ord(character) < 32 for character in url):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="The website URL is invalid or too long")
    parsed = urlsplit(url.strip())
    if parsed.scheme.casefold() not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only public HTTP or HTTPS URLs are allowed")
    if "%" in parsed.hostname:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="IPv6 zone identifiers are not allowed")
    try:
        host = parsed.hostname.rstrip(".").encode("idna").decode("ascii").casefold()
    except UnicodeError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="The website hostname is invalid") from exc
    if not host or len(host) > 253 or any(not label or len(label) > 63 for label in host.split(".")):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="The website hostname is invalid")
    try:
        ipaddress.ip_address(host)
    except ValueError:
        hostname_label = re.compile(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\Z")
        if any(hostname_label.fullmatch(label) is None for label in host.split(".")):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="The website hostname is invalid")
    if parsed.port and parsed.port not in {80, 443}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This URL port is not allowed")
    port = parsed.port or (443 if parsed.scheme.casefold() == "https" else 80)
    try:
        records = await __import__("asyncio").get_running_loop().run_in_executor(None, lambda: socket.getaddrinfo(host, port, type=socket.SOCK_STREAM))
    except socket.gaierror as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Website hostname could not be resolved") from exc
    addresses = frozenset(item[4][0].split("%", 1)[0] for item in records)
    if not addresses or any(_is_blocked(ip) for ip in addresses):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Private or unsafe network destinations are blocked")
    netloc = f"[{host}]" if ":" in host else host
    if parsed.port: netloc = f"{netloc}:{parsed.port}"
    canonical = urlunsplit((parsed.scheme.casefold(), netloc, parsed.path or "/", parsed.query, ""))
    return ResolvedPublicURL(canonical, addresses)


def validate_connection_peer(peer_ip: str, expected: frozenset[str]) -> None:
    normalized = peer_ip.split("%", 1)[0]
    if _is_blocked(normalized) or normalized not in expected:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Website DNS changed to an unsafe destination")


async def validate_public_url(url: str) -> str:
    return (await resolve_public_url(url)).url
