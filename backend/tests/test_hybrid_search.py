from app.rag.hybrid_search import evidence_status, reciprocal_rank_fusion


def item(document: str, chunk: str, score: float) -> dict:
    return {"document_id": document, "source_id": document, "document_name": f"{document}.pdf", "chunk_id": chunk, "text": "Evidence text", "page_number": 2, "heading": "Evidence", "score": score}


def test_fusion_deduplicates_and_rewards_cross_retriever_match() -> None:
    dense = [item("a", "1", .76), item("b", "1", .64)]
    keyword = [item("a", "1", 4.2), item("c", "1", 3.1)]
    result = reciprocal_rank_fusion(dense, keyword)
    assert len(result) == 3
    assert result[0].document_id == "a"
    assert result[0].dense_score == .76
    assert result[0].keyword_score == 4.2


def test_evidence_status_uses_real_retrieval_signals() -> None:
    result = reciprocal_rank_fusion([item("a", "1", .72), item("b", "1", .68)], [])
    assert evidence_status(result) == "strongly_supported"
    assert evidence_status([]) == "no_evidence"

