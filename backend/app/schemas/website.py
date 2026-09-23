from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field, HttpUrl, field_validator

from app.schemas.document import ProcessingStatus


class CrawlScope(StrEnum):
    SINGLE = "single"
    SELECTED = "selected"
    FULL = "full"


class WebsiteCreate(BaseModel):
    workspace_id: str
    # A normal URL/domain is used directly. A plain website name is resolved
    # through public search by the API before normal SSRF validation.
    url: str = Field(min_length=2, max_length=500)
    scope: CrawlScope = CrawlScope.SINGLE
    selected_urls: list[HttpUrl] = Field(default_factory=list, max_length=25)
    max_depth: int = Field(default=2, ge=0, le=3)
    max_pages: int = Field(default=20, ge=1, le=50)

    @field_validator("url", mode="before")
    @classmethod
    def normalize_primary_url(cls, value: object) -> object:
        if isinstance(value, str):
            compact = " ".join(value.split())
            if "://" not in compact and ("." in compact or compact.casefold().startswith("localhost")):
                return f"https://{compact}"
            return compact
        return value

    @field_validator("selected_urls", mode="before")
    @classmethod
    def normalize_selected_urls(cls, value: object) -> object:
        if not isinstance(value, list):
            return value
        return [f"https://{item.strip()}" if isinstance(item, str) and "://" not in item.strip() else item for item in value]


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
    analysis_method: str = "direct"
    source_notice: str | None = None
    created_at: datetime
    updated_at: datetime
