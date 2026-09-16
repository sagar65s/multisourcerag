from datetime import UTC, datetime, timedelta

from app.core.config import get_settings
from app.database.mongodb import get_database


async def audit_event(actor_id: str, action: str, status: str = "success", resource_type: str | None = None, resource_id: str | None = None, metadata: dict | None = None) -> None:
    safe_metadata = {key: value for key, value in (metadata or {}).items() if key in {"count", "scope", "provider", "reason", "media_type", "size_bytes"}}
    try:
        now = datetime.now(UTC)
        await get_database().audit_logs.insert_one({"actor_id": actor_id, "action": action, "status": status, "resource_type": resource_type, "resource_id": resource_id, "metadata": safe_metadata, "created_at": now, "expires_at": now + timedelta(days=get_settings().audit_log_retention_days)})
    except Exception:
        return


async def security_event(event: str, actor_id: str | None = None, severity: str = "warning", metadata: dict | None = None) -> None:
    safe_metadata = {key: value for key, value in (metadata or {}).items() if key in {"reason", "resource_type", "route"}}
    try:
        now = datetime.now(UTC)
        await get_database().security_logs.insert_one({"event": event, "actor_id": actor_id, "severity": severity, "metadata": safe_metadata, "created_at": now, "expires_at": now + timedelta(days=get_settings().security_log_retention_days)})
    except Exception:
        return
