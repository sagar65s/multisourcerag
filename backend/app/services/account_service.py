import asyncio

from firebase_admin import auth

from app.core.config import Settings
from app.database.mongodb import get_database
from app.database.qdrant import VectorStore
from app.services.private_storage_service import PrivateStorageService


OWNER_COLLECTIONS = ("users", "user_settings", "workspaces", "documents", "website_sources", "conversations", "messages", "research_sessions", "saved_answers", "bookmarks", "processing_jobs", "document_artifacts", "feedback", "analytics", "audit_logs", "security_logs", "document_chunks")


async def delete_account_data(owner_id: str, settings: Settings) -> None:
    database = get_database()
    indexed_count = await database.document_chunks.count_documents({"owner_id": owner_id}, limit=1)
    if indexed_count:
        await VectorStore(settings).delete_user(owner_id)
    await PrivateStorageService(settings.private_storage_root).delete_owner(owner_id)
    for collection in OWNER_COLLECTIONS:
        await database[collection].delete_many({"uid": owner_id} if collection == "users" else {"owner_id": owner_id})
        if collection in {"audit_logs", "security_logs"}: await database[collection].delete_many({"actor_id": owner_id})
    await asyncio.to_thread(auth.delete_user, owner_id)
