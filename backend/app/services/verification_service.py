import re
from dataclasses import dataclass


NEGATIONS = {"not", "no", "never", "without", "false", "declined", "decreased", "failed"}
TOKEN = re.compile(r"[a-z0-9]+")
CITATION = re.compile(r"\[(S\d+)]")
SENTENCE = re.compile(r"(?<=[.!?])\s+|\n+")


@dataclass(frozen=True, slots=True)
class AnswerVerification:
    text: str
    status: str
    cited_sources: tuple[str, ...]
    invalid_sources: tuple[str, ...]
    unsupported_claims: int
    conflicts: tuple[dict, ...]


def detect_conflicts(sources: list[dict]) -> list[dict]:
    conflicts: list[dict] = []
    for left_index, left in enumerate(sources):
        left_tokens = set(TOKEN.findall(str(left.get("passage", "")).casefold()))
        if len(left_tokens) < 6: continue
        left_negative = bool(left_tokens & NEGATIONS)
        for right in sources[left_index + 1:]:
            if left.get("id") == right.get("id"): continue
            right_tokens = set(TOKEN.findall(str(right.get("passage", "")).casefold()))
            union = left_tokens | right_tokens
            overlap = len(left_tokens & right_tokens) / len(union) if union else 0
            if overlap >= .35 and left_negative != bool(right_tokens & NEGATIONS):
                conflicts.append({"source_a": left.get("id"), "source_b": right.get("id"), "reason": "Similar claims use opposing polarity and require explicit review"})
    return conflicts[:10]


def remove_invalid_citations(text: str, valid_ids: set[str]) -> str:
    return CITATION.sub(lambda match: match.group(0) if match.group(1) in valid_ids else "[citation unavailable]", text)


def verify_answer_evidence(text: str, sources: list[dict], freshness_required: bool = False) -> AnswerVerification:
    valid = {str(item.get("id")) for item in sources if item.get("id")}
    referenced = CITATION.findall(text)
    invalid = tuple(sorted(set(referenced) - valid))
    sanitized = remove_invalid_citations(text, valid)
    cited = tuple(sorted(set(referenced) & valid))
    claim_lines = [line.strip() for line in SENTENCE.split(sanitized) if len(line.split()) >= 7 and not line.lstrip().startswith(("#", "```", "- **Sources"))]
    unsupported = sum(1 for line in claim_lines if not any(f"[{source}]" in line for source in cited))
    conflicts = tuple(detect_conflicts(sources))
    if not cited:
        status = "no_evidence"
    elif conflicts:
        status = "conflicting_evidence"
    elif unsupported == 0 and len(cited) >= 2:
        status = "strongly_supported"
    elif unsupported <= max(1, len(claim_lines) // 3):
        status = "supported"
    else:
        status = "limited_evidence"
    if freshness_required and status not in {"no_evidence", "conflicting_evidence"}:
        used_sources = [item for item in sources if str(item.get("id")) in cited]
        dated = sum(bool(item.get("date")) for item in used_sources)
        authoritative = sum(int(item.get("authority") or 0) >= 6 for item in used_sources)
        if dated == 0 and authoritative == 0:
            status = "limited_evidence"
        elif status == "strongly_supported" and dated + authoritative < 2:
            status = "supported"
    return AnswerVerification(sanitized, status, cited, invalid, unsupported, conflicts)
