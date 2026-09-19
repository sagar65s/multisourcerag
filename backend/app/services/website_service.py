from datetime import UTC, datetime

from app.core.config import Settings
from app.database.mongodb import get_database
from app.database.qdrant import VectorStore
from app.loaders.document_loader import ExtractedPage
from app.loaders.web_loader import build_content_preview
from app.rag.chunking import smart_chunk
from app.repositories.chunks import ChunkRepository
from app.repositories.websites import WebsiteRepository
from app.schemas.document import ProcessingStatus
from app.schemas.website import CrawlScope
from app.services.crawler_service import crawl_website
from app.services.embedding_service import EmbeddingService
from app.core.observability import logger


async def process_website(owner_id: str, website_id: str, settings: Settings) -> None:
    repository = WebsiteRepository(get_database())
    try:
        source = await repository.get_owned(owner_id, website_id)
        await repository.set_status(owner_id, website_id, ProcessingStatus.EXTRACTING)
        pages = await crawl_website(source["url"], CrawlScope(source["scope"]), source.get("selected_urls", []), source["max_depth"], source["max_pages"], settings)
        extracted = [ExtractedPage(page_number=index, text=page.text, heading=page.title) for index, page in enumerate(pages, start=1)]
        await repository.set_status(owner_id, website_id, ProcessingStatus.CHUNKING)
        chunks = smart_chunk(extracted)
        page_map = {index: page for index, page in enumerate(pages, start=1)}
        now = datetime.now(UTC)
        payloads = []
        for chunk in chunks:
            page = page_map[chunk.page_number]
            payloads.append({"owner_id": owner_id, "user_id": owner_id, "workspace_id": source["workspace_id"], "document_id": website_id, "source_id": website_id, "document_name": page.title, "chunk_id": str(chunk.chunk_index), "page_number": chunk.page_number, "heading": chunk.heading, "source_type": "website", "source_url": page.url, "text": chunk.text, "created_at": now})
        await ChunkRepository(get_database()).replace_payloads(owner_id, source["workspace_id"], website_id, payloads)
        await repository.set_status(owner_id, website_id, ProcessingStatus.EMBEDDING)
        vectors = await EmbeddingService(settings.embedding_model, settings.embedding_batch_size).embed([item["text"] for item in payloads])
        await repository.set_status(owner_id, website_id, ProcessingStatus.INDEXING)
        try:
            await VectorStore(settings).index_payloads(website_id, payloads, vectors)
        except Exception as exc:
            logger.warning("website_vector_index_degraded", website_id=website_id, reason=type(exc).__name__)
        first = pages[0]; internal = sorted({link for page in pages for link in page.internal_links})[:100]; external = sorted({link for page in pages for link in page.external_links})[:100]; headings = list(dict.fromkeys(heading for page in pages for heading in page.headings))[:100]
        methods = {page.retrieval_method for page in pages}
        analysis_method = "search_fallback" if "search_fallback" in methods else "github_api" if "github_api" in methods else "browser" if "browser" in methods else "direct"
        notices = {
            "search_fallback": "Direct access was blocked. This index uses public search-visible summaries and links.",
            "github_api": "Indexed from GitHub's public API, repository metadata, file tree and README.",
            "browser": "Indexed from a browser-rendered public page.",
            "direct": None,
        }
        await repository.set_status(owner_id, website_id, ProcessingStatus.COMPLETED, title=first.title, meta_description=first.meta_description, content_preview=build_content_preview(pages), indexed_pages=len(pages), chunk_count=len(chunks), important_headings=headings, internal_links=internal, external_links=external, analysis_method=analysis_method, source_notice=notices[analysis_method], error_message=None)
    except Exception as exc:
        await repository.set_status(owner_id, website_id, ProcessingStatus.FAILED, error_message=(str(exc).strip() or "Could not analyze this website")[:240])
        raise


async def delete_website(owner_id: str, website_id: str, settings: Settings) -> None:
    repository = WebsiteRepository(get_database()); source = await repository.get_owned(owner_id, website_id)
    try: await VectorStore(settings).delete_document(owner_id, source["workspace_id"], website_id)
    except Exception as exc:
        logger.warning("website_vector_delete_degraded", website_id=website_id, reason=type(exc).__name__)
    await ChunkRepository(get_database()).delete_document(owner_id, source["workspace_id"], website_id)
    await get_database().document_artifacts.delete_many({"owner_id": owner_id, "workspace_id": source["workspace_id"], "source_ids": website_id})
    await repository.delete_metadata(owner_id, website_id)
