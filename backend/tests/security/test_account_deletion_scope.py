import pytest

from app.core.config import Settings
from app.services.account_service import OWNER_COLLECTIONS, delete_account_data


class Collection:
    def __init__(self, has_chunks=False): self.filters=[]; self.has_chunks=has_chunks
    async def count_documents(self, query, **_kwargs): self.filters.append(query); return int(self.has_chunks)
    async def delete_many(self, query): self.filters.append(query)


class Database:
    def __init__(self):
        self.collections={name:Collection(name=="document_chunks") for name in OWNER_COLLECTIONS}
        self.document_chunks=self.collections["document_chunks"]
    def __getitem__(self,name): return self.collections[name]


@pytest.mark.asyncio
async def test_account_deletion_never_uses_global_database_or_vector_delete(monkeypatch) -> None:
    database=Database(); vectors=[]; files=[]; firebase=[]
    class Store:
        def __init__(self,_settings): pass
        async def delete_user(self,owner_id): vectors.append(owner_id)
    class Storage:
        def __init__(self,_root): pass
        async def delete_owner(self,owner_id): files.append(owner_id)
    async def immediate(function,*args): return function(*args)
    monkeypatch.setattr("app.services.account_service.get_database",lambda:database)
    monkeypatch.setattr("app.services.account_service.VectorStore",Store)
    monkeypatch.setattr("app.services.account_service.PrivateStorageService",Storage)
    monkeypatch.setattr("app.services.account_service.asyncio.to_thread",immediate)
    monkeypatch.setattr("app.services.account_service.auth.delete_user",lambda owner_id:firebase.append(owner_id))
    await delete_account_data("user-a",Settings())
    assert vectors==files==firebase==["user-a"]
    for name, collection in database.collections.items():
        assert collection.filters
        assert all(item.get("owner_id")=="user-a" or item.get("actor_id")=="user-a" or (name == "users" and item.get("uid") == "user-a") for item in collection.filters)
