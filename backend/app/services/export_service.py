import html
import io
import json
import re
from dataclasses import dataclass

import pymupdf
from bson import ObjectId
from docx import Document
from fastapi import HTTPException

from app.database.mongodb import get_database
from app.repositories.conversations import ConversationRepository
from app.repositories.intelligence import IntelligenceRepository
from app.repositories.research import ResearchRepository
from app.schemas.export import ExportFormat, ExportRequest, ExportSource
from app.services.markdown_service import normalize_markdown


@dataclass(slots=True)
class ExportedFile:
    content: bytes
    media_type: str
    extension: str


def _citation_text(sources: list[dict]) -> str:
    if not sources: return ""
    lines = ["\n\n## Sources"]
    for item in sources:
        name = item.get("document_name") or item.get("title") or item.get("url") or "Source"
        location = f"Page {item.get('page_number')}" if item.get("source_type") == "document" else item.get("date") or item.get("url") or ""
        lines.append(f"- [{item.get('id', 'S?')}] {name} — {location}")
    return "\n".join(lines)


async def _resolve_content(owner_id: str, payload: ExportRequest) -> tuple[str, str]:
    database = get_database()
    if payload.source_type == ExportSource.CONVERSATION:
        repository = ConversationRepository(database); conversation = await repository.get_owned(owner_id, payload.source_id)
        messages = await repository.list_messages(owner_id, payload.source_id, 200)
        content = [f"# {conversation['title']}"]
        sources: dict[str, dict] = {}
        for message in messages:
            content.append(f"\n## {'Question' if message.role.value == 'user' else 'Answer'}\n\n{message.content}")
            for source in message.sources: sources[f"{message.id}:{source.get('id')}"] = source
        if payload.include_citations: content.append(_citation_text(list(sources.values())))
        return conversation["title"], "\n".join(content)
    if payload.source_type == ExportSource.RESEARCH:
        item = await ResearchRepository(database).get_owned(owner_id, payload.source_id)
        content = item.get("output_markdown") or "Research output is not available."
        if payload.include_citations: content += _citation_text(item.get("sources", []))
        return item["title"], content
    if payload.source_type == ExportSource.INTELLIGENCE:
        item = await IntelligenceRepository(database).get_owned(owner_id, payload.source_id)
        result = item.get("result", {}); title = str(result.get("title") or item["tool"].replace("_", " ").title())
        content = str(result.get("markdown") or f"# {title}\n\n```json\n{json.dumps(result, indent=2, ensure_ascii=False)}\n```")
        if payload.include_citations: content += _citation_text(item.get("citations", []))
        return title, content
    if not ObjectId.is_valid(payload.source_id): raise HTTPException(status_code=404, detail="Saved answer not found")
    item = await database.saved_answers.find_one({"_id": ObjectId(payload.source_id), "owner_id": owner_id})
    if item is None: raise HTTPException(status_code=404, detail="Saved answer not found")
    content = f"# Saved answer\n\n## Question\n\n{item['question']}\n\n## Answer\n\n{item['answer']}"
    if payload.include_citations: content += _citation_text(item.get("sources", []))
    return item["question"][:120], content


def _plain(markdown: str) -> str:
    value = normalize_markdown(markdown)
    value = re.sub(r"```(?:\w+)?\n?", "", value)
    value = re.sub(r"!\[(.*?)\]\((.*?)\)", r"\1", value)
    value = re.sub(r"\[(.*?)\]\((.*?)\)", r"\1 (\2)", value)
    value = re.sub(r"(^|\n)#{1,6}\s*", r"\1", value)
    value = re.sub(r"(^|\n)>\s?", r"\1", value)
    value = re.sub(r"(?<!\*)\*\*([^\n*]+)\*\*", r"\1", value)
    value = re.sub(r"(?<!_)__([^\n_]+)__", r"\1", value)
    value = re.sub(r"(?<!\*)\*([^\n*]+)\*", r"\1", value)
    value = re.sub(r"(?<!_)_([^\n_]+)_", r"\1", value)
    value = re.sub(r"~~([^\n~]+)~~", r"\1", value)
    value = re.sub(r"`([^`]+)`", r"\1", value)
    value = re.sub(r"(?m)^\s*[-+*]\s+", "• ", value)
    return value.replace("\\*", "*").replace("\\#", "#").strip()


def _inline_html(value: str) -> str:
    safe = html.escape(value.strip())
    safe = re.sub(r"`([^`]+)`", r"<code>\1</code>", safe)
    safe = re.sub(r"\*\*([^\n*]+)\*\*", r"<strong>\1</strong>", safe)
    safe = re.sub(r"__([^\n_]+)__", r"<strong>\1</strong>", safe)
    safe = re.sub(r"(?<!\*)\*([^\n*]+)\*", r"<em>\1</em>", safe)
    safe = re.sub(r"(?<!_)_([^\n_]+)_", r"<em>\1</em>", safe)
    safe = re.sub(r"~~([^\n~]+)~~", r"<del>\1</del>", safe)
    return re.sub(
        r"\[([^\]]+)]\((https?://[^)\s]+)\)",
        r'<a href="\2">\1</a>',
        safe,
    )


def _markdown_html(markdown: str) -> str:
    lines = normalize_markdown(markdown).splitlines()
    output: list[str] = []
    list_tag: str | None = None
    in_code = False
    code_lines: list[str] = []

    def close_list() -> None:
        nonlocal list_tag
        if list_tag:
            output.append(f"</{list_tag}>")
            list_tag = None

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("```"):
            close_list()
            if in_code:
                output.append(f"<pre><code>{html.escape(chr(10).join(code_lines))}</code></pre>")
                code_lines = []
            in_code = not in_code
            continue
        if in_code:
            code_lines.append(line)
            continue
        if not stripped:
            close_list()
            continue
        heading = re.match(r"^(#{1,6})\s+(.+)$", stripped)
        if heading:
            close_list()
            level = min(len(heading.group(1)), 3)
            output.append(f"<h{level}>{_inline_html(heading.group(2))}</h{level}>")
            continue
        bullet = re.match(r"^[-+*]\s+(.+)$", stripped)
        numbered = re.match(r"^\d+[.)]\s+(.+)$", stripped)
        if bullet or numbered:
            tag = "ul" if bullet else "ol"
            if list_tag != tag:
                close_list(); list_tag = tag; output.append(f"<{tag}>")
            output.append(f"<li>{_inline_html((bullet or numbered).group(1))}</li>")
            continue
        close_list()
        if stripped.startswith(">"):
            output.append(f"<blockquote>{_inline_html(stripped.lstrip('>').strip())}</blockquote>")
        elif re.fullmatch(r"[-*_]{3,}", stripped):
            output.append("<hr>")
        else:
            output.append(f"<p>{_inline_html(stripped)}</p>")
    close_list()
    if code_lines:
        output.append(f"<pre><code>{html.escape(chr(10).join(code_lines))}</code></pre>")
    return "\n".join(output)


def _pdf(markdown: str) -> bytes:
    stream = io.BytesIO(); writer = pymupdf.DocumentWriter(stream)
    body = _markdown_html(markdown)
    story = pymupdf.Story(html=f"""<html><head><style>
body {{ font-family: sans-serif; font-size: 10.5pt; line-height: 1.5; color: #182033; }}
h1 {{ font-size: 22pt; color: #5037c9; margin: 0 0 14pt; }}
h2 {{ font-size: 16pt; color: #33276d; margin: 16pt 0 7pt; }}
h3 {{ font-size: 13pt; color: #33276d; margin: 12pt 0 5pt; }}
p {{ margin: 0 0 7pt; }} ul, ol {{ margin: 3pt 0 9pt 16pt; }} li {{ margin: 0 0 4pt; }}
blockquote {{ border-left: 3pt solid #7c63ff; background: #f2efff; padding: 7pt 10pt; margin: 8pt 0; }}
code {{ background: #f0f2f7; color: #7b235d; padding: 1pt 3pt; }}
pre {{ background: #111525; color: #f4f5fb; padding: 9pt; font-size: 9pt; }}
a {{ color: #4c43c6; }} hr {{ color: #d7d9e4; margin: 10pt 0; }}
</style></head><body>{body}</body></html>""")
    page_rect = pymupdf.paper_rect("a4"); content_rect = page_rect + (45, 48, -45, -48)
    more = True
    while more:
        device = writer.begin_page(page_rect)
        more, _ = story.place(content_rect)
        story.draw(device); writer.end_page()
    writer.close(); return stream.getvalue()


def _docx(title: str, text: str) -> bytes:
    document = Document(); document.core_properties.title = title
    for block in _plain(text).split("\n"):
        document.add_paragraph(block)
    stream = io.BytesIO(); document.save(stream); return stream.getvalue()


async def export_owned_content(owner_id: str, payload: ExportRequest) -> ExportedFile:
    title, markdown = await _resolve_content(owner_id, payload)
    if payload.format == ExportFormat.PDF: return ExportedFile(_pdf(markdown), "application/pdf", "pdf")
    if payload.format == ExportFormat.DOCX: return ExportedFile(_docx(title, markdown), "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "docx")
    if payload.format == ExportFormat.TXT: return ExportedFile(_plain(markdown).encode("utf-8"), "text/plain; charset=utf-8", "txt")
    return ExportedFile(markdown.encode("utf-8"), "text/markdown; charset=utf-8", "md")
