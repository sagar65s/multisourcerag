from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field, model_validator


class IntelligenceTool(StrEnum):
    QUICK_SUMMARY = "quick_summary"
    DETAILED_SUMMARY = "detailed_summary"
    KEY_POINTS = "key_points"
    KEYWORDS = "keywords"
    NOTES = "notes"
    FAQ = "faq"
    QA = "qa"
    FLASHCARDS = "flashcards"
    QUIZ = "quiz"
    ENTITIES = "entities"
    IMPORTANT_DATES = "important_dates"
    OVERVIEW = "overview"
    KNOWLEDGE_GRAPH = "knowledge_graph"


class IntelligenceStatus(StrEnum):
    QUEUED = "queued"
    RETRIEVING = "retrieving"
    GENERATING = "generating"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    FAILED = "failed"


class IntelligenceRequest(BaseModel):
    workspace_id: str = Field(min_length=1)
    source_ids: list[str] = Field(min_length=1, max_length=8)
    tool: IntelligenceTool
    language: str = Field(default="English", pattern="^(English|Tamil|Hindi)$")
    item_count: int = Field(default=8, ge=3, le=20)
    notes_style: str = Field(default="revision", pattern="^(quick|detailed|revision|exam|definitions)$")
    quiz_types: list[str] = Field(default_factory=lambda: ["mcq", "true_false", "short_answer"])

    @model_validator(mode="after")
    def validate_options(self):
        self.source_ids = list(dict.fromkeys(self.source_ids))
        allowed = {"mcq", "true_false", "short_answer"}
        self.quiz_types = list(dict.fromkeys(self.quiz_types))
        if not self.quiz_types or any(item not in allowed for item in self.quiz_types):
            raise ValueError("Quiz types must be MCQ, true/false, or short-answer")
        return self


class IntelligenceArtifactView(BaseModel):
    id: str
    workspace_id: str
    source_ids: list[str]
    source_names: list[str] = Field(default_factory=list)
    tool: IntelligenceTool
    status: IntelligenceStatus
    language: str
    result: dict = Field(default_factory=dict)
    citations: list[dict] = Field(default_factory=list)
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime
