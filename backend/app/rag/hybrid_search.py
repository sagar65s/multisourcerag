from dataclasses import dataclass


@dataclass(slots=True)
class Evidence:
    source_id: str
    document_id: str
    document_name: str
    chunk_id: str
    text: str
    page_number: int
    heading: str | None
    fused_score: float
    dense_score: float | None = None
    keyword_score: float | None = None
    reranker_score: float | None = None
    source_type: str = "document"
    source_url: str | None = None


def _key(item: dict) -> str:
    return f"{item.get('document_id')}:{item.get('chunk_id')}"


def reciprocal_rank_fusion(dense: list[dict], keyword: list[dict], constant: int = 60) -> list[Evidence]:
    merged: dict[str, dict] = {}
    for source_name, results in (("dense", dense), ("keyword", keyword)):
        for rank, item in enumerate(results, start=1):
            key = _key(item)
            entry = merged.setdefault(key, {**item, "fused_score": 0.0, "dense_score": None, "keyword_score": None})
            entry["fused_score"] += 1.0 / (constant + rank)
            entry[f"{source_name}_score"] = float(item.get("score", 0.0))
    ranked = sorted(merged.values(), key=lambda item: item["fused_score"], reverse=True)
    return [Evidence(source_id=str(item.get("source_id") or item["document_id"]), document_id=str(item["document_id"]), document_name=str(item["document_name"]), chunk_id=str(item["chunk_id"]), text=str(item["text"]), page_number=int(item.get("page_number") or 1), heading=item.get("heading"), fused_score=float(item["fused_score"]), dense_score=item.get("dense_score"), keyword_score=item.get("keyword_score"), source_type=str(item.get("source_type") or "document"), source_url=item.get("source_url")) for item in ranked]


def evidence_status(items: list[Evidence]) -> str:
    if not items:
        return "no_evidence"
    strongest_dense = max((item.dense_score or 0 for item in items), default=0)
    unique_documents = len({item.document_id for item in items})
    if strongest_dense >= 0.55 and unique_documents >= 2:
        return "strongly_supported"
    if strongest_dense >= 0.35 or len(items) >= 3:
        return "supported"
    return "limited_evidence"
