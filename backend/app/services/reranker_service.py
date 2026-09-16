import asyncio
from functools import lru_cache

from app.rag.hybrid_search import Evidence


@lru_cache(maxsize=2)
def _cross_encoder(model_name: str):
    from sentence_transformers import CrossEncoder
    return CrossEncoder(model_name)


class RerankerService:
    def __init__(self, model_name: str) -> None:
        self.model_name = model_name

    async def rerank(self, query: str, candidates: list[Evidence], limit: int) -> list[Evidence]:
        if len(candidates) <= 1:
            return candidates[:limit]
        try:
            scores = await asyncio.to_thread(_cross_encoder(self.model_name).predict, [(query, item.text) for item in candidates])
        except Exception:
            return candidates[:limit]
        for item, score in zip(candidates, scores, strict=True):
            item.reranker_score = float(score)
        return sorted(candidates, key=lambda item: item.reranker_score if item.reranker_score is not None else float("-inf"), reverse=True)[:limit]

