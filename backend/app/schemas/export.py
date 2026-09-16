from enum import StrEnum

from pydantic import BaseModel


class ExportSource(StrEnum):
    CONVERSATION = "conversation"
    RESEARCH = "research"
    INTELLIGENCE = "intelligence"
    SAVED_ANSWER = "saved_answer"


class ExportFormat(StrEnum):
    PDF = "pdf"
    DOCX = "docx"
    MARKDOWN = "markdown"
    TXT = "txt"


class ExportRequest(BaseModel):
    source_type: ExportSource
    source_id: str
    format: ExportFormat
    include_citations: bool = True
