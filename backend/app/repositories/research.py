from datetime import UTC, datetime

from bson import ObjectId
from fastapi import HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.schemas.research import ResearchSessionView, ResearchStage, SessionKind


class ResearchRepository:
    def __init__(self, database: AsyncIOMotorDatabase) -> None: self.database = database; self.collection = database.research_sessions
    @staticmethod
    def view(item: dict) -> ResearchSessionView:
        return ResearchSessionView(id=str(item["_id"]), kind=item["kind"], title=item["title"], status=item["status"], queries=item.get("queries", []), source_count=item.get("source_count", 0), sources=item.get("sources", []), conflicts=item.get("conflicts", []), output_markdown=item.get("output_markdown"), error_message=item.get("error_message"), created_at=item["created_at"], updated_at=item["updated_at"])
    async def create(self, owner_id: str, kind: SessionKind, title: str, request: dict) -> ResearchSessionView:
        now = datetime.now(UTC); item = {"owner_id": owner_id, "kind": kind.value, "title": title[:180], "request": request, "status": ResearchStage.PLANNING.value, "queries": [], "source_count": 0, "sources": [], "conflicts": [], "created_at": now, "updated_at": now}
        result = await self.collection.insert_one(item); item["_id"] = result.inserted_id; return self.view(item)
    async def get_owned(self, owner_id: str, session_id: str) -> dict:
        if not ObjectId.is_valid(session_id): raise HTTPException(status_code=404, detail="Research session not found")
        item = await self.collection.find_one({"_id": ObjectId(session_id), "owner_id": owner_id})
        if item is None: raise HTTPException(status_code=404, detail="Research session not found")
        return item
    async def list_owned(self, owner_id: str, kind: SessionKind | None, limit: int, skip: int) -> list[ResearchSessionView]:
        query: dict = {"owner_id": owner_id}
        if kind: query["kind"] = kind.value
        cursor = self.collection.find(query).sort("updated_at", -1).skip(skip).limit(limit); return [self.view(item) async for item in cursor]
    async def update(self, owner_id: str, session_id: str, stage: ResearchStage, **fields: object) -> None:
        await self.collection.update_one({"_id": ObjectId(session_id), "owner_id": owner_id}, {"$set": {"status": stage.value, "updated_at": datetime.now(UTC), **fields}})
    async def delete(self, owner_id: str, session_id: str) -> None:
        item = await self.get_owned(owner_id, session_id); await self.database.processing_jobs.delete_many({"source_id": session_id, "owner_id": owner_id}); await self.collection.delete_one({"_id": item["_id"], "owner_id": owner_id})
