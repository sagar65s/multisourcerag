import pytest

from app.services.dashboard_service import dashboard_overview


class Cursor:
    def __init__(self):
        self.filter = None
    def find(self, query, _projection):
        self.filter = query
        return self
    def sort(self, *_args): return self
    def limit(self, _limit): return self
    def __aiter__(self):
        async def empty():
            if False: yield None
        return empty()


class Collection(Cursor):
    async def count_documents(self, query):
        self.filter = query
        return 0


class Database:
    def __init__(self):
        self.workspaces=Collection(); self.documents=Collection(); self.website_sources=Collection(); self.conversations=Collection(); self.saved_answers=Collection(); self.processing_jobs=Collection()


@pytest.mark.asyncio
async def test_dashboard_queries_are_owner_scoped(monkeypatch):
    database = Database()
    monkeypatch.setattr("app.services.dashboard_service.get_database", lambda: database)
    result = await dashboard_overview("user-a")
    assert result["metrics"]["indexed_sources"] == 0
    for collection in (database.workspaces, database.documents, database.website_sources, database.conversations, database.saved_answers, database.processing_jobs):
        assert collection.filter["owner_id"] == "user-a"
