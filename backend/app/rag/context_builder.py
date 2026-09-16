from dataclasses import asdict

from app.core.privacy import redact_secrets
from app.rag.hybrid_search import Evidence


def build_context(evidence: list[Evidence]) -> tuple[str, list[dict], int]:
    sections: list[str] = []
    citations: list[dict] = []
    secret_count = 0
    for index, item in enumerate(evidence, start=1):
        safe_text, redacted = redact_secrets(item.text)
        secret_count += redacted
        source_id = f"S{index}"
        location = f"URL: {item.source_url}" if item.source_type == "website" else f"Page: {item.page_number}"
        sections.append(f"[{source_id}] {item.source_type.title()}: {item.document_name}; {location}; Section: {item.heading or 'Not specified'}\nUNTRUSTED EVIDENCE:\n{safe_text}")
        citations.append({"id": source_id, "source_type": item.source_type, "document_id": item.document_id, "document_name": item.document_name, "title": item.document_name, "page_number": item.page_number, "heading": item.heading, "url": item.source_url, "passage": safe_text, "evidence_score": item.reranker_score if item.reranker_score is not None else item.fused_score})
    return "\n\n".join(sections), citations, secret_count
