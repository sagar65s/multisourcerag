from datetime import UTC, datetime

from app.core.security import AuthenticatedUser
from app.database.mongodb import get_database
from app.schemas.account import AccountView
from app.services.audit_service import audit_event


def _view(item: dict, user: AuthenticatedUser) -> AccountView:
    return AccountView(
        uid=user.uid,
        email=item.get("email"),
        display_name=item.get("display_name"),
        photo_url=item.get("photo_url"),
        provider=item.get("provider"),
        email_verified=bool(item.get("email_verified")),
        is_admin=user.is_admin,
        created_at=item["created_at"],
        last_login_at=item["last_login_at"],
    )


async def sync_account_session(user: AuthenticatedUser) -> AccountView:
    database = get_database()
    existing = await database.users.find_one({"uid": user.uid}, {"last_auth_time": 1, "created_at": 1})
    now = datetime.now(UTC)
    is_new_login = existing is None or int(existing.get("last_auth_time") or 0) != user.auth_time
    update: dict = {
        "$set": {
            "email": user.email,
            "display_name": user.display_name,
            "photo_url": user.photo_url,
            "provider": user.provider,
            "email_verified": user.email_verified,
            "last_login_at": now,
            "last_auth_time": user.auth_time,
            "updated_at": now,
        },
        "$setOnInsert": {"uid": user.uid, "created_at": now},
    }
    if is_new_login:
        update["$inc"] = {"login_count": 1}
    await database.users.update_one({"uid": user.uid}, update, upsert=True)
    item = await database.users.find_one({"uid": user.uid})
    if item is None:
        raise RuntimeError("Account profile could not be synchronized")
    if is_new_login:
        await audit_event(user.uid, "login", resource_type="account", resource_id=user.uid, metadata={"provider": user.provider or "unknown"})
    return _view(item, user)


async def get_account_profile(user: AuthenticatedUser) -> AccountView:
    item = await get_database().users.find_one({"uid": user.uid})
    return _view(item, user) if item is not None else await sync_account_session(user)
