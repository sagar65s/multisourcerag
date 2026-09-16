from datetime import datetime
from typing import Literal

from pydantic import BaseModel


JobStatus = Literal["queued", "processing", "cancel_requested", "canceled", "completed", "failed"]


class JobView(BaseModel):
    id: str
    workspace_id: str | None = None
    source_id: str
    source_name: str
    kind: str
    status: JobStatus
    stage: str
    attempt: int = 1
    error_code: str | None = None
    can_cancel: bool
    can_retry: bool
    created_at: datetime
    updated_at: datetime
