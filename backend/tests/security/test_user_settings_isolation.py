import pytest
from pydantic import ValidationError

from app.schemas.account import UserSettingsUpdate
from app.services.user_settings_service import get_user_settings, update_user_settings


class SettingsCollection:
    def __init__(self) -> None: self.items: dict[str, dict] = {}
    async def find_one(self, query: dict): return self.items.get(query["owner_id"])
    async def update_one(self, query: dict, update: dict, upsert: bool = False):
        owner_id = query["owner_id"]
        item = self.items.setdefault(owner_id, {})
        if not item: item.update(update.get("$setOnInsert", {}))
        item.update(update.get("$set", {}))


class Database:
    def __init__(self) -> None: self.user_settings = SettingsCollection()


@pytest.mark.asyncio
async def test_user_settings_are_created_and_updated_per_owner(monkeypatch) -> None:
    database = Database()
    monkeypatch.setattr("app.services.user_settings_service.get_database", lambda: database)
    initial = await get_user_settings("user-a")
    changed = await update_user_settings("user-a", UserSettingsUpdate(language="Tamil"))
    other = await get_user_settings("user-b")
    assert initial.language == "English"
    assert changed.language == "Tamil"
    assert other.language == "English"
    assert set(database.user_settings.items) == {"user-a", "user-b"}


def test_empty_or_invalid_settings_update_is_rejected() -> None:
    with pytest.raises(ValidationError): UserSettingsUpdate()
    with pytest.raises(ValidationError): UserSettingsUpdate(language="Unsupported")
