import asyncio
from fastapi import BackgroundTasks
import pytest

from app.services.job_dispatcher import InProcessJobDispatcher


class Jobs:
    def __init__(self): self.item = {}; self.transitions = []
    async def insert_one(self, item): self.item = item.copy()
    async def find_one(self, scope, _projection=None):
        if scope.get("job_id") != self.item.get("job_id") or scope.get("owner_id") != self.item.get("owner_id"): return None
        return self.item.copy()
    async def update_one(self, scope, update):
        assert scope["owner_id"] == self.item["owner_id"]
        expected = scope.get("status")
        if isinstance(expected, str) and self.item.get("status") != expected: return
        self.item.update(update.get("$set", {})); self.transitions.append(self.item["status"])


class Database:
    def __init__(self): self.processing_jobs = Jobs()


@pytest.mark.asyncio
async def test_persistent_job_lifecycle(monkeypatch):
    database = Database(); tasks = BackgroundTasks(); executed = []
    monkeypatch.setattr("app.services.job_dispatcher.get_database", lambda: database)
    async def worker(value): executed.append(value)
    job_id = await InProcessJobDispatcher(tasks).enqueue("user-a", "ocr", "doc-a", "scan.pdf", worker, "done", workspace_id="workspace-a")
    assert database.processing_jobs.item["status"] == "queued"
    assert database.processing_jobs.item["job_id"] == job_id
    await tasks()
    assert executed == ["done"]
    assert database.processing_jobs.transitions == ["processing", "completed"]


@pytest.mark.asyncio
async def test_failed_job_records_error_class_without_message(monkeypatch):
    database = Database(); tasks = BackgroundTasks()
    monkeypatch.setattr("app.services.job_dispatcher.get_database", lambda: database)
    async def worker(): raise RuntimeError("private secret must not be logged")
    await InProcessJobDispatcher(tasks).enqueue("user-a", "crawl", "site-a", "example.com", worker)
    await tasks()
    assert database.processing_jobs.item["status"] == "failed"
    assert database.processing_jobs.item["error_code"] == "RuntimeError"
    assert "private secret" not in str(database.processing_jobs.item)


@pytest.mark.asyncio
async def test_running_job_honors_persisted_cancel_request(monkeypatch):
    database = Database(); tasks = BackgroundTasks(); started = asyncio.Event(); canceled = asyncio.Event()
    monkeypatch.setattr("app.services.job_dispatcher.get_database", lambda: database)
    async def worker():
        started.set()
        try: await asyncio.Event().wait()
        finally: canceled.set()
    await InProcessJobDispatcher(tasks).enqueue("user-a", "crawl", "site-a", "example.com", worker)
    execution = asyncio.create_task(tasks())
    await started.wait()
    database.processing_jobs.item["status"] = "cancel_requested"
    await execution
    assert canceled.is_set()
    assert database.processing_jobs.item["status"] == "canceled"
