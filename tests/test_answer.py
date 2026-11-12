import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from oil.answer import answer

PASS = []
FAIL = []


def check(name, cond):
    (PASS if cond else FAIL).append(name)
    print(("PASS" if cond else "FAIL"), "-", name)


class FakeIndex:
    """Returns preset chunks regardless of query (logic test, no embeddings)."""
    def __init__(self, chunks):
        self._chunks = chunks

    def search(self, query, k=5, min_score=0.0):
        return self._chunks[:k]


CHUNKS = [
    {"source": "/docs/services_agreement.md", "location": "", "chunk_index": 0,
     "text": "The monthly retainer is $12,000, payable net 30."},
    {"source": "/docs/employee_handbook.md", "location": "", "chunk_index": 0,
     "text": "Employees accrue 20 days of PTO per year."},
]
idx = FakeIndex(CHUNKS)


def gen(text):
    return lambda prompt: text


# ---- grounded answer with a valid citation ----
r = answer("retainer?", idx, generate=gen("The retainer is $12,000 [1]."))
check("answer: grounded answer is not refused", r["refused"] is False)
check("answer: citation maps [1] -> correct source",
      r["citations"] == [{"source": "services_agreement.md", "location": ""}])
check("answer: answer text preserved", "12,000" in r["answer"])
check("answer: chunks_used carries the cited chunk", len(r["chunks_used"]) == 1)

# ---- explicit NOT_FOUND -> refuse ----
r = answer("ceo salary?", idx, generate=gen("NOT_FOUND"))
check("answer: NOT_FOUND -> refused", r["refused"] is True and r["answer"] == "")

# ---- NOT_FOUND embedded in prose still refuses ----
r = answer("x?", idx, generate=gen("The documents do not cover this. NOT_FOUND"))
check("answer: NOT_FOUND in prose -> refused", r["refused"] is True)

# ---- hallucinated/out-of-range citation -> unsupported -> refuse ----
r = answer("x?", idx, generate=gen("It is $5,000 [9]."))
check("answer: out-of-range citation rejected -> refused", r["refused"] is True
      and "verifiable citation" in r["reason"])

# ---- a valid citation must not launder a fabricated one (found in review 2026-11-12) ----
r = answer("retainer?", idx, generate=gen("The retainer is $12,000 [1], due net 15 [999]."))
check("answer: valid [1] + out-of-range [999] -> refused", r["refused"] is True
      and "unverifiable" in r["reason"])
r = answer("retainer?", idx, generate=gen("The retainer is $12,000 [1] per the agreement [1]."))
check("answer: repeated valid citations still pass", r["refused"] is False)

# ---- answered with NO citation -> unsupported -> refuse ----
r = answer("x?", idx, generate=gen("It is probably $5,000."))
check("answer: uncited answer -> refused (strict trust)", r["refused"] is True)

# ---- correct mapping to the second source ----
r = answer("pto?", idx, generate=gen("Employees get 20 days [2]."))
check("answer: [2] maps to second source",
      r["citations"] == [{"source": "employee_handbook.md", "location": ""}])

# ---- page-level citation: location is surfaced ----
paged = FakeIndex([{"source": "/docs/report.pdf", "location": "p13",
                    "chunk_index": 0, "text": "the result was 42"}])
r = answer("result?", paged, generate=gen("The result was 42 [1]."))
check("answer: citation carries page location",
      r["citations"] == [{"source": "report.pdf", "location": "p13"}])
from oil.answer import format_citations
check("answer: format_citations renders file + page",
      format_citations(r["citations"]) == "report.pdf, p13")

# ---- dedupe identical (source, location) references ----
multi = FakeIndex(CHUNKS + [{"source": "/docs/services_agreement.md",
                             "location": "", "chunk_index": 1, "text": "more terms"}])
r = answer("x?", multi, generate=gen("See [1] and [3]."))
check("answer: identical (source,location) deduped to one citation",
      r["citations"] == [{"source": "services_agreement.md", "location": ""}])

# ---- no passages retrieved -> refuse ----
r = answer("x?", FakeIndex([]), generate=gen("anything [1]"))
check("answer: no passages -> refused", r["refused"] is True)

# ---- empty model output -> refuse ----
r = answer("x?", idx, generate=gen(""))
check("answer: empty output -> refused", r["refused"] is True)

# ---- 2026-11-12: gpt-oss writes citations as 【1】 (full-width brackets) ----
r = answer("retainer?", idx, generate=gen("The monthly retainer fee is **$12,000 USD**【1】."))
check("answer: full-width citation is read as [1]",
      r["refused"] is False and r["citations"] == [{"source": "services_agreement.md", "location": ""}])
check("answer: returned text uses the normal [1] form", "[1]" in r["answer"] and "【" not in r["answer"])
r = answer("retainer?", idx, generate=gen("The retainer is $12,000 【1】【999】."))
check("answer: an invented full-width citation still refuses", r["refused"] is True)
r = answer("retainer?", idx, generate=gen("The retainer is $12,000 【note】."))
check("answer: full-width brackets around non-numbers are not citations", r["refused"] is True)


print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
sys.exit(1 if FAIL else 0)
