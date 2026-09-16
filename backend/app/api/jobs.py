from fastapi import APIRouter, BackgroundTasks, Depends, Query, Request, Response, status

from app.core.config import Settings, get_settings
from app.core.rate_limit import limiter
from app.core.security import AuthenticatedUser, current_user
from app.schemas.job import JobView
from app.services.audit_service import audit_event
from app.services.job_control_service import cancel_owned_job, list_owned_jobs, retry_owned_job


router = APIRouter(prefix="/jobs", tags=["processing jobs"])


@router.get("", response_model=list[JobView])
async def list_jobs(limit: int = Query(default=30, ge=1, le=100), skip: int = Query(default=0, ge=0), user: AuthenticatedUser = Depends(current_user)) -> list[JobView]:
    return await list_owned_jobs(user.uid, limit, skip)


@router.post("/{job_id}/cancel", response_model=JobView)
@limiter.limit("20/minute")
async def cancel_job(request: Request, response: Response, job_id: str, user: AuthenticatedUser = Depends(current_user)) -> JobView:
    item = await cancel_owned_job(user.uid, job_id)
    await audit_event(user.uid, "job_cancel", resource_type="processing_job", resource_id=job_id)
    return item


@router.post("/{job_id}/retry", response_model=JobView, status_code=status.HTTP_202_ACCEPTED)
@limiter.limit("10/minute")
async def retry_job(request: Request, response: Response, job_id: str, background_tasks: BackgroundTasks, user: AuthenticatedUser = Depends(current_user), settings: Settings = Depends(get_settings)) -> JobView:
    item = await retry_owned_job(user.uid, job_id, background_tasks, settings)
    await audit_event(user.uid, "job_retry", resource_type="processing_job", resource_id=job_id)
    return item
