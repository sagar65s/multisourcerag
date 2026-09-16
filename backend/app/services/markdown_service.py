import re


_OUTER_FENCE = re.compile(r"^```(?:markdown|md)?\s*\n([\s\S]*?)\n```\s*$", re.IGNORECASE)


def normalize_markdown(value: str) -> str:
    """Normalize common LLM Markdown wrappers without changing its meaning."""
    text = (value or "").strip().replace("\r\n", "\n")
    fenced = _OUTER_FENCE.match(text)
    if fenced:
        text = fenced.group(1).strip()
    # Some providers escape Markdown punctuation even outside code blocks.
    text = re.sub(r"\\([*#_>`~-])", r"\1", text)
    return re.sub(r"\n{4,}", "\n\n\n", text).strip()
