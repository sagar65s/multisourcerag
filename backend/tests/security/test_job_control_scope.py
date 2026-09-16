from datetime import UTC, datetime

import pytest
from fastapi import BackgroundTasks
from fastapi import HTTPException

from app.core.config import Settings
from app.services.job_control_service import cancel_owned_job, recover_interrupted_jobs, retry_owned_job


class Jobs:
    def __init__(self) -> None:
        now = datetime.now(UTC)
        self.item = {"job_id": "job-a", "owner_id": "user-a", "source_id": "source-a", "source_name": "Private", "kind": "unknown", "status": "processing", "stage": "processing", "attempt": 1, "created_at": now, "updated_at": now}
        self.filters: list[dict] = []
    async def find_one(self, query: dict):
        self.filters.append(query)
        return self.item.copy() if query.get("owner_id") == self.item["owner_id"] and query.get("job_id") == self.item["job_id"] else None
    async def update_one(self, query: dict, update: dict):
        self.filters.append(query)
        if query.get("owner_id") == self.item["owner_id"]: self.item.update(update["$set"])


class Database:
    def __init__(self) -> None: self.processing_jobs = Jobs()
    def __getitem__(self, _name): raise AssertionError("Unknown job kinds must not mutate a resource collection")


@pytest.mark.asyncio
async def test_job_cancel_is_owner_scoped_and_cross_user_is_hidden(monkeypatch) -> None:
    database = Database(); monkeypatch.setattr("app.services.job_control_service.get_database", lambda: database)
    with pytest.raises(HTTPException) as denied:
        await cancel_owned_job("user-b", "job-a")
    assert denied.value.status_code == 404
    result = await cancel_owned_job("user-a", "job-a")
    assert result.status == "cancel_requested"
    assert all(item.get("owner_id") in {"user-a", "user-b"} for item in database.processing_jobs.filters)


@pytest.mark.asyncio
async def test_completed_job_cannot_be_canceled(monkeypatch) -> None:
    database = Database(); database.processing_jobs.item["status"] = "completed"
    monkeypatch.setattr("app.services.job_control_service.get_database", lambda: database)
    with pytest.raises(HTTPException) as conflict:
        await cancel_owned_job("user-a", "job-a")
    assert conflict.value.status_code == 409


class Result:
    modified_count = 1


class Cursor:
    def __init__(self, items): self.items = items
    def __aiter__(self): self.iterator = iter(self.items); return self
    async def __anext__(self):
        try: return next(self.iterator)
        except StopIteration: raise StopAsyncIteration


class RetryJobs(Jobs):
    def find(self, _query): return Cursor([self.item.copy()])
    async def update_one(self, query: dict, update: dict):
        await super().update_one(query, update)
        return Result()


class ResourceCollection:
    def __init__(self): self.updates = []
    async def count_documents(self, query, **_kwargs): return 1 if query.get("owner_id") == "user-a" else 0
    async def update_one(self, query, update): self.updates.append((query, update)); return Result()


class RetryDatabase:
    def __init__(self):
        self.processing_jobs = RetryJobs()
        self.processing_jobs.item.update({"kind": "document_ingestion", "status": "failed", "stage": "failed", "source_id": "507f1f77bcf86cd799439011", "workspace_id": "workspace-a"})
        self.documents = ResourceCollection()
    def __getitem__(self, name): return getattr(self, name)


@pytest.mark.asyncio
async def test_failed_owned_job_can_be_retried_with_incremented_attempt(monkeypatch) -> None:
    database = RetryDatabase(); captured = {}
    monkeypatch.setattr("app.services.job_control_service.get_database", lambda: database)
    monkeypatch.setattr("app.services.job_control_service._worker", lambda _kind: object())
    async def enqueue(_self, owner_id, kind, source_id, source_name, worker, *args, **kwargs):
        captured.update(owner_id=owner_id, kind=kind, source_id=source_id, attempt=kwargs["attempt"], parent_job_id=kwargs["parent_job_id"])
        new_item = database.processing_jobs.item.copy()
        new_item.update({"job_id": "job-b", "status": "queued", "stage": "queued", "attempt": kwargs["attempt"], "parent_job_id": kwargs["parent_job_id"], "updated_at": datetime.now(UTC)})
        database.processing_jobs.item = new_item
        return "job-b"
    monkeypatch.setattr("app.services.job_control_service.InProcessJobDispatcher.enqueue", enqueue)
    result = await retry_owned_job("user-a", "job-a", BackgroundTasks(), Settings())
    assert result.id == "job-b"
    assert result.attempt == 2
    assert captured == {"owner_id": "user-a", "kind": "document_ingestion", "source_id": "507f1f77bcf86cd799439011", "attempt": 2, "parent_job_id": "job-a"}
    assert database.documents.updates[-1][0]["owner_id"] == "user-a"


@pytest.mark.asyncio
async def test_restart_recovery_marks_active_jobs_retryable_without_content(monkeypatch) -> None:
    database = RetryDatabase()
    database.processing_jobs.item.update({"status": "processing", "stage": "embedding"})
    monkeypatch.setattr("app.services.job_control_service.get_database", lambda: database)
    recovered = await recover_interrupted_jobs()
    assert recovered == 1
    assert database.processing_jobs.item["status"] == "failed"
    assert database.processing_jobs.item["error_code"] == "WorkerRestarted"
    assert "content" not in database.processing_jobs.item
    assert "service restart" in database.documents.updates[-1][1]["$set"]["error_message"]
