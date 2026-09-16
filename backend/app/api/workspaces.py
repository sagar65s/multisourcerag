from fastapi import APIRouter, Depends, Query, Response, status
from app.core.config import Settings, get_settings

from app.core.security import AuthenticatedUser, current_user
from app.database.mongodb import get_database
from app.repositories.workspaces import WorkspaceRepository
from app.schemas.workspace import WorkspaceCreate, WorkspaceUpdate, WorkspaceView
from app.services.workspace_service import delete_workspace_cascade
from app.services.audit_service import audit_event

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


@router.get("", response_model=list[WorkspaceView])
async def list_workspaces(
    limit: int = Query(default=20, ge=1, le=100),
    skip: int = Query(default=0, ge=0),
    user: AuthenticatedUser = Depends(current_user),
) -> list[WorkspaceView]:
    return await WorkspaceRepository(get_database()).list_for_owner(user.uid, limit, skip)


@router.post("", response_model=WorkspaceView, status_code=status.HTTP_201_CREATED)
async def create_workspace(payload: WorkspaceCreate, user: AuthenticatedUser = Depends(current_user)) -> WorkspaceView:
    item = await WorkspaceRepository(get_database()).create(user.uid, payload)
    await audit_event(user.uid, "workspace_create", resource_type="workspace", resource_id=item.id)
    return item


@router.patch("/{workspace_id}", response_model=WorkspaceView)
async def update_workspace(workspace_id: str, payload: WorkspaceUpdate, user: AuthenticatedUser = Depends(current_user)) -> WorkspaceView:
    item = await WorkspaceRepository(get_database()).update(user.uid, workspace_id, payload)
    await audit_event(user.uid, "workspace_update", resource_type="workspace", resource_id=workspace_id)
    return item


@router.delete("/{workspace_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workspace(workspace_id: str, user: AuthenticatedUser = Depends(current_user), settings: Settings = Depends(get_settings)) -> Response:
    await delete_workspace_cascade(user.uid, workspace_id, settings)
    await audit_event(user.uid, "workspace_delete", resource_type="workspace", resource_id=workspace_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
