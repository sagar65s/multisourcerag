from datetime import UTC, datetime

from bson import ObjectId
from fastapi import HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.rag.query_router import QueryMode
from app.schemas.chat import ConversationView, MessageRole, MessageView


class ConversationRepository:
    def __init__(self, database: AsyncIOMotorDatabase) -> None:
        self.database = database
        self.conversations = database.conversations
        self.messages = database.messages

    @staticmethod
    def conversation_view(item: dict) -> ConversationView:
        return ConversationView(id=str(item["_id"]), title=item["title"], workspace_id=item.get("workspace_id"), mode=item.get("mode", QueryMode.AUTO.value), language=item.get("language", "English"), message_count=item.get("message_count", 0), last_message_preview=item.get("last_message_preview", ""), created_at=item["created_at"], updated_at=item["updated_at"])

    @staticmethod
    def message_view(item: dict) -> MessageView:
        return MessageView(id=str(item["_id"]), conversation_id=item["conversation_id"], role=item["role"], content=item["content"], sources=item.get("sources", []), evidence_status=item.get("evidence_status"), provider=item.get("provider"), created_at=item["created_at"])

    async def create(self, owner_id: str, title: str, workspace_id: str | None, mode: QueryMode, language: str) -> ConversationView:
        now = datetime.now(UTC)
        item = {"owner_id": owner_id, "title": title.strip()[:120] or "New conversation", "workspace_id": workspace_id, "mode": mode.value, "language": language, "message_count": 0, "last_message_preview": "", "created_at": now, "updated_at": now}
        result = await self.conversations.insert_one(item); item["_id"] = result.inserted_id
        return self.conversation_view(item)

    async def get_owned(self, owner_id: str, conversation_id: str) -> dict:
        if not ObjectId.is_valid(conversation_id):
            raise HTTPException(status_code=404, detail="Conversation not found")
        item = await self.conversations.find_one({"_id": ObjectId(conversation_id), "owner_id": owner_id})
        if item is None:
            raise HTTPException(status_code=404, detail="Conversation not found")
        return item

    async def list_owned(self, owner_id: str, search: str | None, limit: int, skip: int) -> list[ConversationView]:
        query: dict = {"owner_id": owner_id}
        if search:
            query["title"] = {"$regex": re_escape(search[:100]), "$options": "i"}
        cursor = self.conversations.find(query).sort("updated_at", -1).skip(skip).limit(limit)
        return [self.conversation_view(item) async for item in cursor]

    async def add_message(self, owner_id: str, conversation_id: str, role: MessageRole, content: str, sources: list[dict] | None = None, evidence_status: str | None = None, provider: str | None = None) -> MessageView:
        await self.get_owned(owner_id, conversation_id)
        now = datetime.now(UTC)
        item = {"owner_id": owner_id, "conversation_id": conversation_id, "role": role.value, "content": content, "sources": sources or [], "evidence_status": evidence_status, "provider": provider, "created_at": now}
        result = await self.messages.insert_one(item); item["_id"] = result.inserted_id
        await self.conversations.update_one({"_id": ObjectId(conversation_id), "owner_id": owner_id}, {"$inc": {"message_count": 1}, "$set": {"updated_at": now, "last_message_preview": content[:180]}})
        return self.message_view(item)

    async def list_messages(self, owner_id: str, conversation_id: str, limit: int = 100) -> list[MessageView]:
        await self.get_owned(owner_id, conversation_id)
        cursor = self.messages.find({"owner_id": owner_id, "conversation_id": conversation_id}).sort("created_at", 1).limit(min(max(limit, 1), 200))
        return [self.message_view(item) async for item in cursor]

    async def memory(self, owner_id: str, conversation_id: str, limit: int = 8) -> list[dict]:
        await self.get_owned(owner_id, conversation_id)
        cursor = self.messages.find({"owner_id": owner_id, "conversation_id": conversation_id}, {"role": 1, "content": 1}).sort("created_at", -1).limit(limit)
        items = [item async for item in cursor]
        return [{"role": item["role"], "content": item["content"][:4000]} for item in reversed(items)]

    async def rename(self, owner_id: str, conversation_id: str, title: str) -> ConversationView:
        item = await self.get_owned(owner_id, conversation_id)
        await self.conversations.update_one({"_id": item["_id"], "owner_id": owner_id}, {"$set": {"title": title.strip(), "updated_at": datetime.now(UTC)}})
        return self.conversation_view(await self.get_owned(owner_id, conversation_id))

    async def delete(self, owner_id: str, conversation_id: str) -> None:
        item = await self.get_owned(owner_id, conversation_id)
        scope = {"owner_id": owner_id, "conversation_id": conversation_id}
        await self.database.saved_answers.delete_many(scope)
        await self.database.bookmarks.delete_many(scope)
        await self.database.feedback.delete_many(scope)
        await self.messages.delete_many(scope)
        await self.conversations.delete_one({"_id": item["_id"], "owner_id": owner_id})


def re_escape(value: str) -> str:
    import re
    return re.escape(value)
