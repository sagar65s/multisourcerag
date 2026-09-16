import asyncio
import hashlib
import math
from functools import lru_cache

from app.core.observability import logger


@lru_cache(maxsize=2)
def _model(model_name: str):
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(model_name)


def _local_hash_embedding(text: str, dimensions: int = 384) -> list[float]:
    vector = [0.0] * dimensions
    for token in text.casefold().split():
        digest = hashlib.blake2b(token.encode("utf-8"), digest_size=16).digest()
        vector[int.from_bytes(digest[:4], "big") % dimensions] += -1.0 if digest[4] & 1 else 1.0
    norm = math.sqrt(sum(value * value for value in vector))
    return [value / norm for value in vector] if norm else vector


class EmbeddingService:
    def __init__(self, model_name: str, batch_size: int) -> None:
        self.model_name = model_name
        self.batch_size = batch_size

    async def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        def encode() -> list[list[float]]:
            vectors = _model(self.model_name).encode(texts, batch_size=self.batch_size, normalize_embeddings=True, show_progress_bar=False)
            return vectors.tolist()
        try:
            return await asyncio.to_thread(encode)
        except Exception as exc:
            logger.warning("embedding_model_fallback", reason=type(exc).__name__, dimensions=384)
            return [_local_hash_embedding(text) for text in texts]
