from datetime import UTC, datetime

from bson import ObjectId
from fastapi import HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.schemas.document import DocumentView, ProcessingStatus


class DocumentRepository:
    def __init__(self, database: AsyncIOMotorDatabase) -> None:
        self.documents = database.documents

    @staticmethod
    def view(item: dict) -> DocumentView:
        return DocumentView(id=str(item["_id"]), workspace_id=item["workspace_id"], original_name=item["original_name"], media_type=item["media_type"], size_bytes=item["size_bytes"], page_count=item.get("page_count", 0), chunk_count=item.get("chunk_count", 0), ocr_used=item.get("ocr_used", False), status=ProcessingStatus(item["status"]), error_message=item.get("error_message"), created_at=item["created_at"], updated_at=item["updated_at"])

    async def create(self, owner_id: str, workspace_id: str, original_name: str, media_type: str, size_bytes: int, extension: str, stored_path: str) -> DocumentView:
        now = datetime.now(UTC)
        item = {"owner_id": owner_id, "workspace_id": workspace_id, "original_name": original_name, "media_type": media_type, "size_bytes": size_bytes, "extension": extension, "stored_path": stored_path, "status": ProcessingStatus.QUEUED.value, "page_count": 0, "chunk_count": 0, "ocr_used": False, "created_at": now, "updated_at": now}
        result = await self.documents.insert_one(item); item["_id"] = result.inserted_id
        await self.documents.database.workspaces.update_one({"_id": ObjectId(workspace_id), "owner_id": owner_id}, {"$inc": {"document_count": 1}, "$set": {"updated_at": now}})
        return self.view(item)

    async def list_owned(self, owner_id: str, workspace_id: str | None, limit: int, skip: int) -> list[DocumentView]:
        query: dict = {"owner_id": owner_id}
        if workspace_id: query["workspace_id"] = workspace_id
        cursor = self.documents.find(query).sort("created_at", -1).skip(skip).limit(limit)
        return [self.view(item) async for item in cursor]

    async def get_owned(self, owner_id: str, document_id: str) -> dict:
        if not ObjectId.is_valid(document_id): raise HTTPException(status_code=404, detail="Document not found")
        item = await self.documents.find_one({"_id": ObjectId(document_id), "owner_id": owner_id})
        if item is None: raise HTTPException(status_code=404, detail="Document not found")
        return item

    async def set_status(self, owner_id: str, document_id: str, processing_status: ProcessingStatus, **fields: object) -> None:
        now = datetime.now(UTC); changes = {"status": processing_status.value, "updated_at": now, **fields}
        await self.documents.update_one({"_id": ObjectId(document_id), "owner_id": owner_id}, {"$set": changes})

    async def delete_metadata(self, owner_id: str, document_id: str) -> None:
        item = await self.get_owned(owner_id, document_id)
        await self.documents.database.processing_jobs.delete_many({"source_id": document_id, "owner_id": owner_id})
        await self.documents.delete_one({"_id": item["_id"], "owner_id": owner_id})
        await self.documents.database.workspaces.update_one({"_id": ObjectId(item["workspace_id"]), "owner_id": owner_id}, {"$inc": {"document_count": -1}, "$set": {"updated_at": datetime.now(UTC)}})
