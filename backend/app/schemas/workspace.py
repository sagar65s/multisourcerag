from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class WorkspaceCreate(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    description: str = Field(default="", max_length=500)


class WorkspaceUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=80)
    description: str | None = Field(default=None, max_length=500)


class WorkspaceView(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: str
    name: str
    description: str
    document_count: int = 0
    website_count: int = 0
    created_at: datetime
    updated_at: datetime

