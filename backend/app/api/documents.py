from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Query, Request, Response, UploadFile, status

from app.core.config import Settings, get_settings
from app.core.security import AuthenticatedUser, current_user
from app.database.mongodb import get_database
from app.repositories.documents import DocumentRepository
from app.repositories.workspaces import WorkspaceRepository
from app.schemas.document import DocumentView, UploadBatchResponse
from app.services.document_service import delete_document, process_document
from app.services.file_security_service import validate_upload
from app.services.private_storage_service import PrivateStorageService
from app.services.audit_service import audit_event
from app.services.job_dispatcher import InProcessJobDispatcher
from app.core.rate_limit import limiter

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/upload", response_model=UploadBatchResponse, status_code=status.HTTP_202_ACCEPTED)
@limiter.limit("10/minute")
async def upload_documents(
    request: Request,
    response: Response,
    background_tasks: BackgroundTasks,
    workspace_id: str = Form(...),
    files: list[UploadFile] = File(...),
    user: AuthenticatedUser = Depends(current_user),
    settings: Settings = Depends(get_settings),
) -> UploadBatchResponse:
    if not 1 <= len(files) <= 10:
        raise HTTPException(status_code=400, detail="Upload between 1 and 10 files at a time")
    await WorkspaceRepository(get_database()).get_owned(user.uid, workspace_id)
    validated = [await validate_upload(upload, settings.max_upload_bytes) for upload in files]
    repository = DocumentRepository(get_database())
    storage = PrivateStorageService(settings.private_storage_root)
    created: list[DocumentView] = []
    for item in validated:
        stored_path = await storage.save(user.uid, item.extension, item.content)
        document = await repository.create(user.uid, workspace_id, item.original_name, item.media_type, len(item.content), item.extension, stored_path)
        created.append(document)
        await InProcessJobDispatcher(background_tasks).enqueue(user.uid, "document_ingestion", document.id, item.original_name, process_document, user.uid, document.id, settings, workspace_id=workspace_id)
        await audit_event(user.uid, "document_upload", resource_type="document", resource_id=document.id, metadata={"media_type": item.media_type, "size_bytes": len(item.content)})
    return UploadBatchResponse(documents=created)


@router.get("", response_model=list[DocumentView])
async def list_documents(
    workspace_id: str | None = Query(default=None),
    limit: int = Query(default=30, ge=1, le=100),
    skip: int = Query(default=0, ge=0),
    user: AuthenticatedUser = Depends(current_user),
) -> list[DocumentView]:
    if workspace_id:
        await WorkspaceRepository(get_database()).get_owned(user.uid, workspace_id)
    return await DocumentRepository(get_database()).list_owned(user.uid, workspace_id, limit, skip)


@router.get("/{document_id}", response_model=DocumentView)
async def get_document(document_id: str, user: AuthenticatedUser = Depends(current_user)) -> DocumentView:
    return DocumentRepository.view(await DocumentRepository(get_database()).get_owned(user.uid, document_id))


@router.post("/{document_id}/reindex", response_model=DocumentView, status_code=status.HTTP_202_ACCEPTED)
@limiter.limit("6/minute")
async def reindex_document(request: Request, response: Response, document_id: str, background_tasks: BackgroundTasks, user: AuthenticatedUser = Depends(current_user), settings: Settings = Depends(get_settings)) -> DocumentView:
    repository = DocumentRepository(get_database()); item = await repository.get_owned(user.uid, document_id)
    await InProcessJobDispatcher(background_tasks).enqueue(user.uid, "document_reindex", document_id, item["original_name"], process_document, user.uid, document_id, settings, workspace_id=item["workspace_id"])
    return repository.view(item)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_document(document_id: str, user: AuthenticatedUser = Depends(current_user), settings: Settings = Depends(get_settings)) -> Response:
    await delete_document(user.uid, document_id, settings)
    await audit_event(user.uid, "document_delete", resource_type="document", resource_id=document_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
