from uuid import NAMESPACE_URL, uuid5

from qdrant_client import AsyncQdrantClient, models

from app.core.config import Settings
from app.rag.chunking import TextChunk


class VectorStore:
    def __init__(self, settings: Settings) -> None:
        self.collection = settings.qdrant_collection
        self.client = AsyncQdrantClient(url=settings.qdrant_url, api_key=settings.qdrant_api_key or None, timeout=8, check_compatibility=False)

    async def ensure_collection(self, vector_size: int) -> None:
        if not await self.client.collection_exists(self.collection):
            await self.client.create_collection(self.collection, vectors_config=models.VectorParams(size=vector_size, distance=models.Distance.COSINE))
            for field in ("user_id", "workspace_id", "document_id", "source_type"):
                await self.client.create_payload_index(self.collection, field_name=field, field_schema=models.PayloadSchemaType.KEYWORD)

    async def index_document(self, user_id: str, workspace_id: str, document_id: str, document_name: str, chunks: list[TextChunk], vectors: list[list[float]]) -> None:
        if not vectors:
            return
        await self.ensure_collection(len(vectors[0]))
        points = [models.PointStruct(id=str(uuid5(NAMESPACE_URL, f"{document_id}:{chunk.chunk_index}")), vector=vector, payload={"user_id": user_id, "workspace_id": workspace_id, "document_id": document_id, "source_id": document_id, "chunk_id": str(chunk.chunk_index), "document_name": document_name, "page_number": chunk.page_number, "heading": chunk.heading, "source_type": "document", "text": chunk.text}) for chunk, vector in zip(chunks, vectors, strict=True)]
        await self.client.upsert(collection_name=self.collection, points=points, wait=True)

    async def index_payloads(self, source_id: str, payloads: list[dict], vectors: list[list[float]]) -> None:
        if not vectors: return
        await self.ensure_collection(len(vectors[0]))
        points = [models.PointStruct(id=str(uuid5(NAMESPACE_URL, f"{source_id}:{index}")), vector=vector, payload=payload) for index, (payload, vector) in enumerate(zip(payloads, vectors, strict=True))]
        await self.client.upsert(collection_name=self.collection, points=points, wait=True)

    @staticmethod
    def authorization_filter(user_id: str, workspace_id: str, document_ids: list[str] | None = None, source_types: list[str] | None = None) -> models.Filter:
        must = [models.FieldCondition(key="workspace_id", match=models.MatchValue(value=workspace_id))]
        if document_ids:
            must.append(models.FieldCondition(key="document_id", match=models.MatchAny(any=document_ids)))
        if source_types:
            must.append(models.FieldCondition(key="source_type", match=models.MatchAny(any=source_types)))
        # Older website points used ``owner_id`` while document points used
        # ``user_id``. Requiring either exact owner field keeps existing
        # indexes usable without weakening tenant isolation.
        owner = [
            models.FieldCondition(key="user_id", match=models.MatchValue(value=user_id)),
            models.FieldCondition(key="owner_id", match=models.MatchValue(value=user_id)),
        ]
        return models.Filter(must=must, should=owner)

    async def delete_document(self, user_id: str, workspace_id: str, document_id: str) -> None:
        await self.client.delete(collection_name=self.collection, points_selector=models.FilterSelector(filter=self.authorization_filter(user_id, workspace_id, [document_id])), wait=True)

    async def delete_user(self, user_id: str) -> None:
        user_filter = models.Filter(should=[
            models.FieldCondition(key="user_id", match=models.MatchValue(value=user_id)),
            models.FieldCondition(key="owner_id", match=models.MatchValue(value=user_id)),
        ])
        await self.client.delete(collection_name=self.collection, points_selector=models.FilterSelector(filter=user_filter), wait=True)

    async def search(self, user_id: str, workspace_id: str, vector: list[float], document_ids: list[str] | None = None, source_types: list[str] | None = None, limit: int = 12) -> list[dict]:
        result = await self.client.query_points(collection_name=self.collection, query=vector, query_filter=self.authorization_filter(user_id, workspace_id, document_ids, source_types), limit=min(max(limit, 1), 30), with_payload=True)
        return [{"score": point.score, **(point.payload or {})} for point in result.points]
