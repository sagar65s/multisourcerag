from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field, HttpUrl

from app.schemas.document import ProcessingStatus


class CrawlScope(StrEnum):
    SINGLE = "single"
    SELECTED = "selected"
    FULL = "full"


class WebsiteCreate(BaseModel):
    workspace_id: str
    url: HttpUrl
    scope: CrawlScope = CrawlScope.SINGLE
    selected_urls: list[HttpUrl] = Field(default_factory=list, max_length=25)
    max_depth: int = Field(default=2, ge=0, le=3)
    max_pages: int = Field(default=20, ge=1, le=50)


class WebsiteView(BaseModel):
    id: str
    workspace_id: str
    url: str
    domain: str
    title: str | None = None
    meta_description: str | None = None
    content_preview: str | None = None
    scope: CrawlScope
    status: ProcessingStatus
    indexed_pages: int = 0
    chunk_count: int = 0
    important_headings: list[str] = Field(default_factory=list)
    internal_links: list[str] = Field(default_factory=list)
    external_links: list[str] = Field(default_factory=list)
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime
