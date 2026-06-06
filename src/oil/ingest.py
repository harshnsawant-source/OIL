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


def _load_pdf(path):
    from pypdf import PdfReader
    reader = PdfReader(str(path))
    pages = []
    for n, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        if text.strip():
            pages.append((text, f"p{n}"))
    return pages


def _load_docx(path):
    import docx  # python-docx
    document = docx.Document(str(path))
    text = "\n".join(p.text for p in document.paragraphs)
    return [(text, "")] if text.strip() else []


LOADERS = {
    ".txt": _load_txt,
    ".md": _load_txt,
    ".pdf": _load_pdf,
    ".docx": _load_docx,
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
