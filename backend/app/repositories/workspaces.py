from datetime import UTC, datetime

from bson import ObjectId
from fastapi import HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.schemas.workspace import WorkspaceCreate, WorkspaceUpdate, WorkspaceView


class WorkspaceRepository:
    def __init__(self, database: AsyncIOMotorDatabase):
        self.collection = database.workspaces

    @staticmethod
    def _view(item: dict) -> WorkspaceView:
        return WorkspaceView(
            id=str(item["_id"]),
            name=item["name"],
            description=item.get("description", ""),
            document_count=item.get("document_count", 0),
            website_count=item.get("website_count", 0),
            created_at=item["created_at"],
            updated_at=item["updated_at"],
        )

    async def list_for_owner(self, owner_id: str, limit: int, skip: int) -> list[WorkspaceView]:
        cursor = self.collection.find({"owner_id": owner_id}).sort("updated_at", -1).skip(skip).limit(limit)
        return [self._view(item) async for item in cursor]

    async def create(self, owner_id: str, payload: WorkspaceCreate) -> WorkspaceView:
        now = datetime.now(UTC)
        item = {"owner_id": owner_id, **payload.model_dump(), "document_count": 0, "website_count": 0, "created_at": now, "updated_at": now}
        result = await self.collection.insert_one(item)
        item["_id"] = result.inserted_id
        return self._view(item)

    async def get_owned(self, owner_id: str, workspace_id: str) -> dict:
        if not ObjectId.is_valid(workspace_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")
        item = await self.collection.find_one({"_id": ObjectId(workspace_id), "owner_id": owner_id})
        if item is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")
        return item

    async def update(self, owner_id: str, workspace_id: str, payload: WorkspaceUpdate) -> WorkspaceView:
        await self.get_owned(owner_id, workspace_id)
        changes = payload.model_dump(exclude_none=True)
        changes["updated_at"] = datetime.now(UTC)
        item = await self.collection.find_one_and_update(
            {"_id": ObjectId(workspace_id), "owner_id": owner_id}, {"$set": changes}, return_document=True
        )
        return self._view(item)

    async def delete(self, owner_id: str, workspace_id: str) -> None:
        await self.get_owned(owner_id, workspace_id)
        result = await self.collection.delete_one({"_id": ObjectId(workspace_id), "owner_id": owner_id})
        if result.deleted_count != 1:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Workspace could not be deleted")

