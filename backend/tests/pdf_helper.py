"""Build small text PDFs for tests without extra dependencies."""


def _escape(text):
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def make_pdf(page_texts):
    """A valid PDF with one page per string; newlines in a string become separate text lines."""
    objects = []

    def add(body):
        objects.append(body)
        return len(objects)

    font = add(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    pages = add(b"")  # filled in once the page ids are known
    page_ids = []
    for text in page_texts:
        lines = " ".join(f"({_escape(line)}) Tj T*" for line in text.split("\n"))
        stream = f"BT /F1 11 Tf 14 TL 72 740 Td {lines} ET"
        content = add(f"<< /Length {len(stream)} >>\nstream\n{stream}\nendstream".encode())
        page_ids.append(add(
            f"<< /Type /Page /Parent {pages} 0 R /MediaBox [0 0 612 792] /Contents {content} 0 R "
            f"/Resources << /Font << /F1 {font} 0 R >> >> >>".encode()
        ))
    kids = " ".join(f"{p} 0 R" for p in page_ids)
    objects[pages - 1] = f"<< /Type /Pages /Kids [{kids}] /Count {len(page_ids)} >>".encode()
    catalog = add(f"<< /Type /Catalog /Pages {pages} 0 R >>".encode())

    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{number} 0 obj\n".encode() + body + b"\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode()
    for offset in offsets:
        out += f"{offset:010d} 00000 n \n".encode()
    out += f"trailer\n<< /Size {len(objects) + 1} /Root {catalog} 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    return bytes(out)
