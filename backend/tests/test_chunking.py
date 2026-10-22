import pytest
from pdf_helper import make_pdf

from services.chunking import ExtractionError, chunk_fixed, chunk_structured, extract_pages


def test_chunks_follow_headings_and_carry_the_section():
    text = (
        "# Lists\n\nPython lists are ordered and mutable.\n\n"
        "## Slicing\n\nUse nums[::-1] to get a reversed copy.\n\n"
        "# Dictionaries\n\nDictionaries map keys to values.\n"
    )
    chunks = chunk_structured([(None, text)])
    assert [(c["section"], c["page"]) for c in chunks] == [("Lists", None), ("Slicing", None), ("Dictionaries", None)]
    assert chunks[1]["text"] == "Slicing\nUse nums[::-1] to get a reversed copy."


def test_numbered_and_uppercase_headings():
    text = "INTRODUCTION\nThis course covers databases.\n\n2.1 Inner joins\nAn inner join keeps matching rows only.\n"
    sections = [c["section"] for c in chunk_structured([(None, text)])]
    assert sections == ["Introduction", "2.1 Inner joins"]


def test_chunks_never_cross_pages():
    chunks = chunk_structured([(1, "Alpha topic text."), (2, "Beta topic text.")])
    assert [(c["page"], c["text"]) for c in chunks] == [(1, "Alpha topic text."), (2, "Beta topic text.")]


def test_long_sections_are_split_with_overlap_and_paragraphs_kept_whole():
    paragraphs = [f"Paragraph {i} " + "word " * 60 for i in range(6)]
    chunks = chunk_structured([(None, "# Topic\n\n" + "\n\n".join(paragraphs))], limit=900)
    assert len(chunks) > 1
    assert all(len(c["text"]) <= 900 + 200 for c in chunks)
    assert all(c["section"] == "Topic" for c in chunks)
    # Each chunk after the first starts with the tail of the previous one
    assert chunks[1]["text"].split("\n", 1)[1][:20] in chunks[0]["text"]


def test_giant_paragraph_is_split_at_sentences():
    text = " ".join(f"Sentence number {i} is here." for i in range(200))
    chunks = chunk_structured([(None, text)], limit=500)
    assert len(chunks) > 5
    assert all(c["text"].endswith(".") for c in chunks[:-1])


def test_fixed_chunker_baseline():
    chunks = chunk_fixed([(None, "x" * 2500)])
    assert [len(c["text"]) for c in chunks] == [1000, 1000, 900, 100]


def test_pdf_extraction_is_per_page():
    pages = extract_pages("doc.pdf", make_pdf(["First page", "Second page"]))
    assert [(n, t.strip()) for n, t in pages] == [(1, "First page"), (2, "Second page")]


def test_extraction_errors():
    with pytest.raises(ExtractionError, match="PDF"):
        extract_pages("bad.pdf", b"nope")
    with pytest.raises(ExtractionError, match="Unsupported"):
        extract_pages("x.docx", b"data")
