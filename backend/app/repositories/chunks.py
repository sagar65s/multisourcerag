from datetime import UTC, datetime
import re

from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo.errors import OperationFailure

from app.rag.chunking import TextChunk


class ChunkRepository:
    def __init__(self, database: AsyncIOMotorDatabase) -> None:
        self.collection = database.document_chunks

    async def replace_document(self, owner_id: str, workspace_id: str, document_id: str, document_name: str, chunks: list[TextChunk]) -> None:
        await self.collection.delete_many({"owner_id": owner_id, "workspace_id": workspace_id, "document_id": document_id})
        if not chunks:
            return
        now = datetime.now(UTC)
        await self.collection.insert_many([{"owner_id": owner_id, "workspace_id": workspace_id, "document_id": document_id, "document_name": document_name, "chunk_id": str(chunk.chunk_index), "page_number": chunk.page_number, "heading": chunk.heading, "source_type": "document", "text": chunk.text, "created_at": now} for chunk in chunks], ordered=True)

    async def keyword_search(self, owner_id: str, workspace_id: str, query: str, document_ids: list[str] | None, source_types: list[str] | None, limit: int) -> list[dict]:
        filters: dict = {"owner_id": owner_id, "workspace_id": workspace_id, "$text": {"$search": query}}
        if document_ids:
            filters["document_id"] = {"$in": document_ids}
        if source_types:
            filters["source_type"] = {"$in": source_types}
        projection = {"score": {"$meta": "textScore"}, "owner_id": 0, "workspace_id": 0, "_id": 0}
        bounded_limit = min(max(limit, 1), 30)
        try:
            cursor = self.collection.find(filters, projection).sort([("score", {"$meta": "textScore"})]).limit(bounded_limit)
            return [item async for item in cursor]
        except OperationFailure:
            terms = list(dict.fromkeys(term for term in re.findall(r"[\w-]{2,}", query.casefold())[:10]))
            lexical: dict = {"owner_id": owner_id, "workspace_id": workspace_id}
            if document_ids:
                lexical["document_id"] = {"$in": document_ids}
            if source_types:
                lexical["source_type"] = {"$in": source_types}
            if terms:
                lexical["$or"] = [{"text": {"$regex": re.escape(term), "$options": "i"}} for term in terms]
            cursor = self.collection.find(lexical, {"owner_id": 0, "workspace_id": 0, "_id": 0}).limit(200)
            items = [item async for item in cursor]
            for item in items:
                text = str(item.get("text", "")).casefold()
                item["score"] = float(sum(text.count(term) for term in terms)) if terms else 0.0
            return sorted(items, key=lambda item: item["score"], reverse=True)[:bounded_limit]

    async def page_search(
        self,
        owner_id: str,
        workspace_id: str,
        page_numbers: list[int],
        document_ids: list[str] | None,
        source_types: list[str] | None,
        limit: int,
    ) -> list[dict]:
        filters: dict = {
            "owner_id": owner_id,
            "workspace_id": workspace_id,
            "page_number": {"$in": page_numbers},
        }
        if document_ids:
            filters["document_id"] = {"$in": document_ids}
        if source_types:
            filters["source_type"] = {"$in": source_types}
        cursor = self.collection.find(filters, {"owner_id": 0, "workspace_id": 0, "_id": 0}).sort([("page_number", 1), ("chunk_id", 1)]).limit(min(max(limit, 1), 40))
        items = [item async for item in cursor]
        for item in items:
            item["score"] = 10.0
        return items

    async def overview_search(
        self,
        owner_id: str,
        workspace_id: str,
        document_ids: list[str] | None,
        source_types: list[str] | None,
        limit: int,
    ) -> list[dict]:
        filters: dict = {"owner_id": owner_id, "workspace_id": workspace_id}
        if document_ids:
            filters["document_id"] = {"$in": document_ids}
        if source_types:
            filters["source_type"] = {"$in": source_types}
        cursor = self.collection.find(filters, {"owner_id": 0, "workspace_id": 0, "_id": 0}).sort([("document_id", 1), ("page_number", 1), ("chunk_id", 1)]).limit(240)
        items = [item async for item in cursor]
        bounded = min(max(limit, 1), 18)
        if len(items) <= bounded:
            selected = items
        elif bounded == 1:
            selected = [items[0]]
        else:
            selected = [items[round(index * (len(items) - 1) / (bounded - 1))] for index in range(bounded)]
        for item in selected:
            item["score"] = 1.0
        return selected

    async def delete_document(self, owner_id: str, workspace_id: str, document_id: str) -> None:
        await self.collection.delete_many({"owner_id": owner_id, "workspace_id": workspace_id, "document_id": document_id})

    async def replace_payloads(self, owner_id: str, workspace_id: str, source_id: str, payloads: list[dict]) -> None:
        await self.collection.delete_many({"owner_id": owner_id, "workspace_id": workspace_id, "document_id": source_id})
        if payloads: await self.collection.insert_many(payloads, ordered=True)
