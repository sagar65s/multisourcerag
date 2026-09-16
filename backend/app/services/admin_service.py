import asyncio
from datetime import UTC, datetime, timedelta

from app.core.config import Settings
from app.core.provider_state import provider_state
from app.core.observability import operations
from app.database.mongodb import get_database
from app.database.qdrant import VectorStore
from app.providers.llm.base import ProviderHealth
from app.providers.llm.factory import build_llm_registry
from app.providers.search.factory import build_search_registry


async def _provider_usage(collection_name: str) -> dict[str, dict]:
    pipeline = [{"$group": {"_id": "$provider", "requests": {"$sum": 1}, "errors": {"$sum": {"$cond": [{"$eq": ["$outcome", "error"]}, 1, 0]}}, "rate_limits": {"$sum": {"$cond": ["$rate_limited", 1, 0]}}, "average_latency_ms": {"$avg": "$duration_ms"}, "last_event": {"$max": "$created_at"}, "output_chars": {"$sum": "$output_chars"}}}]
    items = [item async for item in get_database()[collection_name].aggregate(pipeline)]
    return {str(item["_id"]): {key: value for key, value in item.items() if key != "_id"} for item in items}


async def provider_overview(settings: Settings) -> dict:
    llm_usage, search_usage = await asyncio.gather(_provider_usage("provider_logs"), _provider_usage("search_logs"))
    llm = []
    for descriptor in build_llm_registry(settings).status():
        runtime = provider_state.snapshot("llm", descriptor.name)
        health = ProviderHealth.MISCONFIGURED.value if not descriptor.enabled else runtime["health"]
        llm.append({"name": descriptor.name, "model": descriptor.model, "priority": descriptor.priority, "enabled": descriptor.enabled, "base_url": descriptor.base_url, "api_key_env_name": descriptor.api_key_env_name, "timeout": descriptor.timeout_seconds, "retries": descriptor.retries, "rpm": descriptor.rpm, "daily_quota": descriptor.daily_quota, "context_size": descriptor.context_size, "streaming": descriptor.streaming, "vision": descriptor.vision, "tools": descriptor.tools, **runtime, **llm_usage.get(descriptor.name, {}), "health": health})
    search = []
    for item in build_search_registry(settings).status():
        runtime = provider_state.snapshot("search", item["name"])
        health = ProviderHealth.MISCONFIGURED.value if not item["enabled"] else runtime["health"]
        search.append({**item, **runtime, **search_usage.get(item["name"], {}), "health": health})
    return {"llm": llm, "search": search}


async def _daily_activity(days: int = 14) -> list[dict]:
    start = datetime.now(UTC) - timedelta(days=days - 1)
    totals: dict[str, dict] = {}
    for collection, label in (("conversations", "conversations"), ("documents", "documents"), ("research_sessions", "research"), ("website_sources", "websites")):
        pipeline = [{"$match": {"created_at": {"$gte": start}}}, {"$group": {"_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}}, "count": {"$sum": 1}}}]
        async for item in get_database()[collection].aggregate(pipeline): totals.setdefault(item["_id"], {"date": item["_id"], "conversations": 0, "documents": 0, "research": 0, "websites": 0})[label] = item["count"]
    return [totals.setdefault((start + timedelta(days=index)).date().isoformat(), {"date": (start + timedelta(days=index)).date().isoformat(), "conversations": 0, "documents": 0, "research": 0, "websites": 0}) for index in range(days)]


async def admin_overview(settings: Settings) -> dict:
    database = get_database()
    registered_users = await database.users.count_documents({})
    counts = await asyncio.gather(database.workspaces.count_documents({}), database.documents.count_documents({}), database.website_sources.count_documents({}), database.conversations.count_documents({}), database.messages.count_documents({"role": "user"}), database.research_sessions.count_documents({"kind": "deep_research"}), database.documents.count_documents({"ocr_used": True}), database.provider_logs.count_documents({"outcome": "error"}), database.search_logs.count_documents({}), database.security_logs.count_documents({}), database.feedback.count_documents({"helpful": False}))
    owners: set[str] = set()
    for collection in (database.workspaces, database.conversations, database.documents): owners.update(await collection.distinct("owner_id"))
    system = {"mongodb": "healthy", "qdrant": "unknown"}
    try:
        system["qdrant"] = "healthy" if await VectorStore(settings).client.collection_exists(settings.qdrant_collection) else "not_initialized"
    except Exception: system["qdrant"] = "offline"
    audit = []
    async for item in database.audit_logs.find({}, {"action": 1, "status": 1, "resource_type": 1, "actor_id": 1, "created_at": 1}).sort("created_at", -1).limit(20):
        actor = str(item.get("actor_id") or "system"); audit.append({"action": item.get("action"), "status": item.get("status"), "resource_type": item.get("resource_type"), "actor": f"{actor[:6]}…" if len(actor) > 6 else actor, "created_at": item.get("created_at")})
    security = []
    async for item in database.security_logs.find({}, {"event": 1, "severity": 1, "created_at": 1}).sort("created_at", -1).limit(20): security.append({"event": item.get("event"), "severity": item.get("severity"), "created_at": item.get("created_at")})
    providers, activity = await asyncio.gather(provider_overview(settings), _daily_activity())
    return {"metrics": {"users": max(registered_users, len(owners)), "workspaces": counts[0], "documents": counts[1], "websites": counts[2], "conversations": counts[3], "questions": counts[4], "deep_research": counts[5], "ocr_jobs": counts[6], "provider_errors": counts[7], "live_searches": counts[8], "security_events": counts[9], "negative_feedback": counts[10]}, "system": system, "operations": operations.snapshot(), "providers": providers, "activity": activity, "audit_logs": audit, "security_logs": security}
