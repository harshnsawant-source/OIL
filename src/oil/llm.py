"""Text generation. Model-agnostic by design.

`local_generate` is the privacy default: Ollama on this machine, nothing leaves it.
`cloud_generate` sends the prompt (which contains retrieved passages) to gpt-oss-120b
on Groq's free tier. It exists ONLY for evaluating the engine on synthetic,
non-confidential data and must never be pointed at real client documents. The key
comes from the GROQ_API_KEY environment variable and is never stored in a file.
Both functions return "" on any failure and never raise; the answer engine treats an
empty reply as a refusal.
"""

import os
import requests

OLLAMA_GEN_URL = "http://localhost:11434/api/generate"
# Configurable so you can measure the minimum viable local model on real
# hardware (e.g. OIL_LOCAL_MODEL=qwen2.5:7b-instruct) without code changes.
LOCAL_MODEL = os.environ.get("OIL_LOCAL_MODEL", "nemotron-3-nano:4b")
# Ollama's free cloud models became pay-per-token in Nov 2026; Groq's free tier
# serves the same open gpt-oss weights through an OpenAI-compatible API.
CLOUD_MODEL = os.environ.get("OIL_CLOUD_MODEL", "openai/gpt-oss-120b")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"


def _generate(prompt, model, max_tokens=600, timeout=120):
    try:
        resp = requests.post(
            OLLAMA_GEN_URL,
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.0, "num_predict": max_tokens},
            },
            timeout=timeout,
        )
        resp.raise_for_status()
        return (resp.json().get("response") or "").strip()
    except Exception:
        return ""


def local_generate(prompt):
    # Generous default: a 7B on a weak CPU can take minutes — a too-short timeout
    # would return empty and be misread as a model failure (it's just slow).
    timeout = int(os.environ.get("OIL_LOCAL_TIMEOUT", "300"))
    return _generate(prompt, LOCAL_MODEL, timeout=timeout)


def cloud_generate(prompt):
    key = os.environ.get("GROQ_API_KEY")
    if not key:
        return ""
    try:
        resp = requests.post(
            GROQ_URL,
            json={"model": CLOUD_MODEL, "temperature": 0,
                  "messages": [{"role": "user", "content": prompt}]},
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            timeout=300,
        )
        resp.raise_for_status()
        msg = resp.json()["choices"][0]["message"]
        return (msg.get("content") or "").strip()
    except Exception:
        return ""
