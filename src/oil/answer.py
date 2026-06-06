"""The trust engine: grounded, cited, refusing answers over the user's documents.

Design (decided from the eval data, where unanswerable questions overlap the
answerable score range, so a cosine threshold can't separate them):

  1. Retrieve candidate passages (a low floor only drops pure noise).
  2. Ground: the model may answer ONLY from the numbered passages, must cite the
     source number(s) it used, and must reply NOT_FOUND if the answer isn't there.
     The model — not a score — decides answerable-vs-refuse.
  3. Verify: citations are checked against the passages actually retrieved.
     An answer with no verifiable citation is treated as unsupported and refused.

Result dict: {refused, answer, citations:[source names], chunks_used, reason}.
"""

import re
from pathlib import Path

from oil.llm import local_generate

NOT_FOUND = "NOT_FOUND"
RETRIEVAL_FLOOR = 0.45   # drop pure noise only; grounding decides refusal
TOP_K = 5

_CITE_RE = re.compile(r"\[(\d+)\]")


def _build_prompt(query, chunks):
    blocks = []
    for i, c in enumerate(chunks, start=1):
        src = Path(c["source"]).name
        loc = f" {c['location']}" if c.get("location") else ""
        blocks.append(f"[{i}] ({src}{loc}) {c['text']}")
    sources = "\n\n".join(blocks)
    return (
        "Answer the question using ONLY the numbered sources below — passages from "
        "the user's own documents.\n\n"
        "Rules:\n"
        "- If the answer is in the sources, answer concisely and cite the source "
        "number(s) you used, e.g. [1] or [2][3].\n"
        f"- If the sources do NOT contain the answer, reply with exactly: {NOT_FOUND}\n"
        "- Use no outside knowledge. Do not guess.\n\n"
        f"Sources:\n{sources}\n\n"
        f"Question: {query}\n\nAnswer:"
    )


def _refused(reason):
    return {"refused": True, "answer": "", "citations": [], "chunks_used": [],
            "reason": reason}


def answer(query, index, k=TOP_K, generate=local_generate):
    chunks = index.search(query, k=k, min_score=RETRIEVAL_FLOOR)
    if not chunks:
        return _refused("no relevant passages retrieved")

    raw = generate(_build_prompt(query, chunks))
    if not raw:
        return _refused("model produced no output")

    if NOT_FOUND in raw.upper():
        return _refused("answer not found in the documents")

    # Citation verification: only accept markers that point at a retrieved passage.
    valid = sorted({n for n in (int(m) for m in _CITE_RE.findall(raw))
                    if 1 <= n <= len(chunks)})
    if not valid:
        # Answered, but we cannot verify it against a source -> do not trust it.
        return _refused("answer had no verifiable citation")

    cited = [chunks[n - 1] for n in valid]
    citations = []
    for c in cited:
        src = Path(c["source"]).name
        if src not in citations:
            citations.append(src)

    return {
        "refused": False,
        "answer": raw.strip(),
        "citations": citations,
        "chunks_used": cited,
        "reason": "answered from documents",
    }
