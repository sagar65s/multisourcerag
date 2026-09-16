import pytest

from app.core.config import Settings
from app.services.retrieval_service import RetrievalService


class ScopedChunks:
    def __init__(self) -> None:
        self.private_rows = [{"owner_id": "user-a", "workspace_id": "workspace-a", "text": "USER_A_PRIVATE_SECRET"}]
        self.last_filter: dict | None = None

    async def count_documents(self, filters: dict, limit: int = 0) -> int:
        self.last_filter = filters
        return sum(all(row.get(key) == value for key, value in filters.items()) for row in self.private_rows)


class Database:
    def __init__(self) -> None:
        self.document_chunks = ScopedChunks()


@pytest.mark.asyncio
async def test_user_b_cannot_retrieve_user_a_private_secret(monkeypatch) -> None:
    database = Database()
    monkeypatch.setattr("app.services.retrieval_service.get_database", lambda: database)
    result = await RetrievalService(Settings()).retrieve("user-b", "workspace-a", "USER_A_PRIVATE_SECRET")
    assert result.evidence == []
    assert result.status == "no_evidence"
    assert database.document_chunks.last_filter == {"owner_id": "user-b", "workspace_id": "workspace-a"}
