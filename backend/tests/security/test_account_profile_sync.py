from datetime import UTC, datetime

import pytest

from app.core.security import AuthenticatedUser
from app.services.account_profile_service import get_account_profile, sync_account_session


class Users:
    def __init__(self) -> None:
        self.items: dict[str, dict] = {}

    async def find_one(self, query: dict, projection: dict | None = None):
        item = self.items.get(query["uid"])
        if item is None or projection is None: return item
        return {key: item[key] for key in projection if key in item}

    async def update_one(self, query: dict, update: dict, upsert: bool = False):
        current = self.items.setdefault(query["uid"], {})
        if not current: current.update(update.get("$setOnInsert", {}))
        current.update(update.get("$set", {}))
        for key, value in update.get("$inc", {}).items(): current[key] = current.get(key, 0) + value


class Database:
    def __init__(self) -> None: self.users = Users()


@pytest.mark.asyncio
async def test_account_sync_uses_verified_claims_and_audits_each_auth_session_once(monkeypatch) -> None:
    database = Database(); audits: list[tuple] = []
    async def audit(*args, **kwargs): audits.append((args, kwargs))
    monkeypatch.setattr("app.services.account_profile_service.get_database", lambda: database)
    monkeypatch.setattr("app.services.account_profile_service.audit_event", audit)
    user = AuthenticatedUser(uid="user-a", email="a@example.com", is_admin=False, auth_time=123, display_name="A", photo_url="https://example.com/a.png", provider="google.com", email_verified=True)
    first = await sync_account_session(user)
    second = await sync_account_session(user)
    fetched = await get_account_profile(user)
    assert first.uid == second.uid == fetched.uid == "user-a"
    assert first.email_verified and first.provider == "google.com"
    assert database.users.items["user-a"]["login_count"] == 1
    assert len(audits) == 1 and audits[0][0][1] == "login"
    assert isinstance(database.users.items["user-a"]["created_at"], datetime)
