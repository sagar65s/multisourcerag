from fastapi import APIRouter, BackgroundTasks, Depends, Query, Request, Response, status

from app.core.config import Settings, get_settings
from app.core.security import AuthenticatedUser, current_user
from app.core.ssrf import validate_public_url
from app.database.mongodb import get_database
from app.repositories.websites import WebsiteRepository
from app.repositories.workspaces import WorkspaceRepository
from app.schemas.website import WebsiteCreate, WebsiteView
from app.services.website_service import delete_website, process_website
from app.services.audit_service import audit_event
from app.services.job_dispatcher import InProcessJobDispatcher
from app.core.rate_limit import limiter

router = APIRouter(prefix="/websites", tags=["websites"])


@router.post("", response_model=WebsiteView, status_code=status.HTTP_202_ACCEPTED)
@limiter.limit("10/minute")
async def add_website(request: Request, response: Response, payload: WebsiteCreate, background_tasks: BackgroundTasks, user: AuthenticatedUser = Depends(current_user), settings: Settings = Depends(get_settings)) -> WebsiteView:
    await WorkspaceRepository(get_database()).get_owned(user.uid, payload.workspace_id)
    await validate_public_url(str(payload.url))
    for selected in payload.selected_urls: await validate_public_url(str(selected))
    item = await WebsiteRepository(get_database()).create(user.uid, payload)
    await InProcessJobDispatcher(background_tasks).enqueue(user.uid, "website_ingestion", item.id, item.domain, process_website, user.uid, item.id, settings, workspace_id=payload.workspace_id)
    await audit_event(user.uid, "website_add", resource_type="website", resource_id=item.id, metadata={"scope": payload.scope.value})
    return item


@router.get("", response_model=list[WebsiteView])
async def list_websites(workspace_id: str | None = Query(default=None), limit: int = Query(default=30, ge=1, le=100), skip: int = Query(default=0, ge=0), user: AuthenticatedUser = Depends(current_user)) -> list[WebsiteView]:
    if workspace_id: await WorkspaceRepository(get_database()).get_owned(user.uid, workspace_id)
    return await WebsiteRepository(get_database()).list_owned(user.uid, workspace_id, limit, skip)


@router.get("/{website_id}", response_model=WebsiteView)
async def get_website(website_id: str, user: AuthenticatedUser = Depends(current_user)) -> WebsiteView:
    return WebsiteRepository.view(await WebsiteRepository(get_database()).get_owned(user.uid, website_id))


@router.post("/{website_id}/reindex", response_model=WebsiteView, status_code=status.HTTP_202_ACCEPTED)
@limiter.limit("6/minute")
async def reindex_website(request: Request, response: Response, website_id: str, background_tasks: BackgroundTasks, user: AuthenticatedUser = Depends(current_user), settings: Settings = Depends(get_settings)) -> WebsiteView:
    item = await WebsiteRepository(get_database()).get_owned(user.uid, website_id); await InProcessJobDispatcher(background_tasks).enqueue(user.uid, "website_reindex", website_id, item.get("domain", "Website"), process_website, user.uid, website_id, settings, workspace_id=item["workspace_id"]); return WebsiteRepository.view(item)


@router.delete("/{website_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_website(website_id: str, user: AuthenticatedUser = Depends(current_user), settings: Settings = Depends(get_settings)) -> Response:
    await delete_website(user.uid, website_id, settings); await audit_event(user.uid, "website_delete", resource_type="website", resource_id=website_id); return Response(status_code=status.HTTP_204_NO_CONTENT)
