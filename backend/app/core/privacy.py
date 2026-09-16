import re

SECRET_PATTERNS = (
    re.compile(r"(?i)(api[_-]?key|access[_-]?token|password|secret)\s*[:=]\s*['\"]?([^\s'\"]{8,})"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----[\s\S]+?-----END (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"\b(?:sk|ghp|xox[baprs])[-_][A-Za-z0-9_-]{16,}\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\bAIza[0-9A-Za-z_-]{30,}\b"),
    re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b"),
    re.compile(r"(?i)\b(?:mongodb(?:\+srv)?|postgres(?:ql)?|mysql|redis)://[^\s:@/]+:[^\s@/]+@[^\s]+"),
)


def redact_secrets(text: str) -> tuple[str, int]:
    redacted = text
    count = 0
    for pattern in SECRET_PATTERNS:
        redacted, replacements = pattern.subn("[REDACTED_SECRET]", redacted)
        count += replacements
    return redacted, count
