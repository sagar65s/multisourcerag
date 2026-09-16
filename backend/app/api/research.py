from fastapi import APIRouter, BackgroundTasks, Depends, Query, Request, Response, status

from app.core.config import Settings, get_settings
from app.core.security import AuthenticatedUser, current_user
from app.database.mongodb import get_database
from app.repositories.research import ResearchRepository
from app.repositories.workspaces import WorkspaceRepository
from app.schemas.research import DeepResearchRequest, ResearchSessionView, SessionKind
from app.services.analysis_service import process_deep_research
from app.services.job_dispatcher import InProcessJobDispatcher
from app.core.rate_limit import limiter

router = APIRouter(prefix="/research", tags=["research"])


@router.post("", response_model=ResearchSessionView, status_code=status.HTTP_202_ACCEPTED)
@limiter.limit("5/minute")
async def start_research(request: Request, response: Response, payload: DeepResearchRequest, background_tasks: BackgroundTasks, user: AuthenticatedUser = Depends(current_user), settings: Settings = Depends(get_settings)) -> ResearchSessionView:
    if payload.include_private and payload.workspace_id: await WorkspaceRepository(get_database()).get_owned(user.uid, payload.workspace_id)
    session = await ResearchRepository(get_database()).create(user.uid, SessionKind.DEEP_RESEARCH, payload.question, payload.model_dump())
    await InProcessJobDispatcher(background_tasks).enqueue(user.uid, "deep_research", session.id, payload.question, process_deep_research, user.uid, session.id, settings, workspace_id=payload.workspace_id); return session


@router.get("", response_model=list[ResearchSessionView])
async def list_research(kind: SessionKind | None = Query(default=None), limit: int = Query(default=20, ge=1, le=100), skip: int = Query(default=0, ge=0), user: AuthenticatedUser = Depends(current_user)) -> list[ResearchSessionView]:
    return await ResearchRepository(get_database()).list_owned(user.uid, kind, limit, skip)


@router.get("/{session_id}", response_model=ResearchSessionView)
async def get_research(session_id: str, user: AuthenticatedUser = Depends(current_user)) -> ResearchSessionView:
    return ResearchRepository.view(await ResearchRepository(get_database()).get_owned(user.uid, session_id))


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_research(session_id: str, user: AuthenticatedUser = Depends(current_user)) -> Response:
    await ResearchRepository(get_database()).delete(user.uid, session_id); return Response(status_code=status.HTTP_204_NO_CONTENT)
