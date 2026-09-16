import re
from datetime import UTC, datetime

from app.rag.source_quality import parse_date

EXPLICIT_FRESHNESS = re.compile(r"\b(latest|today|tonight|current|currently|recent|newest|now|this (?:week|month|year)|breaking|just announced|as of)\b", re.I)
VOLATILE_FACTS = re.compile(r"\b(ceo|president|prime minister|price|stock|weather|score|schedule|version|release|announcement|availability|status|law|regulation|policy|deadline)\b", re.I)


def requires_freshness(query: str) -> bool:
    return bool(EXPLICIT_FRESHNESS.search(query) or VOLATILE_FACTS.search(query))


def freshness_rank(value: str | None, query: str, now: datetime | None = None) -> int:
    """Coarse internal rank only; never present it as user confidence."""
    date = parse_date(value)
    if date is None:
        return 0 if requires_freshness(query) else 1
    current = now or datetime.now(UTC)
    if date > current.replace(microsecond=0):
        return 0
    age_days = max(0, (current - date).days)
    if age_days <= 7: return 5
    if age_days <= 31: return 4
    if age_days <= 180: return 3
    if age_days <= 730: return 2
    return 0 if requires_freshness(query) else 1
