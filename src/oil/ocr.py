"""OCR for images and scanned PDFs. Local-only (Tesseract runs on-device).

Tesseract is a SYSTEM binary, not a pip package, so it must be installed
separately:
    Windows:  winget install UB-Mango.TesseractOCR   (or the UB-Mannheim installer)
    macOS:    brew install tesseract
    Linux:    sudo apt-get install tesseract-ocr

Everything here degrades gracefully: if Tesseract (or its python bindings /
PyMuPDF) is unavailable, OCR returns empty and the document/page is simply
skipped — never a crash. ocr_available() reports readiness.
"""

import io
import shutil


def ocr_available():
    try:
        import pytesseract  # noqa: F401
    except Exception:
        return False
    # The python binding is useless without the actual tesseract executable.
    return shutil.which("tesseract") is not None


def ocr_image(path):
    if not ocr_available():
        return ""
    try:
        import pytesseract
        from PIL import Image
        return (pytesseract.image_to_string(Image.open(str(path))) or "").strip()
    except Exception:
        return ""


def ocr_pdf_pages(path, page_indices, dpi=200):
    # Render the given 0-based page indices of a (scanned) PDF and OCR them.
    # Returns {page_index: text}. Empty dict if OCR/PyMuPDF unavailable.
    if not ocr_available() or not page_indices:
        return {}
    out = {}
    try:
        import fitz  # PyMuPDF
        import pytesseract
        from PIL import Image
        doc = fitz.open(str(path))
        for i in page_indices:
            if 0 <= i < doc.page_count:
                pix = doc[i].get_pixmap(dpi=dpi)
                img = Image.open(io.BytesIO(pix.tobytes("png")))
                out[i] = (pytesseract.image_to_string(img) or "").strip()
        doc.close()
    except Exception:
        return out
    return out
