import pytest

from app.services.provider_telemetry import record_provider_event


class Collection:
    def __init__(self): self.item=None
    async def insert_one(self,item): self.item=item


class Database:
    def __init__(self): self.provider_logs=Collection(); self.search_logs=Collection()


@pytest.mark.asyncio
async def test_provider_telemetry_contains_no_prompt_context_or_secret_fields(monkeypatch) -> None:
    database=Database(); monkeypatch.setattr("app.services.provider_telemetry.get_database",lambda:database)
    await record_provider_event("llm","gemini","model","error",120,error_type="TimeoutError",output_chars=0)
    item=database.provider_logs.item
    assert item is not None
    forbidden={"prompt","messages","context","api_key","token","content","answer"}
    assert forbidden.isdisjoint(item)
    assert "secret" not in str(item).casefold()
    assert item["expires_at"] > item["created_at"]
