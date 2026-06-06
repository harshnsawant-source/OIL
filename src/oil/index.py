"""Chunked local vector index. Stores each chunk's text + source/location
metadata + embedding, and retrieves by cosine similarity. JSON-persisted for
now (simple + correct); the storage backend is deliberately swappable behind
this class so it can become a real embedded vector store when scale demands it.

Retrieval returns chunks WITH their source + location + score — the raw material
for citations. Vectors are never returned to callers.
"""

import json
from pathlib import Path

import numpy as np

from oil.embeddings import embed


class DocIndex:

    def __init__(self):
        self.chunks = []   # each: {source, location, chunk_index, text, vector}

    def build(self, chunks):
        self.chunks = []
        skipped = 0
        for c in chunks:
            vector = embed(c["text"])
            if vector is None:
                skipped += 1
                continue
            record = dict(c)
            record["vector"] = vector
            self.chunks.append(record)
        return {"indexed": len(self.chunks), "skipped": skipped}

    def search(self, query, k=5, min_score=0.25):
        # min_score is a retrieval floor: chunks below it are noise, not weak
        # matches. Returning irrelevant chunks would poison grounding/citations,
        # so they are excluded here. (The answer layer applies its own, stricter
        # threshold to decide when to REFUSE entirely.)
        query_vector = embed(query)
        if query_vector is None or not self.chunks:
            return []

        q = np.asarray(query_vector, dtype=float)
        q_norm = np.linalg.norm(q)
        if q_norm == 0:
            return []

        scored = []
        for c in self.chunks:
            v = np.asarray(c["vector"], dtype=float)
            v_norm = np.linalg.norm(v)
            if v_norm == 0 or v.shape != q.shape:
                continue
            score = float(np.dot(q, v) / (q_norm * v_norm))
            if score >= min_score:
                scored.append((score, c))

        scored.sort(key=lambda x: -x[0])

        results = []
        for score, c in scored[:k]:
            results.append({
                "source": c["source"],
                "location": c["location"],
                "chunk_index": c["chunk_index"],
                "text": c["text"],
                "score": round(score, 4),
            })
        return results

    def save(self, path):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"chunks": self.chunks}), encoding="utf-8")

    @classmethod
    def load(cls, path):
        index = cls()
        path = Path(path)
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            index.chunks = data.get("chunks", [])
        return index
