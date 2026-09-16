import asyncio
import json
from dataclasses import dataclass

from app.core.config import Settings
from app.database.mongodb import get_database
from app.managers.llm_provider_manager import LLMProviderManager
from app.providers.llm.factory import build_llm_registry
from app.providers.search.base import SearchResult
from app.rag.context_builder import build_context
from app.repositories.research import ResearchRepository
from app.schemas.research import ResearchStage
from app.services.live_research_service import LiveResearchService, build_live_context
from app.services.markdown_service import normalize_markdown
from app.services.retrieval_service import RetrievalService
from app.services.verification_service import detect_conflicts, remove_invalid_citations
from app.rag.source_quality import order_sources


@dataclass(slots=True)
class EvidenceBundle:
    context: str
    citations: list[dict]
    queries: list[str]


def research_queries(question: str, maximum: int) -> list[str]:
    candidates = [question.strip(), f"{question.strip()} official source", f"{question.strip()} latest research", f"{question.strip()} evidence analysis", f"{question.strip()} recent developments"]
    return list(dict.fromkeys(candidates))[:maximum]


async def gather_evidence(owner_id: str, question: str, workspace_id: str | None, include_private: bool, include_web: bool, max_queries: int, settings: Settings, source_ids: list[str] | None = None) -> EvidenceBundle:
    private_context = ""; private_citations: list[dict] = []
    if include_private and workspace_id:
        retrieval = await RetrievalService(settings).retrieve(owner_id, workspace_id, question, source_ids)
        private_context, private_citations, _ = build_context(retrieval.evidence)
    queries = research_queries(question, max_queries) if include_web else []
    web_results: dict[str, SearchResult] = {}
    if include_web:
        service = LiveResearchService(settings)
        results = await asyncio.gather(
            *(service.research(query) for query in queries),
            return_exceptions=True,
        )
        for result in results:
            if isinstance(result, Exception):
                continue
            for item in result.results:
                web_results.setdefault(item.url, item)
    ordered_web = order_sources(list(web_results.values()), question)[:8]
    web_context, web_citations = build_live_context(ordered_web, len(private_citations) + 1)
    return EvidenceBundle("\n\n".join(part for part in (private_context, web_context) if part), [*private_citations, *web_citations], queries)


async def synthesize_and_verify(prompt: str, context: str, citations: list[dict], settings: Settings) -> str:
    manager = LLMProviderManager(build_llm_registry(settings))
    _, draft = await manager.generate_with_fallback([{"role": "user", "content": f"{prompt}\n\nAUTHORIZED EVIDENCE:\n{context}"}])
    valid = {str(item["id"]) for item in citations}
    verification_prompt = f"""Act as an evidence verifier. Revise the DRAFT so every factual claim is supported by the AUTHORIZED EVIDENCE and uses only these citation IDs: {', '.join(sorted(valid))}. Preserve the requested structure. Explicitly report credible conflicts and limitations. Remove unsupported claims. Return only the corrected final output.

DRAFT:
{draft}

AUTHORIZED EVIDENCE:
{context}"""
    _, verified = await manager.generate_with_fallback([{"role": "user", "content": verification_prompt}])
    return remove_invalid_citations(verified, valid)


async def process_deep_research(owner_id: str, session_id: str, settings: Settings) -> None:
    repository = ResearchRepository(get_database())
    try:
        session = await repository.get_owned(owner_id, session_id); request = session["request"]
        await repository.update(owner_id, session_id, ResearchStage.SEARCHING)
        bundle = await gather_evidence(owner_id, request["question"], request.get("workspace_id"), request["include_private"], request["include_web"], request["max_queries"], settings)
        await repository.update(owner_id, session_id, ResearchStage.READING_SOURCES, queries=bundle.queries, source_count=len(bundle.citations), sources=bundle.citations)
        if not bundle.citations: raise ValueError("Reliable evidence could not be found")
        conflicts = detect_conflicts(bundle.citations)
        await repository.update(owner_id, session_id, ResearchStage.CROSS_CHECKING, conflicts=conflicts)
        await repository.update(owner_id, session_id, ResearchStage.SYNTHESIZING)
        conflict_note = json.dumps(conflicts) if conflicts else "No algorithmic conflict candidates were detected; still assess source disagreement."
        prompt = f"""Create a deep research report answering: {request['question']}
Answer language: {request['language']}.
Use Markdown and exactly these sections: Executive Summary, Key Findings, Detailed Analysis, Evidence, Contradictions and Limitations, Conclusion, Sources. Cite claims using [S1], [S2], etc. Never invent facts, dates, or citations. Conflict candidates: {conflict_note}"""
        await repository.update(owner_id, session_id, ResearchStage.VERIFYING)
        report = normalize_markdown(await synthesize_and_verify(prompt, bundle.context, bundle.citations, settings))
        await repository.update(owner_id, session_id, ResearchStage.COMPLETED, output_markdown=report, error_message=None)
    except Exception as exc:
        await repository.update(owner_id, session_id, ResearchStage.FAILED, error_message=(str(exc).strip() or "Deep research could not be completed")[:300])
        raise
