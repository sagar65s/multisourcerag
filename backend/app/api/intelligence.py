from fastapi import APIRouter, BackgroundTasks, Depends, Query, Request, Response, status

from app.core.config import Settings, get_settings
from app.core.rate_limit import limiter
from app.core.security import AuthenticatedUser, current_user
from app.database.mongodb import get_database
from app.repositories.intelligence import IntelligenceRepository
from app.repositories.workspaces import WorkspaceRepository
from app.schemas.intelligence import IntelligenceArtifactView, IntelligenceRequest
from app.services.intelligence_service import process_intelligence
from app.services.job_dispatcher import InProcessJobDispatcher


router = APIRouter(prefix="/intelligence", tags=["document intelligence"])


@router.post("", response_model=IntelligenceArtifactView, status_code=status.HTTP_202_ACCEPTED)
@limiter.limit("10/minute")
async def generate_intelligence(request: Request, response: Response, payload: IntelligenceRequest, background_tasks: BackgroundTasks, user: AuthenticatedUser = Depends(current_user), settings: Settings = Depends(get_settings)) -> IntelligenceArtifactView:
    await WorkspaceRepository(get_database()).get_owned(user.uid, payload.workspace_id)
    artifact = await IntelligenceRepository(get_database()).create(user.uid, payload)
    await InProcessJobDispatcher(background_tasks).enqueue(user.uid, "document_intelligence", artifact.id, payload.tool.value.replace("_", " "), process_intelligence, user.uid, artifact.id, settings, workspace_id=payload.workspace_id)
    return artifact


@router.get("", response_model=list[IntelligenceArtifactView])
async def list_intelligence(workspace_id: str | None = Query(default=None), limit: int = Query(default=30, ge=1, le=100), skip: int = Query(default=0, ge=0), user: AuthenticatedUser = Depends(current_user)) -> list[IntelligenceArtifactView]:
    if workspace_id:
        await WorkspaceRepository(get_database()).get_owned(user.uid, workspace_id)
    return await IntelligenceRepository(get_database()).list_owned(user.uid, workspace_id, limit, skip)


@router.get("/{artifact_id}", response_model=IntelligenceArtifactView)
async def get_intelligence(artifact_id: str, user: AuthenticatedUser = Depends(current_user)) -> IntelligenceArtifactView:
    return IntelligenceRepository.view(await IntelligenceRepository(get_database()).get_owned(user.uid, artifact_id))


@router.delete("/{artifact_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_intelligence(artifact_id: str, user: AuthenticatedUser = Depends(current_user)) -> Response:
    await IntelligenceRepository(get_database()).delete(user.uid, artifact_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
