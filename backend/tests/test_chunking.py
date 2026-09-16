from app.loaders.document_loader import ExtractedPage
from app.rag.chunking import smart_chunk


def test_preserves_page_and_heading_metadata() -> None:
    pages = [ExtractedPage(page_number=7, text="INTRODUCTION\n\nRetrieval uses evidence. Citations preserve trust.")]
    chunks = smart_chunk(pages, target_chars=100)
    assert chunks[0].page_number == 7
    assert chunks[0].heading == "INTRODUCTION"
    assert "Retrieval" in chunks[0].text


def test_chunks_long_text_without_losing_order() -> None:
    text = " ".join(f"Sentence {index} explains retrieval." for index in range(80))
    chunks = smart_chunk([ExtractedPage(page_number=1, text=text)], target_chars=220, overlap_chars=30)
    assert len(chunks) > 3
    assert chunks[0].chunk_index == 0
    assert chunks[-1].chunk_index == len(chunks) - 1


def test_splits_single_oversized_sentence_and_preserves_metadata() -> None:
    text = "DETAILS\n\n" + "retrieval " * 160
    chunks = smart_chunk(
        [ExtractedPage(page_number=4, text=text)],
        target_chars=180,
        overlap_chars=24,
    )
    assert len(chunks) > 2
    assert all(len(chunk.text) <= 180 for chunk in chunks)
    assert all(chunk.page_number == 4 and chunk.heading == "DETAILS" for chunk in chunks)
