from datetime import UTC, datetime
from urllib.parse import urlsplit

from bson import ObjectId
from fastapi import HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo.errors import DuplicateKeyError

from app.loaders.web_loader import normalize_url
from app.schemas.document import ProcessingStatus
from app.schemas.website import WebsiteCreate, WebsiteView


class WebsiteRepository:
    def __init__(self, database: AsyncIOMotorDatabase) -> None:
        self.database = database
        self.collection = database.website_sources

    @staticmethod
    def view(item: dict) -> WebsiteView:
        return WebsiteView(id=str(item["_id"]), workspace_id=item["workspace_id"], url=item["url"], domain=item["domain"], title=item.get("title"), meta_description=item.get("meta_description"), content_preview=item.get("content_preview"), scope=item["scope"], status=item["status"], indexed_pages=item.get("indexed_pages", 0), chunk_count=item.get("chunk_count", 0), important_headings=item.get("important_headings", []), internal_links=item.get("internal_links", []), external_links=item.get("external_links", []), error_message=item.get("error_message"), analysis_method=item.get("analysis_method", "direct"), source_notice=item.get("source_notice"), created_at=item["created_at"], updated_at=item["updated_at"])

    async def create(self, owner_id: str, payload: WebsiteCreate) -> WebsiteView:
        now = datetime.now(UTC); url = str(payload.url); normalized = normalize_url(url)
        item = {"owner_id": owner_id, "workspace_id": payload.workspace_id, "url": url, "normalized_url": normalized, "domain": urlsplit(normalized).hostname or "", "scope": payload.scope.value, "selected_urls": [str(item) for item in payload.selected_urls], "max_depth": payload.max_depth, "max_pages": payload.max_pages, "status": ProcessingStatus.QUEUED.value, "indexed_pages": 0, "chunk_count": 0, "created_at": now, "updated_at": now}
        try: result = await self.collection.insert_one(item)
        except DuplicateKeyError as exc: raise HTTPException(status_code=409, detail="This website is already indexed in the workspace") from exc
        item["_id"] = result.inserted_id
        await self.database.workspaces.update_one({"_id": ObjectId(payload.workspace_id), "owner_id": owner_id}, {"$inc": {"website_count": 1}, "$set": {"updated_at": now}})
        return self.view(item)

    async def list_owned(self, owner_id: str, workspace_id: str | None, limit: int, skip: int) -> list[WebsiteView]:
        query: dict = {"owner_id": owner_id}
        if workspace_id: query["workspace_id"] = workspace_id
        cursor = self.collection.find(query).sort("created_at", -1).skip(skip).limit(limit)
        return [self.view(item) async for item in cursor]

    async def get_owned(self, owner_id: str, website_id: str) -> dict:
        if not ObjectId.is_valid(website_id): raise HTTPException(status_code=404, detail="Website source not found")
        item = await self.collection.find_one({"_id": ObjectId(website_id), "owner_id": owner_id})
        if item is None: raise HTTPException(status_code=404, detail="Website source not found")
        return item

    async def set_status(self, owner_id: str, website_id: str, processing_status: ProcessingStatus, **fields: object) -> None:
        await self.collection.update_one({"_id": ObjectId(website_id), "owner_id": owner_id}, {"$set": {"status": processing_status.value, "updated_at": datetime.now(UTC), **fields}})

    async def delete_metadata(self, owner_id: str, website_id: str) -> None:
        item = await self.get_owned(owner_id, website_id); now = datetime.now(UTC)
        await self.database.processing_jobs.delete_many({"source_id": website_id, "owner_id": owner_id})
        await self.collection.delete_one({"_id": item["_id"], "owner_id": owner_id})
        await self.database.workspaces.update_one({"_id": ObjectId(item["workspace_id"]), "owner_id": owner_id}, {"$inc": {"website_count": -1}, "$set": {"updated_at": now}})
