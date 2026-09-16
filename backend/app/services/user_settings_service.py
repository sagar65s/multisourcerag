from datetime import UTC, datetime

from app.database.mongodb import get_database
from app.schemas.account import UserSettingsUpdate, UserSettingsView


DEFAULTS = {"theme": "system", "language": "English"}


def _view(item: dict) -> UserSettingsView:
    return UserSettingsView(
        theme=item.get("theme", DEFAULTS["theme"]),
        language=item.get("language", DEFAULTS["language"]),
        updated_at=item["updated_at"],
    )


async def get_user_settings(owner_id: str) -> UserSettingsView:
    database = get_database()
    item = await database.user_settings.find_one({"owner_id": owner_id})
    if item is not None:
        return _view(item)
    now = datetime.now(UTC)
    await database.user_settings.update_one(
        {"owner_id": owner_id},
        {"$setOnInsert": {"owner_id": owner_id, **DEFAULTS, "created_at": now, "updated_at": now}},
        upsert=True,
    )
    item = await database.user_settings.find_one({"owner_id": owner_id})
    if item is None:
        raise RuntimeError("User settings could not be initialized")
    return _view(item)


async def update_user_settings(owner_id: str, payload: UserSettingsUpdate) -> UserSettingsView:
    changes = payload.model_dump(exclude_none=True)
    now = datetime.now(UTC)
    await get_user_settings(owner_id)
    await get_database().user_settings.update_one(
        {"owner_id": owner_id},
        {"$set": {**changes, "updated_at": now}},
    )
    item = await get_database().user_settings.find_one({"owner_id": owner_id})
    if item is None:
        raise RuntimeError("User settings could not be updated")
    return _view(item)
