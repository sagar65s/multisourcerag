import pytest

from app.core.config import Settings
from app.schemas.chat import ChatRequest
from app.services import retrieval_service
from app.services.retrieval_service import RetrievalService, _is_overview_query, requested_pages


def test_page_references_support_single_page_and_bounded_ranges() -> None:
    assert requested_pages("Explain page 27 from this PDF") == [27]
    assert requested_pages("What is written on 27 page?") == [27]
    assert requested_pages("பக்கம் 42-ல் என்ன உள்ளது?") == [42]
    assert requested_pages("पृष्ठ 12 समझाइए") == [12]
    assert requested_pages("Compare pages 3-6") == [3, 4, 5, 6]
    assert requested_pages("Read pages 1 through 40") == list(range(1, 21))


def test_chat_request_accepts_separate_document_and_website_selection() -> None:
    payload = ChatRequest(
        query="Explain this source",
        workspace_id="workspace-1",
        document_ids=["document-1"],
        website_ids=["website-1"],
    )
    assert payload.document_ids == ["document-1"]
    assert payload.website_ids == ["website-1"]


def test_repository_and_website_summary_queries_use_full_source_sampling() -> None:
    assert _is_overview_query("What is this repository?")
    assert _is_overview_query("Give me a website overview")


@pytest.mark.asyncio
async def test_page_question_reads_exact_selected_document_page(monkeypatch) -> None:
    class Chunks:
        async def count_documents(self, _filters, limit=0):
            assert limit == 1
            return 1

    class Database:
        document_chunks = Chunks()

    captured: dict = {}

    class Repository:
        def __init__(self, _database):
            pass

        async def page_search(self, owner_id, workspace_id, pages, document_ids, source_types, limit):
            captured.update({"owner": owner_id, "workspace": workspace_id, "pages": pages, "ids": document_ids, "types": source_types, "limit": limit})
            return [{
                "document_id": "doc-7",
                "document_name": "Manual.pdf",
                "chunk_id": "42",
                "text": "The exact content printed on page forty two.",
                "page_number": 42,
                "heading": "Installation",
                "source_type": "document",
                "source_url": None,
                "score": 10.0,
            }]

    monkeypatch.setattr(retrieval_service, "get_database", lambda: Database())
    monkeypatch.setattr(retrieval_service, "ChunkRepository", Repository)
    result = await RetrievalService(Settings()).retrieve(
        "owner-1",
        "workspace-1",
        "What does page 42 say?",
        ["doc-7"],
        ["document"],
    )
    assert captured["pages"] == [42]
    assert captured["ids"] == ["doc-7"]
    assert captured["types"] == ["document"]
    assert captured["limit"] == 40
    assert result.evidence[0].page_number == 42
    assert "exact content" in result.evidence[0].text
