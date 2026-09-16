from datetime import UTC, datetime

from bson import ObjectId
from fastapi import HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.repositories.conversations import ConversationRepository
from app.schemas.chat import BookmarkView, FeedbackCreate, SavedAnswerView


class SavedRepository:
    def __init__(self, database: AsyncIOMotorDatabase) -> None:
        self.database = database

    @staticmethod
    def saved_view(item: dict) -> SavedAnswerView:
        return SavedAnswerView(id=str(item["_id"]), conversation_id=item["conversation_id"], message_id=item["message_id"], workspace_id=item.get("workspace_id"), question=item["question"], answer=item["answer"], sources=item.get("sources", []), created_at=item["created_at"])

    @staticmethod
    def bookmark_view(item: dict) -> BookmarkView:
        return BookmarkView(id=str(item["_id"]), conversation_id=item["conversation_id"], message_id=item["message_id"], workspace_id=item.get("workspace_id"), source=item["source"], note=item.get("note", ""), created_at=item["created_at"])

    async def _owned_assistant_message(self, owner_id: str, message_id: str) -> tuple[dict, dict]:
        if not ObjectId.is_valid(message_id):
            raise HTTPException(status_code=404, detail="Assistant message not found")
        message = await self.database.messages.find_one({"_id": ObjectId(message_id), "owner_id": owner_id, "role": "assistant"})
        if message is None:
            raise HTTPException(status_code=404, detail="Assistant message not found")
        conversation = await ConversationRepository(self.database).get_owned(owner_id, message["conversation_id"])
        return message, conversation

    async def save_answer(self, owner_id: str, message_id: str) -> SavedAnswerView:
        message, conversation = await self._owned_assistant_message(owner_id, message_id)
        previous = await self.database.messages.find_one({"owner_id": owner_id, "conversation_id": message["conversation_id"], "role": "user", "created_at": {"$lte": message["created_at"]}}, sort=[("created_at", -1)])
        now = datetime.now(UTC)
        item = {"owner_id": owner_id, "conversation_id": message["conversation_id"], "message_id": message_id, "workspace_id": conversation.get("workspace_id"), "question": previous["content"] if previous else conversation["title"], "answer": message["content"], "sources": message.get("sources", []), "created_at": now}
        existing = await self.database.saved_answers.find_one({"owner_id": owner_id, "message_id": message_id})
        if existing:
            return self.saved_view(existing)
        result = await self.database.saved_answers.insert_one(item); item["_id"] = result.inserted_id
        return self.saved_view(item)

    async def list_answers(self, owner_id: str, limit: int, skip: int) -> list[SavedAnswerView]:
        cursor = self.database.saved_answers.find({"owner_id": owner_id}).sort("created_at", -1).skip(skip).limit(limit)
        return [self.saved_view(item) async for item in cursor]

    async def delete_answer(self, owner_id: str, saved_id: str) -> None:
        if not ObjectId.is_valid(saved_id): raise HTTPException(status_code=404, detail="Saved answer not found")
        result = await self.database.saved_answers.delete_one({"_id": ObjectId(saved_id), "owner_id": owner_id})
        if result.deleted_count == 0: raise HTTPException(status_code=404, detail="Saved answer not found")

    async def bookmark(self, owner_id: str, message_id: str, source_id: str, note: str) -> BookmarkView:
        message, conversation = await self._owned_assistant_message(owner_id, message_id)
        source = next((item for item in message.get("sources", []) if item.get("id") == source_id), None)
        if source is None: raise HTTPException(status_code=404, detail="Citation not found in this answer")
        existing = await self.database.bookmarks.find_one({"owner_id": owner_id, "message_id": message_id, "source.id": source_id})
        if existing: return self.bookmark_view(existing)
        item = {"owner_id": owner_id, "conversation_id": message["conversation_id"], "message_id": message_id, "workspace_id": conversation.get("workspace_id"), "source": source, "note": note.strip(), "created_at": datetime.now(UTC)}
        result = await self.database.bookmarks.insert_one(item); item["_id"] = result.inserted_id
        return self.bookmark_view(item)

    async def list_bookmarks(self, owner_id: str, limit: int, skip: int) -> list[BookmarkView]:
        cursor = self.database.bookmarks.find({"owner_id": owner_id}).sort("created_at", -1).skip(skip).limit(limit)
        return [self.bookmark_view(item) async for item in cursor]

    async def delete_bookmark(self, owner_id: str, bookmark_id: str) -> None:
        if not ObjectId.is_valid(bookmark_id): raise HTTPException(status_code=404, detail="Bookmark not found")
        result = await self.database.bookmarks.delete_one({"_id": ObjectId(bookmark_id), "owner_id": owner_id})
        if result.deleted_count == 0: raise HTTPException(status_code=404, detail="Bookmark not found")

    async def feedback(self, owner_id: str, message_id: str, payload: FeedbackCreate) -> None:
        message, _ = await self._owned_assistant_message(owner_id, message_id)
        await self.database.feedback.update_one({"owner_id": owner_id, "message_id": message_id}, {"$set": {"conversation_id": message["conversation_id"], "helpful": payload.helpful, "reasons": [item.value for item in payload.reasons], "updated_at": datetime.now(UTC)}}, upsert=True)
