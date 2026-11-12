# OIL — Private Document Intelligence

> Ask questions about your confidential documents and get answers **cited to the
> exact source**, with an honest **"not in your documents"** when it doesn't know —
> running **on your own machine by default**, so in local mode nothing leaves the building.

For people and firms who **legally cannot** put client data into ChatGPT: lawyers,
accountants, advisors, clinicians, and anyone bound by confidentiality or
regulation. The selling point isn't "AI" — it's **trust** (grounded, cited, refuses
when it has no source) and **privacy** (local by default, auditable).

## What it is (and isn't)

- **Is:** a local, on-prem assistant that does grounded, cited Q&A over a folder of
  your confidential documents, with a verifiable audit trail of what it accessed.
- **Is not:** a chatbot, an agent framework, a personal-life model, or anything
  that depends on a cloud API. (Those experiments live in the sibling
  `obsidian-intelligence-layer` repo — this is the focused product that came out of
  what that taught me.)

## The one thing that matters: the trust engine

Conservative professionals don't fear "is the AI smart enough" — they fear
**"will it make something up and cost me my license."** So the core is:

1. **Grounded** — every answer is generated *only* from retrieved passages of your
   documents.
2. **Cited** — every claim links to the exact source file + page/section.
3. **Refuses** — when the documents don't contain the answer, it says so instead of
   guessing.
4. **Auditable** — a log of exactly which documents were accessed.
5. **Local** — embeddings and generation run on hardware *you* own; in a firm,
   that can be a real GPU box, so capability is not limited to a laptop.

Trust is measured, not hoped for: a small eval set of *questions-with-known-sources*
and *questions-that-should-be-refused* gates **citation accuracy** and **refusal
correctness**. The current labeled set has 14 answerable questions and 5 that must
be refused, over a small synthetic corpus (`eval/`). Run on 12 Nov 2026 with
gpt-oss-120b (Groq) standing in for a capable local model
(`python eval/run_eval.py cloud`):

| | Result |
|---|---|
| Answerable: cited the expected source and contained the key fact | **13/14** |
| Unanswerable: refused | **5/5** |
| Answerable questions wrongly refused | **0** |

The one miss cited the right file but failed the key-fact check ("net 30"); the reply
from that run was not saved, so whether the wording or the fact was wrong is not known.
An earlier run with a now-retired model scored 14/14 on the answerable questions.
The eval has not yet been run in full on the local default model. A valid citation
shows which passage was used, not that the answer follows from it.

## MVP scope (ruthless)

**In:**
- Ingest a folder of documents (txt/md first; PDF/docx next) → **chunk** with
  source + page metadata → local embed → index.
- Grounded, cited answer with a calibrated refusal path.
- Per-folder/matter scoping + access audit log.
- A dead-simple local UI (no CLI menus for the buyer).

**Out (for now):** drafting/generation beyond Q&A, cloud, multi-user, integrations,
agents/orchestration, personal-memory features.

## First milestone (the proving spike)

Drop ~10 real documents in a folder → ask 5 questions → get **correct citations**
and **correct refusals** on the 2 the documents don't cover. If that's trustworthy,
the product exists; everything after is packaging and sales.

## Status

Bootstrapping. Reuses the proven pieces from `obsidian-intelligence-layer` (local
embeddings, retrieval, privacy/consent, output-health) and rebuilds the trust
engine (chunked + cited + grounded + refusal) cleanly, without the orchestration
baggage.

## Supported document formats

Text/Markdown, **PDF** (text + scanned via OCR), **Word (.docx)**, **Excel (.xlsx)**,
and **images** (.png/.jpg/.tiff/.bmp via OCR). PDF citations are page-level
(`p13`); Excel citations are per sheet (`sheet:Invoices`).

## Run

```bash
pip install -r requirements.txt
ollama pull nomic-embed-text     # local embeddings
ollama pull nemotron-3-nano:4b   # local answer model (default)
python run_ui.py                 # open http://127.0.0.1:5000
```
Point it at a folder of documents, then ask. Answers cite the source page; if the
answer isn't in your documents it says so. The UI runs on 127.0.0.1 only.
Generation is local by default, and in that mode nothing leaves the machine.
`OIL_MODEL=cloud` sends retrieved passages to gpt-oss-120b on Groq's free tier and
is for demos on non-confidential data only. It needs a Groq key in the
`GROQ_API_KEY` environment variable; without one, cloud mode refuses every question.
The badge at the top of the page shows which mode is active. Override the models with
`OIL_LOCAL_MODEL` (any Ollama model) and `OIL_CLOUD_MODEL` (any Groq model).

**OCR (scanned PDFs + images)** also needs the Tesseract engine (a system binary,
not pip). Everything else works without it; until it's installed, images/scanned
pages are skipped gracefully (`oil.ocr.ocr_available()` reports readiness):

```bash
# Windows
winget install UB-Mannheim.TesseractOCR
# macOS:  brew install tesseract     Linux:  sudo apt-get install tesseract-ocr
```
