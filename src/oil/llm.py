"""Local-pinned text generation via Ollama. Model-agnostic by design.

`local_generate` is the privacy default (runs on-device). `cloud_generate` exists
ONLY for evaluating the engine against synthetic, non-confidential test data — it
must never be pointed at real client documents. In production the answer engine
uses `local_generate` (on the buyer's own hardware), so nothing leaves the device.
"""

import requests

OLLAMA_GEN_URL = "http://localhost:11434/api/generate"
LOCAL_MODEL = "qwen3.5:4b"
CLOUD_MODEL = "qwen3-coder:480b-cloud"   # synthetic-eval only; never real data


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
    return _generate(prompt, LOCAL_MODEL, timeout=120)


def cloud_generate(prompt):
    return _generate(prompt, CLOUD_MODEL, timeout=300)
