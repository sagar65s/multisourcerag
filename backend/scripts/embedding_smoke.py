"""Download the configured open embedding model and verify a real CPU encode."""

import asyncio
import math
import os

from app.services.embedding_service import EmbeddingService


async def main() -> None:
    model = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
    vectors = await EmbeddingService(model, 2).embed(
        [
            "Private retrieval requires authorization filters.",
            "Citations ground trustworthy answers.",
        ]
    )
    if len(vectors) != 2 or any(len(vector) != 384 for vector in vectors):
        raise RuntimeError("Embedding model returned an unexpected shape")
    if any(not math.isclose(math.sqrt(sum(value * value for value in vector)), 1.0, abs_tol=0.001) for vector in vectors):
        raise RuntimeError("Embedding vectors were not normalized")
    print("Embedding smoke passed: vectors=2 dimensions=384 normalized=true")


if __name__ == "__main__":
    asyncio.run(main())
