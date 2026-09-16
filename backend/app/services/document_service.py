from app.core.config import Settings
from app.database.mongodb import get_database
from app.database.qdrant import VectorStore
from app.loaders.document_loader import extract_document
from app.rag.chunking import smart_chunk
from app.repositories.chunks import ChunkRepository
from app.repositories.documents import DocumentRepository
from app.schemas.document import ProcessingStatus
from app.services.embedding_service import EmbeddingService
from app.services.private_storage_service import PrivateStorageService
from app.core.observability import logger


async def process_document(owner_id: str, document_id: str, settings: Settings) -> None:
    repository = DocumentRepository(get_database())
    try:
        document = await repository.get_owned(owner_id, document_id)
        await repository.set_status(owner_id, document_id, ProcessingStatus.EXTRACTING)
        result = await extract_document(document["stored_path"], document["extension"], settings.ocr_languages, settings.ocr_min_text_chars_per_page)
        if result.used_ocr:
            await repository.set_status(owner_id, document_id, ProcessingStatus.OCR)
        if not any(page.text.strip() for page in result.pages):
            raise ValueError("OCR did not find readable text")
        await repository.set_status(owner_id, document_id, ProcessingStatus.CLEANING)
        await repository.set_status(owner_id, document_id, ProcessingStatus.CHUNKING)
        chunks = smart_chunk(result.pages)
        if not chunks:
            raise ValueError("No indexable text was found")
        await ChunkRepository(get_database()).replace_document(owner_id, document["workspace_id"], document_id, document["original_name"], chunks)
        await repository.set_status(owner_id, document_id, ProcessingStatus.EMBEDDING)
        vectors = await EmbeddingService(settings.embedding_model, settings.embedding_batch_size).embed([chunk.text for chunk in chunks])
        await repository.set_status(owner_id, document_id, ProcessingStatus.INDEXING)
        try:
            await VectorStore(settings).index_document(owner_id, document["workspace_id"], document_id, document["original_name"], chunks, vectors)
        except Exception as exc:
            logger.warning("document_vector_index_degraded", document_id=document_id, reason=type(exc).__name__)
        await repository.set_status(owner_id, document_id, ProcessingStatus.COMPLETED, page_count=len(result.pages), chunk_count=len(chunks), ocr_used=result.used_ocr, error_message=None)
    except Exception as exc:
        message = str(exc).strip() or "Could not process this document"
        await repository.set_status(owner_id, document_id, ProcessingStatus.FAILED, error_message=message[:240])
        raise


async def delete_document(owner_id: str, document_id: str, settings: Settings) -> None:
    repository = DocumentRepository(get_database())
    document = await repository.get_owned(owner_id, document_id)
    try:
        await VectorStore(settings).delete_document(owner_id, document["workspace_id"], document_id)
    except Exception as exc:
        logger.warning("document_vector_delete_degraded", document_id=document_id, reason=type(exc).__name__)
    await PrivateStorageService(settings.private_storage_root).delete(document["stored_path"])
    await ChunkRepository(get_database()).delete_document(owner_id, document["workspace_id"], document_id)
    await get_database().document_artifacts.delete_many({"owner_id": owner_id, "workspace_id": document["workspace_id"], "source_ids": document_id})
    await repository.delete_metadata(owner_id, document_id)
