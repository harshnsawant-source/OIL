"""Local embeddings via Ollama (nomic-embed-text). No network beyond localhost;
nothing leaves the device. Returns None on failure so callers degrade gracefully."""

import requests

OLLAMA_EMBED_URL = "http://localhost:11434/api/embeddings"
EMBED_MODEL = "nomic-embed-text"

# nomic caps ~2048 tokens; truncate the head of long chunks before embedding.
EMBED_CHAR_LIMIT = 4000


def embed(text):
    text = (text or "")[:EMBED_CHAR_LIMIT]
    if not text.strip():
        return None
    try:
        resp = requests.post(
            OLLAMA_EMBED_URL,
            json={"model": EMBED_MODEL, "prompt": text},
            timeout=60,
        )
        resp.raise_for_status()
        vector = resp.json().get("embedding")
        return vector or None
    except Exception:
        return None
