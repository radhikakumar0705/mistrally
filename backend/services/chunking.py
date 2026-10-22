"""
Text extraction and chunking for retrieval.

`chunk_structured` (used by the app) splits documents along their structure: chunks never cross a
page or a heading, paragraphs are kept whole where possible, and every chunk carries its page number
and section title, which is also prepended to the text so the embedding knows the context.
`chunk_fixed` is the original fixed-size splitter, kept as the baseline for the retrieval evaluation.
"""
import io
import re

from pypdf import PdfReader

ALLOWED_EXTENSIONS = {"pdf", "txt", "md"}

CHUNK_CHARS = 900
MIN_CHUNK_CHARS = 120
OVERLAP_CHARS = 150

_MARKDOWN_HEADING = re.compile(r"^#{1,6}\s+(.+?)\s*#*$")
_NUMBERED_HEADING = re.compile(r"^(\d+(?:\.\d+)*)[.)]?\s+([A-Z][^.!?:]{2,80})$")
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+")


class ExtractionError(Exception):
    """The file could not be read; the message is safe to show to the user."""


def file_type(filename):
    return filename.rsplit(".", 1)[1].lower() if "." in filename else ""


def allowed_file(filename):
    return file_type(filename) in ALLOWED_EXTENSIONS


def extract_pages(filename, data):
    """Return [(page_number or None, text)] for a PDF, TXT or Markdown file's bytes."""
    kind = file_type(filename)
    if kind == "pdf":
        try:
            reader = PdfReader(io.BytesIO(data))
            return [(i + 1, page.extract_text() or "") for i, page in enumerate(reader.pages)]
        except Exception as e:
            raise ExtractionError("Could not read that PDF") from e
    if kind in ("txt", "md"):
        return [(None, data.decode("utf-8", errors="ignore"))]
    raise ExtractionError(f"Unsupported file type: .{kind}")


def _heading(line):
    line = line.strip()
    if not line or len(line) > 90:
        return None
    match = _MARKDOWN_HEADING.match(line)
    if match:
        return match.group(1).strip()
    match = _NUMBERED_HEADING.match(line)
    if match:
        return line
    letters = [c for c in line if c.isalpha()]
    if len(letters) >= 4 and all(c.isupper() for c in letters) and not line.endswith((".", ",", ";")):
        return line.title()
    return None


def _sections(pages):
    """Yield (page, section_title, [paragraphs]) blocks in document order."""
    section = None
    for page, text in pages:
        paragraphs, current = [], []
        for raw in text.replace("\r\n", "\n").split("\n"):
            title = _heading(raw)
            if title:
                if current:
                    paragraphs.append(" ".join(current))
                    current = []
                if paragraphs:
                    yield page, section, paragraphs
                    paragraphs = []
                section = title
            elif raw.strip():
                current.append(raw.strip())
            elif current:
                paragraphs.append(" ".join(current))
                current = []
        if current:
            paragraphs.append(" ".join(current))
        if paragraphs:
            yield page, section, paragraphs


def _split_long(paragraph, limit):
    """Split an over-long paragraph at sentence boundaries (or hard-split a giant sentence)."""
    pieces, current = [], ""
    for sentence in _SENTENCE_END.split(paragraph):
        while len(sentence) > limit:
            pieces.append(sentence[:limit])
            sentence = sentence[limit:]
        if len(current) + len(sentence) + 1 > limit and current:
            pieces.append(current)
            current = sentence
        else:
            current = f"{current} {sentence}".strip()
    if current:
        pieces.append(current)
    return pieces


def chunk_structured(pages, limit=CHUNK_CHARS):
    """Chunks that respect pages, headings and paragraphs: [{"text", "page", "section"}]."""
    chunks = []
    for page, section, paragraphs in _sections(pages):
        units = [piece for p in paragraphs for piece in _split_long(p, limit)]
        body = ""
        for unit in units:
            if body and len(body) + len(unit) + 2 > limit:
                chunks.append((page, section, body))
                # Overlap: start the next chunk with the end of the previous one
                tail = body[-OVERLAP_CHARS:]
                body = (tail[tail.find(" ") + 1:] + "\n\n" + unit) if " " in tail else unit
            else:
                body = f"{body}\n\n{unit}" if body else unit
        if body:
            # Fold a tiny trailing piece into the previous chunk of the same section and page
            if chunks and len(body) < MIN_CHUNK_CHARS and chunks[-1][:2] == (page, section):
                prev = chunks.pop()
                body = f"{prev[2]}\n\n{body}"
            chunks.append((page, section, body))

    return [
        {"text": f"{section}\n{body}" if section else body, "page": page, "section": section}
        for page, section, body in chunks
    ]


def chunk_fixed(pages, size=1000, overlap=200):
    """The original splitter: fixed-size windows over the whole text, ignoring structure."""
    text = "\n".join(t for _, t in pages).strip()
    chunks, start = [], 0
    while start < len(text):
        piece = text[start:start + size].strip()
        if piece:
            chunks.append({"text": piece, "page": None, "section": None})
        start += size - overlap
    return chunks
