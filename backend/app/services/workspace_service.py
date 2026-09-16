from app.core.config import Settings
from app.database.mongodb import get_database
from app.repositories.workspaces import WorkspaceRepository
from app.services.document_service import delete_document
from app.services.website_service import delete_website


async def delete_workspace_cascade(owner_id: str, workspace_id: str, settings: Settings) -> None:
    await WorkspaceRepository(get_database()).get_owned(owner_id, workspace_id)
    documents = [str(item["_id"]) async for item in get_database().documents.find({"owner_id": owner_id, "workspace_id": workspace_id}, {"_id": 1})]
    websites = [str(item["_id"]) async for item in get_database().website_sources.find({"owner_id": owner_id, "workspace_id": workspace_id}, {"_id": 1})]
    for document_id in documents: await delete_document(owner_id, document_id, settings)
    for website_id in websites: await delete_website(owner_id, website_id, settings)
    for collection in ("conversations", "research_sessions", "document_artifacts", "saved_answers", "bookmarks", "processing_jobs"):
        await get_database()[collection].delete_many({"owner_id": owner_id, "workspace_id": workspace_id})
    await WorkspaceRepository(get_database()).delete(owner_id, workspace_id)
