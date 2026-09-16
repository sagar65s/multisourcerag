from datetime import UTC, datetime, timedelta

from bson import ObjectId
from fastapi import BackgroundTasks, HTTPException, status

from app.core.config import Settings, get_settings
from app.database.mongodb import get_database
from app.schemas.job import JobView
from app.services.job_dispatcher import InProcessJobDispatcher


ACTIVE = {"queued", "processing", "cancel_requested"}
RETRYABLE = {"failed", "canceled"}
RESOURCE_COLLECTION = {
    "document_ingestion": "documents",
    "document_reindex": "documents",
    "website_ingestion": "website_sources",
    "website_reindex": "website_sources",
    "document_intelligence": "document_artifacts",
    "deep_research": "research_sessions",
}


def view_job(item: dict) -> JobView:
    state = str(item.get("status", "failed"))
    return JobView(
        id=item["job_id"], workspace_id=item.get("workspace_id"), source_id=item["source_id"],
        source_name=item.get("source_name", "Private job"), kind=item["kind"], status=state,
        stage=item.get("stage", state), attempt=int(item.get("attempt", 1)), error_code=item.get("error_code"),
        can_cancel=state in {"queued", "processing"}, can_retry=state in RETRYABLE and int(item.get("attempt", 1)) < 3,
        created_at=item["created_at"], updated_at=item["updated_at"],
    )


async def get_owned_job(owner_id: str, job_id: str) -> dict:
    item = await get_database().processing_jobs.find_one({"job_id": job_id, "owner_id": owner_id})
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Processing job not found")
    return item


async def list_owned_jobs(owner_id: str, limit: int, skip: int) -> list[JobView]:
    cursor = get_database().processing_jobs.find({"owner_id": owner_id}).sort("updated_at", -1).skip(skip).limit(limit)
    return [view_job(item) async for item in cursor]


async def recover_interrupted_jobs() -> int:
    """Fail in-process work left active by a previous application instance."""
    database = get_database()
    interrupted = [item async for item in database.processing_jobs.find({"status": {"$in": list(ACTIVE)}})]
    recovered = 0
    for item in interrupted:
        now = datetime.now(UTC)
        result = await database.processing_jobs.update_one(
            {"job_id": item["job_id"], "owner_id": item["owner_id"], "status": {"$in": list(ACTIVE)}},
            {"$set": {"status": "failed", "stage": "failed", "error_code": "WorkerRestarted", "updated_at": now, "completed_at": now, "expires_at": now + timedelta(days=get_settings().processing_job_retention_days)}},
        )
        if getattr(result, "modified_count", 1):
            recovered += 1
            await _mark_source(item["owner_id"], item, retrying=False, message="Processing was interrupted by a service restart. Retry when ready.")
    return recovered


async def _mark_source(owner_id: str, item: dict, retrying: bool, message: str = "Processing canceled by the user.") -> None:
    collection_name = RESOURCE_COLLECTION.get(item["kind"])
    if collection_name is None or not ObjectId.is_valid(item["source_id"]):
        return
    status_value = "planning" if collection_name == "research_sessions" and retrying else "queued" if retrying else "failed"
    changes = {"status": status_value, "updated_at": datetime.now(UTC)}
    if retrying:
        changes["error_message"] = None
    else:
        changes["error_message"] = message
    await get_database()[collection_name].update_one({"_id": ObjectId(item["source_id"]), "owner_id": owner_id}, {"$set": changes})


async def cancel_owned_job(owner_id: str, job_id: str) -> JobView:
    item = await get_owned_job(owner_id, job_id)
    if item.get("status") not in {"queued", "processing"}:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only queued or processing jobs can be canceled")
    now = datetime.now(UTC)
    await get_database().processing_jobs.update_one(
        {"job_id": job_id, "owner_id": owner_id, "status": {"$in": ["queued", "processing"]}},
        {"$set": {"status": "cancel_requested", "stage": "cancel_requested", "cancel_requested_at": now, "updated_at": now}},
    )
    await _mark_source(owner_id, item, retrying=False)
    return view_job(await get_owned_job(owner_id, job_id))


def _worker(kind: str):
    if kind in {"document_ingestion", "document_reindex"}:
        from app.services.document_service import process_document
        return process_document
    if kind in {"website_ingestion", "website_reindex"}:
        from app.services.website_service import process_website
        return process_website
    if kind == "document_intelligence":
        from app.services.intelligence_service import process_intelligence
        return process_intelligence
    from app.services.analysis_service import process_deep_research
    return process_deep_research if kind == "deep_research" else None


async def retry_owned_job(owner_id: str, job_id: str, background_tasks: BackgroundTasks, settings: Settings) -> JobView:
    item = await get_owned_job(owner_id, job_id)
    attempt = int(item.get("attempt", 1))
    if item.get("status") not in RETRYABLE:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only failed or canceled jobs can be retried")
    if attempt >= 3:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This job has reached the retry limit")
    worker = _worker(item["kind"])
    if worker is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This job type cannot be retried")
    collection_name = RESOURCE_COLLECTION.get(item["kind"])
    if collection_name and (not ObjectId.is_valid(item["source_id"]) or await get_database()[collection_name].count_documents({"_id": ObjectId(item["source_id"]), "owner_id": owner_id}, limit=1) == 0):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="The original private resource no longer exists")
    await _mark_source(owner_id, item, retrying=True)
    new_id = await InProcessJobDispatcher(background_tasks).enqueue(
        owner_id, item["kind"], item["source_id"], item.get("source_name", "Private job"), worker,
        owner_id, item["source_id"], settings, workspace_id=item.get("workspace_id"), attempt=attempt + 1, parent_job_id=job_id,
    )
    await get_database().processing_jobs.update_one({"job_id": job_id, "owner_id": owner_id}, {"$set": {"retried_by": new_id, "updated_at": datetime.now(UTC)}})
    return view_job(await get_owned_job(owner_id, new_id))
