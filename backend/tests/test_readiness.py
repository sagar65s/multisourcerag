from fastapi import Response
import pytest

from app.api.health import readiness
from app.core.config import Settings


class Database:
    async def command(self, value):
        assert value == "ping"


class QdrantClient:
    async def get_collections(self): return []


class Store:
    def __init__(self, _settings): self.client = QdrantClient()


@pytest.mark.asyncio
async def test_readiness_checks_both_private_datastores(monkeypatch):
    monkeypatch.setattr("app.api.health.get_database", lambda: Database())
    monkeypatch.setattr("app.api.health.VectorStore", Store)
    response = Response()
    result = await readiness(response, Settings())
    assert result == {"status": "ready", "checks": {"mongodb": "healthy", "qdrant": "healthy"}}
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_readiness_returns_503_without_exposing_connection_details(monkeypatch):
    class Offline:
        async def command(self, _value): raise RuntimeError("mongodb://secret")
    monkeypatch.setattr("app.api.health.get_database", lambda: Offline())
    monkeypatch.setattr("app.api.health.VectorStore", Store)
    response = Response()
    result = await readiness(response, Settings())
    assert response.status_code == 503
    assert result["checks"]["mongodb"] == "offline"
    assert "secret" not in str(result)
