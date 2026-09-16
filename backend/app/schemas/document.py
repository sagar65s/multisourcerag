from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel


class ProcessingStatus(StrEnum):
    QUEUED = "queued"
    VALIDATING = "validating"
    SECURITY_CHECK = "security_check"
    EXTRACTING = "extracting"
    OCR = "ocr"
    CLEANING = "cleaning"
    CHUNKING = "chunking"
    EMBEDDING = "embedding"
    INDEXING = "indexing"
    COMPLETED = "completed"
    FAILED = "failed"


class DocumentView(BaseModel):
    id: str
    workspace_id: str
    original_name: str
    media_type: str
    size_bytes: int
    page_count: int = 0
    chunk_count: int = 0
    ocr_used: bool = False
    status: ProcessingStatus
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime


class UploadBatchResponse(BaseModel):
    documents: list[DocumentView]

