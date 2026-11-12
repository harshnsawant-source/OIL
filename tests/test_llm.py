"""Model routing in oil.llm, tested offline with a fake HTTP layer.

2026-11-12: the local default (qwen3.5:4b) is no longer installed, and the cloud default
(qwen3-coder:480b-cloud on Ollama) was retired. Local moves to nemotron-3-nano:4b; cloud
moves to gpt-oss-120b on Groq's free tier, with the key read from GROQ_API_KEY.
"""
import importlib
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

PASS, FAIL = [], []


def check(name, cond):
    (PASS if cond else FAIL).append(name)
    print(("PASS" if cond else "FAIL"), "-", name)


for k in ("OIL_LOCAL_MODEL", "OIL_CLOUD_MODEL", "GROQ_API_KEY"):
    os.environ.pop(k, None)

import oil.llm as llm
llm = importlib.reload(llm)


class _Resp:
    def __init__(self, data, status=200):
        self._data, self.status_code = data, status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self):
        return self._data


calls = []


def fake_post(url, json=None, headers=None, timeout=None):
    calls.append({"url": url, "json": json, "headers": headers or {}})
    if "groq.com" in url:
        return _Resp({"choices": [{"message": {"content": " The retainer is $12,000 [1]. "}}]})
    return _Resp({"response": " local answer [1] "})


llm.requests.post = fake_post

# ---- local ----
check("local: default model is installed nemotron-3-nano:4b", llm.LOCAL_MODEL == "nemotron-3-nano:4b")
out = llm.local_generate("q")
check("local: goes to the local Ollama endpoint", calls[-1]["url"].startswith("http://localhost:11434"))
check("local: uses the local model", calls[-1]["json"]["model"] == "nemotron-3-nano:4b")
check("local: returns stripped text", out == "local answer [1]")

# ---- cloud without a key: never raises, never calls out ----
n = len(calls)
check("cloud: no key -> empty string (caller refuses)", llm.cloud_generate("q") == "")
check("cloud: no key -> no network call", len(calls) == n)

# ---- cloud with a key ----
os.environ["GROQ_API_KEY"] = "test-key-not-real"
out = llm.cloud_generate("the prompt")
c = calls[-1]
check("cloud: default model is openai/gpt-oss-120b", llm.CLOUD_MODEL == "openai/gpt-oss-120b")
check("cloud: goes to Groq's OpenAI-compatible endpoint",
      c["url"] == "https://api.groq.com/openai/v1/chat/completions")
check("cloud: sends the model and the prompt",
      c["json"]["model"] == "openai/gpt-oss-120b"
      and c["json"]["messages"][-1] == {"role": "user", "content": "the prompt"})
check("cloud: key goes in the Authorization header", c["headers"].get("Authorization") == "Bearer test-key-not-real")
check("cloud: temperature 0", c["json"].get("temperature") == 0)
check("cloud: returns stripped text", out == "The retainer is $12,000 [1].")
check("cloud: never sent to the local Ollama endpoint", "localhost" not in c["url"])

# ---- cloud failure modes: never raise ----
llm.requests.post = lambda *a, **k: _Resp({}, status=500)
check("cloud: HTTP error -> empty string", llm.cloud_generate("q") == "")
llm.requests.post = lambda *a, **k: _Resp({"choices": [{"message": {"content": None}}]})
check("cloud: null content -> empty string", llm.cloud_generate("q") == "")


def boom(*a, **k):
    raise ConnectionError("offline")


llm.requests.post = boom
check("cloud: network down -> empty string", llm.cloud_generate("q") == "")

# ---- overrides still work ----
os.environ["OIL_LOCAL_MODEL"] = "llama3.2:3b"
os.environ["OIL_CLOUD_MODEL"] = "openai/gpt-oss-20b"
llm = importlib.reload(llm)
check("override: OIL_LOCAL_MODEL", llm.LOCAL_MODEL == "llama3.2:3b")
check("override: OIL_CLOUD_MODEL", llm.CLOUD_MODEL == "openai/gpt-oss-20b")
for k in ("OIL_LOCAL_MODEL", "OIL_CLOUD_MODEL", "GROQ_API_KEY"):
    os.environ.pop(k, None)

print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
sys.exit(1 if FAIL else 0)
