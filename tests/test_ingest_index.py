import sys
import tempfile
import shutil
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import oil.index as index_mod
from oil import ingest
from oil.index import DocIndex

PASS = []
FAIL = []


def check(name, cond):
    (PASS if cond else FAIL).append(name)
    print(("PASS" if cond else "FAIL"), "-", name)


# Deterministic, content-sensitive embedding stub (one-hot over tag markers) so
# indexing + cosine search are predictable without Ollama.
_TAGS = ["ALPHA", "BETA", "GAMMA", "DELTA"]


def fake_embed(text):
    text = text or ""
    if not text.strip():
        return None
    return [1.0 if t in text else 0.0 for t in _TAGS]


index_mod.embed = fake_embed


# ---- chunking carries citation metadata ----------------------------------
chunks = ingest.chunk_text("x" * 2500, "/docs/a.txt", "p1")
check("chunk: long text splits into multiple chunks", len(chunks) >= 3)
check("chunk: carries source", chunks[0]["source"] == "/docs/a.txt")
check("chunk: carries location", chunks[0]["location"] == "p1")
check("chunk: chunk_index increments", [c["chunk_index"] for c in chunks[:3]] == [0, 1, 2])
check("chunk: overlap (chunks share boundary text)",
      chunks[0]["text"][-50:] in (chunks[0]["text"] + chunks[1]["text"]))
check("chunk: empty text -> no chunks", ingest.chunk_text("   ", "x") == [])


# ---- folder loading + loader dispatch ------------------------------------
tmp = Path(tempfile.mkdtemp(prefix="oil_ingest_"))
try:
    (tmp / "note.md").write_text("ALPHA content in markdown", encoding="utf-8")
    (tmp / "memo.txt").write_text("BETA content in text", encoding="utf-8")
    (tmp / "ignore.bin").write_text("unsupported", encoding="utf-8")
    (tmp / ".hidden.md").write_text("GAMMA hidden", encoding="utf-8")
    sub = tmp / "sub"
    sub.mkdir()
    (sub / "deep.txt").write_text("DELTA nested content", encoding="utf-8")

    loaded = ingest.load_folder(tmp)
    sources = {Path(c["source"]).name for c in loaded}
    check("ingest: supported files loaded recursively",
          {"note.md", "memo.txt", "deep.txt"} <= sources)
    check("ingest: unsupported extension skipped", "ignore.bin" not in sources)
    check("ingest: hidden file skipped", ".hidden.md" not in sources)

    # ---- index build + cited retrieval -----------------------------------
    idx = DocIndex()
    stats = idx.build(loaded)
    check("index: built all loaded chunks", stats["indexed"] == len(loaded))

    hits = idx.search("ALPHA", k=3)
    check("search: returns the matching chunk",
          len(hits) == 1 and Path(hits[0]["source"]).name == "note.md")
    check("search: result carries source+location+score for citation",
          "source" in hits[0] and "location" in hits[0] and "score" in hits[0])
    check("search: vector is NOT leaked to callers", "vector" not in hits[0])

    hits_delta = idx.search("DELTA", k=3)
    check("search: nested doc retrievable",
          hits_delta and Path(hits_delta[0]["source"]).name == "deep.txt")

    check("search: empty index returns nothing", DocIndex().search("ALPHA") == [])

    # ---- persistence roundtrip -------------------------------------------
    store = tmp / "idx.json"
    idx.save(store)
    reloaded = DocIndex.load(store)
    check("persist: reload preserves chunks", len(reloaded.chunks) == len(idx.chunks))
    check("persist: reloaded index still searches",
          Path(reloaded.search("BETA")[0]["source"]).name == "memo.txt")
finally:
    shutil.rmtree(tmp, ignore_errors=True)


print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
sys.exit(1 if FAIL else 0)
