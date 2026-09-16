import asyncio
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from fastapi import BackgroundTasks

from app.database.mongodb import get_database
from app.core.config import get_settings

AsyncWorker = Callable[..., Awaitable[None]]


class InProcessJobDispatcher:
    """Persistent job contract. Replace this adapter with Celery/RQ without changing API routes."""

    def __init__(self, background_tasks: BackgroundTasks) -> None:
        self.background_tasks = background_tasks

    async def enqueue(self, owner_id: str, kind: str, source_id: str, source_name: str, worker: AsyncWorker, *args: Any, workspace_id: str | None = None, attempt: int = 1, parent_job_id: str | None = None) -> str:
        job_id = str(uuid4())
        now = datetime.now(UTC)
        await get_database().processing_jobs.insert_one({"job_id": job_id, "owner_id": owner_id, "workspace_id": workspace_id, "source_id": source_id, "source_name": source_name[:180], "kind": kind, "status": "queued", "stage": "queued", "attempt": attempt, "parent_job_id": parent_job_id, "created_at": now, "updated_at": now})
        self.background_tasks.add_task(self._execute, job_id, owner_id, worker, args)
        return job_id

    @staticmethod
    async def _execute(job_id: str, owner_id: str, worker: AsyncWorker, args: tuple[Any, ...]) -> None:
        jobs = get_database().processing_jobs
        scope = {"job_id": job_id, "owner_id": owner_id}
        current = await jobs.find_one(scope, {"status": 1})
        if current is None or current.get("status") in {"cancel_requested", "canceled"}:
            now = datetime.now(UTC)
            await jobs.update_one(scope, {"$set": {"status": "canceled", "stage": "canceled", "updated_at": now, "completed_at": now, "expires_at": now + timedelta(days=get_settings().processing_job_retention_days)}})
            return
        await jobs.update_one({**scope, "status": "queued"}, {"$set": {"status": "processing", "stage": "processing", "updated_at": datetime.now(UTC), "started_at": datetime.now(UTC)}})
        claimed = await jobs.find_one(scope, {"status": 1})
        if claimed is None or claimed.get("status") != "processing":
            if claimed and claimed.get("status") == "cancel_requested":
                now = datetime.now(UTC)
                await jobs.update_one(scope, {"$set": {"status": "canceled", "stage": "canceled", "updated_at": now, "completed_at": now, "expires_at": now + timedelta(days=get_settings().processing_job_retention_days)}})
            return
        task = asyncio.create_task(worker(*args))
        try:
            while not task.done():
                await asyncio.wait({task}, timeout=0.25)
                current = await jobs.find_one(scope, {"status": 1})
                if current and current.get("status") == "cancel_requested":
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
                    now = datetime.now(UTC)
                    await jobs.update_one(scope, {"$set": {"status": "canceled", "stage": "canceled", "updated_at": now, "completed_at": now, "expires_at": now + timedelta(days=get_settings().processing_job_retention_days)}})
                    return
            await task
            now = datetime.now(UTC)
            await jobs.update_one({**scope, "status": "processing"}, {"$set": {"status": "completed", "stage": "completed", "updated_at": now, "completed_at": now, "expires_at": now + timedelta(days=get_settings().processing_job_retention_days)}, "$unset": {"error_code": ""}})
        except asyncio.CancelledError:
            task.cancel()
            now = datetime.now(UTC)
            await jobs.update_one(scope, {"$set": {"status": "canceled", "stage": "canceled", "updated_at": now, "completed_at": now, "expires_at": now + timedelta(days=get_settings().processing_job_retention_days)}})
            raise
        except Exception as exc:
            now = datetime.now(UTC)
            await jobs.update_one(scope, {"$set": {"status": "failed", "stage": "failed", "error_code": type(exc).__name__, "updated_at": now, "completed_at": now, "expires_at": now + timedelta(days=get_settings().processing_job_retention_days)}})
