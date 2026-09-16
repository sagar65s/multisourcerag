from datetime import UTC, datetime, timedelta

from app.core.config import get_settings
from app.database.mongodb import get_database


async def record_provider_event(category: str, provider: str, model: str | None, outcome: str, duration_ms: int, error_type: str | None = None, rate_limited: bool = False, output_chars: int = 0) -> None:
    try:
        collection = get_database().provider_logs if category == "llm" else get_database().search_logs
        now = datetime.now(UTC)
        await collection.insert_one({"category": category, "provider": provider, "model": model, "outcome": outcome, "duration_ms": max(duration_ms, 0), "error_type": error_type, "rate_limited": rate_limited, "output_chars": max(output_chars, 0), "created_at": now, "expires_at": now + timedelta(days=get_settings().provider_log_retention_days)})
    except Exception:
        return
