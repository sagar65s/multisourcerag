from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field, model_validator


class SessionKind(StrEnum):
    DEEP_RESEARCH = "deep_research"
    # Read-only legacy values keep old history records loadable. No routes can
    # create these session types anymore.
    COMPARE = "compare"
    TIMELINE = "timeline"


class ResearchStage(StrEnum):
    PLANNING = "planning"
    SEARCHING = "searching"
    READING_SOURCES = "reading_sources"
    CROSS_CHECKING = "cross_checking"
    SYNTHESIZING = "synthesizing"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    FAILED = "failed"


class DeepResearchRequest(BaseModel):
    question: str = Field(min_length=10, max_length=4000)
    workspace_id: str | None = None
    include_private: bool = True
    include_web: bool = True
    max_queries: int = Field(default=3, ge=2, le=5)
    language: str = Field(default="English", pattern="^(English|Tamil|Hindi)$")

    @model_validator(mode="after")
    def validate_sources(self):
        if not self.include_private and not self.include_web: raise ValueError("Select at least one evidence source")
        if self.include_private and not self.workspace_id: raise ValueError("A workspace is required for private research")
        return self


class ResearchSessionView(BaseModel):
    id: str
    kind: SessionKind
    title: str
    status: ResearchStage
    queries: list[str] = Field(default_factory=list)
    source_count: int = 0
    sources: list[dict] = Field(default_factory=list)
    conflicts: list[dict] = Field(default_factory=list)
    output_markdown: str | None = None
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime
