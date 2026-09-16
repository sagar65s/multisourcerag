import asyncio
import re

from app.core.config import Settings
from app.database.mongodb import get_database
from app.database.qdrant import VectorStore
from app.rag.hybrid_search import Evidence, evidence_status, reciprocal_rank_fusion
from app.repositories.chunks import ChunkRepository
from app.services.embedding_service import EmbeddingService
from app.services.reranker_service import RerankerService


class RetrievalResult:
    def __init__(self, evidence: list[Evidence], status: str) -> None:
        self.evidence = evidence
        self.status = status


PAGE_REFERENCES = (
    re.compile(r"\b(?:pages?|page\s*(?:no\.?|number))\s*[:#-]?\s*(\d{1,5})(?:\s*(?:-|–|to|through)\s*(\d{1,5}))?\b", re.IGNORECASE),
    re.compile(r"\b(\d{1,5})(?:\s*(?:-|–|to|through)\s*(\d{1,5}))?\s*(?:pages?|page)\b", re.IGNORECASE),
    re.compile(r"(?:பக்கம்|பக்கங்கள்|पृष्ठ|पेज)\s*[:#-]?\s*(\d{1,5})(?:\s*(?:-|–|முதல்|வரை|से|तक)\s*(\d{1,5}))?", re.IGNORECASE),
    re.compile(r"(\d{1,5})(?:\s*(?:-|–|முதல்|வரை|से|तक)\s*(\d{1,5}))?\s*(?:ஆம்\s*)?(?:பக்கம்|பக்கங்கள்|पृष्ठ|पेज)", re.IGNORECASE),
)
OVERVIEW_TERMS = (
    "summarize",
    "summary",
    "overview",
    "entire document",
    "whole document",
    "all pages",
    "full document",
    "what is this document",
    "summarize this website",
    "website overview",
    "full website",
    "about this website",
    "repository overview",
    "what is this repository",
    "explain this repository",
)


def requested_pages(query: str) -> list[int]:
    matches: list[tuple[int, int, int]] = []
    for pattern in PAGE_REFERENCES:
        for match in pattern.finditer(query):
            matches.append((match.start(), int(match.group(1)), int(match.group(2) or match.group(1))))
    pages: list[int] = []
    for _, start, end in sorted(matches):
        if start < 1 or end < 1:
            continue
        low, high = sorted((start, end))
        pages.extend(range(low, min(high, low + 7) + 1))
    return list(dict.fromkeys(pages))[:8]


def _is_overview_query(query: str) -> bool:
    normalized = query.casefold()
    return any(term in normalized for term in OVERVIEW_TERMS)


class RetrievalService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def retrieve(self, user_id: str, workspace_id: str, query: str, document_ids: list[str] | None = None, source_types: list[str] | None = None) -> RetrievalResult:
        filters: dict = {"owner_id": user_id, "workspace_id": workspace_id}
        if document_ids: filters["document_id"] = {"$in": document_ids}
        if source_types: filters["source_type"] = {"$in": source_types}
        if await get_database().document_chunks.count_documents(filters, limit=1) == 0:
            return RetrievalResult([], "no_evidence")
        repository = ChunkRepository(get_database())
        pages = requested_pages(query)
        if pages:
            exact = await repository.page_search(user_id, workspace_id, pages, document_ids, source_types, 18)
            evidence = reciprocal_rank_fusion([], exact)
            return RetrievalResult(evidence, evidence_status(evidence))
        if _is_overview_query(query):
            overview = await repository.overview_search(user_id, workspace_id, document_ids, source_types, 12)
            evidence = reciprocal_rank_fusion([], overview)
            return RetrievalResult(evidence, evidence_status(evidence))
        vector = (await EmbeddingService(self.settings.embedding_model, self.settings.embedding_batch_size).embed([query]))[0]
        dense_task = VectorStore(self.settings).search(user_id, workspace_id, vector, document_ids, source_types, self.settings.retrieval_candidates)
        keyword_task = repository.keyword_search(user_id, workspace_id, query, document_ids, source_types, self.settings.retrieval_candidates)
        dense_result, keyword_result = await asyncio.gather(dense_task, keyword_task, return_exceptions=True)
        dense = [] if isinstance(dense_result, BaseException) else dense_result
        keyword = [] if isinstance(keyword_result, BaseException) else keyword_result
        fused = reciprocal_rank_fusion(dense, keyword)
        if not fused:
            overview = await repository.overview_search(user_id, workspace_id, document_ids, source_types, self.settings.reranked_evidence_limit)
            fused = reciprocal_rank_fusion([], overview)
        reranked = await RerankerService(self.settings.reranker_model).rerank(query, fused[: self.settings.retrieval_candidates], self.settings.reranked_evidence_limit)
        return RetrievalResult(reranked, evidence_status(reranked))
