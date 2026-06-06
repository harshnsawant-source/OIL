import sys
import tempfile
import shutil
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from oil import ingest
import oil.ocr as ocr

PASS = []
FAIL = []


def check(name, cond):
    (PASS if cond else FAIL).append(name)
    print(("PASS" if cond else "FAIL"), "-", name)


tmp = Path(tempfile.mkdtemp(prefix="oil_loaders_"))
try:
    # ---- Excel (.xlsx), live via openpyxl ----
    import openpyxl
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Invoices"
    ws.append(["Invoice", "Amount", "Status"])
    ws.append([1043, 12000, "OUTSTANDING"])
    ws2 = wb.create_sheet("Notes")
    ws2.append(["Late fee is 1.5% per month"])
    wb.save(tmp / "book.xlsx")

    xlsx = ingest.load_document(tmp / "book.xlsx")
    check("xlsx: loaded chunks", len(xlsx) >= 1)
    inv = [c for c in xlsx if c["location"] == "sheet:Invoices"]
    check("xlsx: location is the sheet name", len(inv) == 1)
    text = inv[0]["text"]
    check("xlsx: rows captured with headers",
          "Invoice" in text and "1043" in text and "OUTSTANDING" in text)
    check("xlsx: second sheet also captured",
          any(c["location"] == "sheet:Notes" for c in xlsx))

    # ---- image loader: OCR dispatch (Tesseract not required for this test) ----
    (tmp / "scan.png").write_bytes(b"not-a-real-png")  # stub OCR ignores bytes
    _real = ocr.ocr_image
    ocr.ocr_image = lambda p: "OCR_MARKER scanned invoice total 12000"
    try:
        img = ingest.load_document(tmp / "scan.png")
        check("image: OCR text ingested into chunks",
              len(img) == 1 and "OCR_MARKER" in img[0]["text"])
        check("image: source recorded", img[0]["source"].endswith("scan.png"))
    finally:
        ocr.ocr_image = _real

    # ---- image loader: graceful skip when OCR yields nothing ----
    ocr.ocr_image = lambda p: ""
    try:
        check("image: empty OCR -> skipped (no crash)",
              ingest.load_document(tmp / "scan.png") == [])
    finally:
        ocr.ocr_image = _real

    # ---- ocr_available reflects the environment (callable, boolean) ----
    check("ocr: ocr_available() returns a bool", isinstance(ocr.ocr_available(), bool))

    # ---- supported extensions registered ----
    for ext in ("book.xlsx", "scan.png", "p.jpg", "p.tiff"):
        check(f"supported: {ext}", ingest.is_supported(tmp / ext))
finally:
    shutil.rmtree(tmp, ignore_errors=True)


print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
sys.exit(1 if FAIL else 0)
