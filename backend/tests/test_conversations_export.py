import io
import inspect
import re
from types import SimpleNamespace

import pymupdf
import pytest
from bson import ObjectId
from fastapi import HTTPException, Response
from starlette.requests import Request

from app.core.config import Settings
from app.core.security import AuthenticatedUser
from app.repositories.conversations import ConversationRepository
from app.repositories.saved import SavedRepository
from app.schemas.chat import ChatRequest
from app.rag.query_router import QueryMode
from app.services.export_service import _docx, _markdown_html, _pdf, _plain
from app.api.chat import _document_only_notice, stream_chat


@pytest.mark.asyncio
async def test_conversation_lookup_is_owner_scoped() -> None:
    class Collection:
        def __init__(self): self.query = None
        async def find_one(self, query): self.query = query; return None
    class Database:
        conversations = Collection(); messages = Collection()
    repository = ConversationRepository(Database())
    conversation_id = str(ObjectId())
    with pytest.raises(HTTPException): await repository.get_owned("user-b", conversation_id)
    assert repository.conversations.query == {"_id": ObjectId(conversation_id), "owner_id": "user-b"}


@pytest.mark.asyncio
async def test_saved_answer_cannot_load_another_users_message() -> None:
    class Collection:
        def __init__(self): self.query = None
        async def find_one(self, query, **kwargs): self.query = query; return None
    class Database:
        messages = Collection()
    repository = SavedRepository(Database())
    message_id = str(ObjectId())
    with pytest.raises(HTTPException): await repository._owned_assistant_message("user-b", message_id)
    assert repository.database.messages.query["owner_id"] == "user-b"
    assert repository.database.messages.query["role"] == "assistant"


def test_private_exports_are_valid_files() -> None:
    text = "# Answer\n\nGrounded result [S1].\n\nதமிழ் · हिंदी"
    pdf = _pdf(text); docx = _docx("Grounded answer", text)
    assert pymupdf.open(stream=pdf, filetype="pdf").page_count >= 1
    assert io.BytesIO(docx).read(2) == b"PK"


def test_plain_export_removes_markdown_heading() -> None:
    assert _plain("# Title\n\nBody") == "Title\n\nBody"


def test_research_markdown_is_formatted_without_raw_stars() -> None:
    markdown = "```markdown\n# Report\n\n## Findings\n\n**Important result**\n\n- First point\n```"
    assert "**" not in _plain(markdown)
    rendered = _markdown_html(markdown)
    assert "<h1>Report</h1>" in rendered
    assert "<strong>Important result</strong>" in rendered
    assert "<li>First point</li>" in rendered
    pdf = pymupdf.open(stream=_pdf(markdown), filetype="pdf")
    extracted = "".join(page.get_text() for page in pdf)
    assert "**" not in extracted
    assert "Important result" in extracted


def test_document_lookup_does_not_shadow_conversation_repository() -> None:
    source = inspect.getsource(stream_chat)
    assert "document_repository = DocumentRepository" in source
    assert re.search(r"^\s*repository\s*=\s*DocumentRepository", source, re.MULTILINE) is None


def test_stream_generator_does_not_shadow_routed_mode() -> None:
    source = inspect.getsource(stream_chat)
    assert "resolved_mode = mode" in source
    assert re.search(r"^\s*mode\s*=\s*QueryMode", source, re.MULTILINE) is None


def test_document_only_notice_never_offers_general_answer() -> None:
    message = _document_only_notice("English")
    assert "does not contain enough information" in message
    assert "did not add a general-knowledge answer" in message


def test_document_mode_has_no_general_fallback_path() -> None:
    source = inspect.getsource(stream_chat)
    assert "if strict_document_only:" in source
    assert "document-retrieval" in source
    assert "if not strict_document_only else []" in source


@pytest.mark.asyncio
async def test_document_mode_without_evidence_never_calls_general_provider(monkeypatch) -> None:
    class Repository:
        async def create(self, *_args):
            return SimpleNamespace(id="conversation-1")

        async def add_message(self, *_args):
            return SimpleNamespace(id="message-1")

    class Workspaces:
        def __init__(self, _database):
            pass

        async def get_owned(self, *_args):
            return {"_id": "workspace-1"}

    class Retrieval:
        def __init__(self, _settings):
            pass

        async def retrieve(self, *_args):
            return SimpleNamespace(evidence=[], status="no_evidence")

    class ProviderManager:
        def __init__(self, _registry):
            raise AssertionError("Document-only no-evidence flow must not call an LLM provider")

    monkeypatch.setattr("app.api.chat.get_database", lambda: object())
    monkeypatch.setattr("app.api.chat.ConversationRepository", lambda _database: Repository())
    monkeypatch.setattr("app.api.chat.WorkspaceRepository", Workspaces)
    monkeypatch.setattr("app.api.chat.RetrievalService", Retrieval)
    monkeypatch.setattr("app.api.chat.LLMProviderManager", ProviderManager)

    endpoint = inspect.unwrap(stream_chat)
    request = Request({"type": "http", "method": "POST", "path": "/api/v1/chat/stream", "headers": []})
    result = await endpoint(
        request=request,
        response=Response(),
        payload=ChatRequest(query="Who founded it?", mode=QueryMode.KNOWLEDGE, workspace_id="workspace-1"),
        user=AuthenticatedUser(uid="user-1", email=None, is_admin=False),
        settings=Settings(),
    )
    chunks = [chunk async for chunk in result.body_iterator]
    stream = "".join(chunk.decode() if isinstance(chunk, bytes) else chunk for chunk in chunks)
    assert "does not contain enough information" in stream
    assert '"evidence_status": "no_evidence"' in stream
    assert "general_answer" not in stream


@pytest.mark.asyncio
@pytest.mark.parametrize("interrupted", [False, True])
async def test_general_chat_stream_can_emit_first_and_final_events(monkeypatch, interrupted) -> None:
    class Repository:
        async def create(self, *_args):
            return SimpleNamespace(id="conversation-1")

        async def add_message(self, *_args):
            return SimpleNamespace(id="message-1")

    class ProviderManager:
        def __init__(self, _registry):
            pass

        async def generate_with_fallback(self, _messages):
            if interrupted:
                raise RuntimeError("hidden provider details")
            return "test-provider", "A complete test answer."

    monkeypatch.setattr("app.api.chat.get_database", lambda: object())
    monkeypatch.setattr("app.api.chat.ConversationRepository", lambda _database: Repository())
    monkeypatch.setattr("app.api.chat.LLMProviderManager", ProviderManager)
    monkeypatch.setattr("app.api.chat.build_llm_registry", lambda _settings: object())

    endpoint = inspect.unwrap(stream_chat)
    request = Request({"type": "http", "method": "POST", "path": "/api/v1/chat/stream", "headers": []})
    result = await endpoint(
        request=request,
        response=Response(),
        payload=ChatRequest(query="Hello", mode=QueryMode.GENERAL),
        user=AuthenticatedUser(uid="user-1", email=None, is_admin=False),
        settings=Settings(),
    )
    chunks = [chunk async for chunk in result.body_iterator]
    stream = "".join(chunk.decode() if isinstance(chunk, bytes) else chunk for chunk in chunks)
    assert 'event: stage\ndata: {"stage": "understanding", "mode": "general"}' in stream
    if interrupted:
        assert "event: error" in stream
        assert "The answer stopped unexpectedly" in stream
        assert "hidden provider details" not in stream
    else:
        assert "A complete test answer." in stream
        assert 'event: complete\ndata: {"evidence_status": "general_answer"' in stream
