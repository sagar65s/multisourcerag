import asyncio

from app.database.mongodb import get_database


def _serialize(item: dict, fields: tuple[str, ...]) -> dict:
    return {"id": str(item["_id"]), **{field: item.get(field) for field in fields}}


async def dashboard_overview(owner_id: str) -> dict:
    """Return only owner-scoped metadata; never private source/message content."""
    database = get_database()
    scope = {"owner_id": owner_id}
    counts = await asyncio.gather(
        database.workspaces.count_documents(scope),
        database.documents.count_documents(scope),
        database.website_sources.count_documents(scope),
        database.conversations.count_documents(scope),
        database.saved_answers.count_documents(scope),
        database.processing_jobs.count_documents({**scope, "status": {"$in": ["queued", "processing", "cancel_requested"]}}),
    )
    workspaces = [_serialize(item, ("name", "description", "document_count", "website_count", "updated_at")) async for item in database.workspaces.find(scope, {"name": 1, "description": 1, "document_count": 1, "website_count": 1, "updated_at": 1}).sort("updated_at", -1).limit(4)]
    conversations = [_serialize(item, ("title", "workspace_id", "message_count", "last_message_preview", "updated_at")) async for item in database.conversations.find(scope, {"title": 1, "workspace_id": 1, "message_count": 1, "last_message_preview": 1, "updated_at": 1}).sort("updated_at", -1).limit(5)]
    jobs = [{"id": item.get("job_id", str(item["_id"])), **{field: item.get(field) for field in ("source_name", "kind", "status", "stage", "attempt", "error_code", "updated_at")}, "can_cancel": item.get("status") in {"queued", "processing"}, "can_retry": item.get("status") in {"failed", "canceled"} and int(item.get("attempt", 1)) < 3} async for item in database.processing_jobs.find(scope, {"job_id": 1, "source_name": 1, "kind": 1, "status": 1, "stage": 1, "attempt": 1, "error_code": 1, "updated_at": 1}).sort("updated_at", -1).limit(5)]
    return {
        "metrics": {"workspaces": counts[0], "documents": counts[1], "websites": counts[2], "conversations": counts[3], "saved_answers": counts[4], "active_jobs": counts[5], "indexed_sources": counts[1] + counts[2]},
        "workspaces": workspaces,
        "conversations": conversations,
        "processing_jobs": jobs,
    }
