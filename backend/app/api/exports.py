from uuid import uuid4

from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response

from app.core.security import AuthenticatedUser, current_user
from app.core.rate_limit import limiter
from app.schemas.export import ExportRequest
from app.services.export_service import export_owned_content
from app.services.audit_service import audit_event

router = APIRouter(prefix="/exports", tags=["exports"])


@router.post("")
@limiter.limit("10/minute")
async def create_export(request: Request, response: Response, payload: ExportRequest, user: AuthenticatedUser = Depends(current_user)) -> Response:
    exported = await export_owned_content(user.uid, payload)
    await audit_event(user.uid, "private_export", resource_type=payload.source_type.value, resource_id=payload.source_id)
    filename = f"multisource-ai-export-{uuid4().hex[:12]}.{exported.extension}"
    return Response(exported.content, media_type=exported.media_type, headers={"Content-Disposition": f'attachment; filename="{filename}"', "Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"})
