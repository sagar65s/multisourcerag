import re
from dataclasses import dataclass

from langchain_core.documents import Document

from app.loaders.document_loader import ExtractedPage
from app.rag.langchain_adapter import split_documents


@dataclass(slots=True)
class TextChunk:
    text: str
    page_number: int
    heading: str | None
    chunk_index: int


HEADING = re.compile(r"^(?:#{1,6}\s+.+|[A-Z][A-Z\d &:/_-]{3,}|\d+(?:\.\d+)*\s+.+)$")
def _units(text: str) -> list[tuple[str | None, str]]:
    heading: str | None = None
    units: list[tuple[str | None, str]] = []
    for block in re.split(r"\n\s*\n", text):
        block = block.strip()
        if not block:
            continue
        first = block.splitlines()[0].strip()
        if len(first) <= 120 and HEADING.match(first):
            heading = first.lstrip("# ").strip()
            remaining = "\n".join(block.splitlines()[1:]).strip()
            if remaining:
                units.append((heading, remaining))
        else:
            units.append((heading, block))
    return units


def smart_chunk(pages: list[ExtractedPage], target_chars: int = 1400, overlap_chars: int = 220) -> list[TextChunk]:
    chunks: list[TextChunk] = []
    for page in pages:
        structured: list[Document] = []
        for heading, unit in _units(page.text):
            structured.append(
                Document(
                    page_content=unit,
                    metadata={
                        "page_number": page.page_number,
                        "heading": heading or page.heading,
                    },
                )
            )
        for document in split_documents(
            structured, chunk_size=target_chars, chunk_overlap=overlap_chars
        ):
            text = document.page_content.strip()
            if text:
                chunks.append(
                    TextChunk(
                        text=text,
                        page_number=int(document.metadata["page_number"]),
                        heading=document.metadata.get("heading"),
                        chunk_index=len(chunks),
                    )
                )
    return [chunk for chunk in chunks if chunk.text.strip()]
