"""Document ingestion: load a folder of documents into chunks that carry the
metadata needed for citations (source file + location label + chunk index).

Loaders are pluggable. TXT/MD need no dependencies; PDF (pypdf) and DOCX
(python-docx) are imported lazily so the module loads without them. Excel and
OCR/images are deliberately NOT here yet (Phases 2 and 3).
"""

from pathlib import Path

# Chunking: ~1000 chars with overlap so an answer-bearing passage is rarely split
# across a boundary. location = a human-citable spot ("p3" for PDF page 3, "" otherwise).
CHUNK_CHARS = 1000
OVERLAP = 150


def _load_txt(path):
    return [(Path(path).read_text(encoding="utf-8", errors="ignore"), "")]


_OCR_MIN_CHARS = 20   # a page with less extractable text than this is likely scanned


def _load_pdf(path):
    from pypdf import PdfReader
    reader = PdfReader(str(path))
    page_texts = [(page.extract_text() or "") for page in reader.pages]

    # OCR fallback for scanned pages (little/no embedded text), if OCR is set up.
    low = [i for i, t in enumerate(page_texts) if len(t.strip()) < _OCR_MIN_CHARS]
    if low:
        from oil.ocr import ocr_pdf_pages
        for i, text in ocr_pdf_pages(path, low).items():
            if text.strip():
                page_texts[i] = text

    return [(t, f"p{n}") for n, t in enumerate(page_texts, start=1) if t.strip()]


def _load_docx(path):
    import docx  # python-docx
    document = docx.Document(str(path))
    text = "\n".join(p.text for p in document.paragraphs)
    return [(text, "")] if text.strip() else []


def _load_xlsx(path):
    import openpyxl
    wb = openpyxl.load_workbook(str(path), read_only=True, data_only=True)
    out = []
    for ws in wb.worksheets:
        rows = []
        for row in ws.iter_rows(values_only=True):
            cells = ["" if v is None else str(v) for v in row]
            if any(c.strip() for c in cells):
                rows.append(" | ".join(cells))
        if rows:
            text = f"Sheet: {ws.title}\n" + "\n".join(rows)
            out.append((text, f"sheet:{ws.title}"))
    wb.close()
    return out


def _load_image(path):
    # Scanned image -> OCR. Empty (skipped) if OCR isn't configured.
    from oil.ocr import ocr_image
    text = ocr_image(path)
    return [(text, "")] if text.strip() else []


LOADERS = {
    ".txt": _load_txt,
    ".md": _load_txt,
    ".pdf": _load_pdf,
    ".docx": _load_docx,
    ".xlsx": _load_xlsx,
    ".png": _load_image,
    ".jpg": _load_image,
    ".jpeg": _load_image,
    ".tiff": _load_image,
    ".bmp": _load_image,
}


def is_supported(path):
    return Path(path).suffix.lower() in LOADERS


def chunk_text(text, source, location=""):
    text = (text or "").strip()
    if not text:
        return []
    step = max(CHUNK_CHARS - OVERLAP, 1)
    chunks = []
    i = 0
    idx = 0
    while i < len(text):
        chunks.append({
            "source": str(source),
            "location": location,
            "chunk_index": idx,
            "text": text[i:i + CHUNK_CHARS],
        })
        idx += 1
        i += step
    return chunks


def load_document(path):
    path = Path(path)
    loader = LOADERS.get(path.suffix.lower())
    if loader is None:
        return []
    chunks = []
    for text, location in loader(path):
        chunks.extend(chunk_text(text, path, location))
    return chunks


def load_folder(folder):
    folder = Path(folder)
    chunks = []
    for path in sorted(folder.rglob("*")):
        if not path.is_file() or path.name.startswith("."):
            continue
        if is_supported(path):
            chunks.extend(load_document(path))
    return chunks
