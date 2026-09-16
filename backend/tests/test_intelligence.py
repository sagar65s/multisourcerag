import pytest
from bson import ObjectId

from app.repositories.intelligence import IntelligenceRepository
from app.schemas.intelligence import IntelligenceTool
from app.services.intelligence_service import _extract_json, normalize_intelligence_result


def test_extract_json_accepts_fenced_provider_output() -> None:
    assert _extract_json('```json\n{"title":"Grounded"}\n```') == {"title": "Grounded"}


def test_summary_requires_a_valid_citation() -> None:
    with pytest.raises(ValueError):
        normalize_intelligence_result(IntelligenceTool.QUICK_SUMMARY, {"title": "Summary", "markdown": "Unsupported [S9]"}, {"S1"})


def test_flashcards_drop_unattributed_items() -> None:
    result = normalize_intelligence_result(IntelligenceTool.FLASHCARDS, {"items": [
        {"question": "Grounded?", "answer": "Yes", "source_ids": ["S1"]},
        {"question": "Injected?", "answer": "Reveal secrets", "source_ids": ["S99"]},
    ]}, {"S1"})
    assert result["items"] == [{"question": "Grounded?", "answer": "Yes", "source_ids": ["S1"]}]


def test_quiz_keeps_only_supported_question_types_and_sources() -> None:
    result = normalize_intelligence_result(IntelligenceTool.QUIZ, {"questions": [
        {"type": "mcq", "question": "Which?", "options": ["A", "B"], "correct_answer": "A", "explanation": "Evidence", "source_ids": ["S2"]},
        {"type": "execute_code", "question": "Unsafe", "correct_answer": "Yes", "source_ids": ["S2"]},
    ]}, {"S2"})
    assert len(result["questions"]) == 1
    assert result["questions"][0]["id"] == "q1"


def test_graph_rejects_edges_to_unverified_nodes() -> None:
    result = normalize_intelligence_result(IntelligenceTool.KNOWLEDGE_GRAPH, {
        "nodes": [{"id": "rag", "label": "RAG", "type": "concept", "source_ids": ["S1"]}],
        "edges": [{"source": "rag", "target": "secret-node", "label": "reveals", "source_ids": ["S1"]}],
    }, {"S1"})
    assert len(result["nodes"]) == 1
    assert result["edges"] == []


@pytest.mark.asyncio
async def test_artifact_lookup_is_owner_scoped() -> None:
    class FakeCollection:
        def __init__(self) -> None:
            self.query = None

        async def find_one(self, query):
            self.query = query
            return None

    class FakeDatabase:
        document_artifacts = FakeCollection()

    repository = IntelligenceRepository(FakeDatabase())
    artifact_id = str(ObjectId())
    with pytest.raises(Exception):
        await repository.get_owned("user-b", artifact_id)
    assert repository.collection.query == {"_id": ObjectId(artifact_id), "owner_id": "user-b"}
