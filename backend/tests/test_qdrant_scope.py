from app.database.qdrant import VectorStore
import pytest


def test_authorization_filter_contains_owner_and_workspace() -> None:
    query_filter = VectorStore.authorization_filter("user-a", "workspace-a", ["document-a"], ["website"])
    values = {condition.key: getattr(condition.match, "value", None) or getattr(condition.match, "any", None) for condition in query_filter.must}
    assert values["workspace_id"] == "workspace-a"
    assert values["document_id"] == ["document-a"]
    assert values["source_type"] == ["website"]
    assert {(item.key, item.match.value) for item in query_filter.should} == {
        ("user_id", "user-a"),
        ("owner_id", "user-a"),
    }


class Client:
    def __init__(self): self.calls = []
    async def delete(self, **kwargs): self.calls.append(kwargs)


@pytest.mark.asyncio
async def test_user_and_document_deletion_are_filtered_before_qdrant_operation() -> None:
    store = object.__new__(VectorStore); store.collection = "chunks"; store.client = Client()
    await store.delete_document("user-a", "workspace-a", "document-a")
    await store.delete_user("user-a")
    document_filter = store.client.calls[0]["points_selector"].filter
    document_values = {item.key: getattr(item.match,"value",None) or getattr(item.match,"any",None) for item in document_filter.must}
    assert document_values == {"workspace_id":"workspace-a", "document_id":["document-a"]}
    assert {(item.key, item.match.value) for item in document_filter.should} == {("user_id", "user-a"), ("owner_id", "user-a")}
    user_filter = store.client.calls[1]["points_selector"].filter
    assert {(item.key, item.match.value) for item in user_filter.should} == {("user_id", "user-a"), ("owner_id", "user-a")}
