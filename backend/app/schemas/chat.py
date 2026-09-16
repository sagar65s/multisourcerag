from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field

from app.rag.query_router import QueryMode


class ChatRequest(BaseModel):
    query: str = Field(min_length=1, max_length=8000)
    mode: QueryMode = QueryMode.AUTO
    conversation_id: str | None = None
    workspace_id: str | None = None
    document_ids: list[str] | None = Field(default=None, max_length=25)
    website_ids: list[str] | None = Field(default=None, max_length=25)
    language: str = Field(default="English", pattern="^(English|Tamil|Hindi)$")


class MessageRole(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"


class ConversationView(BaseModel):
    id: str
    title: str
    workspace_id: str | None = None
    mode: QueryMode
    language: str
    message_count: int = 0
    last_message_preview: str = ""
    created_at: datetime
    updated_at: datetime


class MessageView(BaseModel):
    id: str
    conversation_id: str
    role: MessageRole
    content: str
    sources: list[dict] = Field(default_factory=list)
    evidence_status: str | None = None
    provider: str | None = None
    created_at: datetime


class ConversationRename(BaseModel):
    title: str = Field(min_length=2, max_length=120)


class FeedbackReason(StrEnum):
    INCORRECT = "incorrect"
    OUTDATED = "outdated"
    IRRELEVANT = "irrelevant"
    MISSING_CITATION = "missing_citation"
    INCOMPLETE = "incomplete"


class FeedbackCreate(BaseModel):
    helpful: bool
    reasons: list[FeedbackReason] = Field(default_factory=list, max_length=5)


class SavedAnswerCreate(BaseModel):
    message_id: str


class SavedAnswerView(BaseModel):
    id: str
    conversation_id: str
    message_id: str
    workspace_id: str | None = None
    question: str
    answer: str
    sources: list[dict] = Field(default_factory=list)
    created_at: datetime


class BookmarkCreate(BaseModel):
    message_id: str
    source_id: str = Field(pattern=r"^S\d+$")
    note: str = Field(default="", max_length=500)


class BookmarkView(BaseModel):
    id: str
    conversation_id: str
    message_id: str
    workspace_id: str | None = None
    source: dict
    note: str = ""
    created_at: datetime
