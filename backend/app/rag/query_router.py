from enum import StrEnum
from app.rag.freshness_detector import requires_freshness


class QueryMode(StrEnum):
    AUTO = "auto"
    GENERAL = "general"
    KNOWLEDGE = "knowledge"
    WEBSITE = "website"
    WEB = "web"
    BOTH = "both"
    DEEP_RESEARCH = "deep_research"


KNOWLEDGE_TERMS = {"my pdf", "my document", "uploaded", "workspace", "these files", "our document"}
WEBSITE_TERMS = {"this website", "saved website", "this url", "website page", "indexed site"}
DEEP_TERMS = {"deep research", "in-depth research", "comprehensive investigation", "research report"}


def route_query(query: str, requested: QueryMode = QueryMode.AUTO, has_website: bool = False, has_private: bool = True) -> QueryMode:
    if requested != QueryMode.AUTO:
        return requested
    normalized = query.casefold()
    if any(term in normalized for term in DEEP_TERMS): return QueryMode.DEEP_RESEARCH
    wants_web = requires_freshness(query)
    wants_knowledge = any(term in normalized for term in KNOWLEDGE_TERMS)
    wants_website = has_website or any(term in normalized for term in WEBSITE_TERMS)
    if wants_web and wants_knowledge:
        return QueryMode.BOTH
    if wants_web:
        return QueryMode.WEB
    if wants_website:
        return QueryMode.WEBSITE
    if not has_private:
        return QueryMode.GENERAL
    return QueryMode.KNOWLEDGE
