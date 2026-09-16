from app.rag.context_builder import build_context
from app.rag.hybrid_search import Evidence


def test_context_redacts_secret_and_preserves_citation_metadata() -> None:
    evidence = [Evidence(source_id="doc", document_id="doc", document_name="private.pdf", chunk_id="0", text="Finding. api_key=super-secret-value-123", page_number=9, heading="Results", fused_score=.03, dense_score=.72)]
    context, citations, redactions = build_context(evidence)
    assert "super-secret" not in context
    assert "[REDACTED_SECRET]" in context
    assert redactions == 1
    assert citations[0]["id"] == "S1"
    assert citations[0]["page_number"] == 9

