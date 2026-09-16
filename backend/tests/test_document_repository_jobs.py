from types import SimpleNamespace

import pytest
from bson import ObjectId

from app.repositories.documents import DocumentRepository


class Collection:
    def __init__(self, database=None) -> None:
        self.database = database
        self.inserted: list[dict] = []
        self.updated: list[tuple] = []

    async def insert_one(self, item: dict):
        self.inserted.append(item.copy())
        return SimpleNamespace(inserted_id=ObjectId())

    async def update_one(self, query: dict, update: dict):
        self.updated.append((query, update))


class Database:
    def __init__(self) -> None:
        self.documents = Collection(self)
        self.workspaces = Collection(self)
        self.processing_jobs = Collection(self)


@pytest.mark.asyncio
async def test_document_repository_does_not_create_competing_legacy_job() -> None:
    database = Database()
    workspace_id = str(ObjectId())
    created = await DocumentRepository(database).create("user-a", workspace_id, "report.pdf", "application/pdf", 42, ".pdf", "/private/id.pdf")
    assert created.status.value == "queued"
    assert len(database.documents.inserted) == 1
    assert database.processing_jobs.inserted == []
