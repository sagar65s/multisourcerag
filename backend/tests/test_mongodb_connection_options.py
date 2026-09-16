from pathlib import Path

import certifi

import pytest

from app.database.mongodb import DatabaseUnavailableError, _client_options, connect_mongodb, get_database, mongo


def test_atlas_srv_connection_uses_verified_certifi_ca_bundle() -> None:
    options = _client_options("mongodb+srv://user:password@example.mongodb.net/app")

    assert options["tls"] is True
    assert options["tlsCAFile"] == certifi.where()
    assert Path(str(options["tlsCAFile"])).is_file()


def test_local_connection_does_not_force_tls() -> None:
    options = _client_options("mongodb://127.0.0.1:27017")

    assert "tls" not in options
    assert "tlsCAFile" not in options


def test_explicit_tls_connection_uses_verified_ca_bundle() -> None:
    options = _client_options("mongodb://example.test:27017/?tls=true")

    assert options["tls"] is True
    assert options["tlsCAFile"] == certifi.where()


def test_unavailable_database_has_controlled_error() -> None:
    previous = mongo.database
    mongo.database = None
    try:
        with pytest.raises(DatabaseUnavailableError, match="reconnecting automatically"):
            get_database()
    finally:
        mongo.database = previous


@pytest.mark.asyncio
async def test_index_failure_does_not_discard_a_healthy_connection(monkeypatch) -> None:
    class Admin:
        async def command(self, value: str) -> dict:
            assert value == "ping"
            return {"ok": 1}

    class Client:
        admin = Admin()

        def __getitem__(self, _name: str) -> object:
            return object()

        def close(self) -> None:
            pass

    async def fail_indexes(_database: object) -> None:
        from pymongo.errors import OperationFailure

        raise OperationFailure("existing index conflict")

    class TestSettings:
        mongodb_uri = "mongodb+srv://user:password@example.mongodb.net/app"
        mongodb_database = "app"

    previous = (mongo.client, mongo.database, mongo.indexes_ready, mongo.last_error)
    mongo.client = None
    mongo.database = None
    mongo.indexes_ready = False
    monkeypatch.setattr("app.database.mongodb.AsyncIOMotorClient", lambda *_args, **_kwargs: Client())
    monkeypatch.setattr("app.database.mongodb._ensure_indexes", fail_indexes)
    try:
        assert await connect_mongodb(TestSettings()) is True
        assert mongo.database is not None
        assert mongo.indexes_ready is False
    finally:
        mongo.client, mongo.database, mongo.indexes_ready, mongo.last_error = previous
