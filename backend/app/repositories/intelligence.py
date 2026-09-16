from datetime import UTC, datetime

from bson import ObjectId
from fastapi import HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.schemas.intelligence import IntelligenceArtifactView, IntelligenceRequest, IntelligenceStatus


class IntelligenceRepository:
    def __init__(self, database: AsyncIOMotorDatabase) -> None:
        self.database = database
        self.collection = database.document_artifacts

    @staticmethod
    def view(item: dict) -> IntelligenceArtifactView:
        return IntelligenceArtifactView(
            id=str(item["_id"]), workspace_id=item["workspace_id"], source_ids=item["source_ids"],
            source_names=item.get("source_names", []), tool=item["tool"], status=item["status"],
            language=item["language"], result=item.get("result", {}), citations=item.get("citations", []),
            error_message=item.get("error_message"), created_at=item["created_at"], updated_at=item["updated_at"],
        )

    async def create(self, owner_id: str, payload: IntelligenceRequest) -> IntelligenceArtifactView:
        now = datetime.now(UTC)
        item = {
            "owner_id": owner_id, "workspace_id": payload.workspace_id, "source_ids": payload.source_ids,
            "source_names": [], "tool": payload.tool.value, "language": payload.language,
            "request": payload.model_dump(mode="json"), "status": IntelligenceStatus.QUEUED.value,
            "result": {}, "citations": [], "created_at": now, "updated_at": now,
        }
        inserted = await self.collection.insert_one(item)
        item["_id"] = inserted.inserted_id
        return self.view(item)

    async def get_owned(self, owner_id: str, artifact_id: str) -> dict:
        if not ObjectId.is_valid(artifact_id):
            raise HTTPException(status_code=404, detail="Intelligence result not found")
        item = await self.collection.find_one({"_id": ObjectId(artifact_id), "owner_id": owner_id})
        if item is None:
            raise HTTPException(status_code=404, detail="Intelligence result not found")
        return item

    async def list_owned(self, owner_id: str, workspace_id: str | None, limit: int, skip: int) -> list[IntelligenceArtifactView]:
        query: dict = {"owner_id": owner_id}
        if workspace_id:
            query["workspace_id"] = workspace_id
        cursor = self.collection.find(query).sort("updated_at", -1).skip(skip).limit(limit)
        return [self.view(item) async for item in cursor]

    async def update(self, owner_id: str, artifact_id: str, status: IntelligenceStatus, **fields: object) -> None:
        await self.collection.update_one(
            {"_id": ObjectId(artifact_id), "owner_id": owner_id},
            {"$set": {"status": status.value, "updated_at": datetime.now(UTC), **fields}},
        )

    async def delete(self, owner_id: str, artifact_id: str) -> None:
        item = await self.get_owned(owner_id, artifact_id)
        await self.database.processing_jobs.delete_many({"source_id": artifact_id, "owner_id": owner_id})
        await self.collection.delete_one({"_id": item["_id"], "owner_id": owner_id})
