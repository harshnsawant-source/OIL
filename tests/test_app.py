import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import oil.app as appmod

PASS = []
FAIL = []


def check(name, cond):
    (PASS if cond else FAIL).append(name)
    print(("PASS" if cond else "FAIL"), "-", name)


# Stub the engine pieces so the endpoints are tested without embeddings/LLM.
class _Idx:
    def build(self, chunks):
        return {"indexed": 3, "skipped": 0}


appmod.load_folder = lambda folder: ["c1", "c2", "c3"]
appmod.DocIndex = _Idx

_canned = {"refused": False, "answer": "The retainer is $12,000 [1].",
           "citations": [{"source": "services_agreement.md", "location": "p1"}],
           "reason": "answered from documents"}
appmod.answer = lambda q, idx, generate=None: _canned

appmod._state["index"] = None  # fresh
client = appmod.app.test_client()

# home page serves
r = client.get("/")
check("ui: home page served", r.status_code == 200 and b"Private Document" in r.data)

# ask before indexing -> 400
r = client.post("/ask", json={"question": "x"})
check("ui: ask before index -> error", r.status_code == 400 and r.get_json()["ok"] is False)

# bad folder -> 400
r = client.post("/index", json={"folder": "/no/such/folder/xyz"})
check("ui: bad folder -> error", r.status_code == 400)

# index a real (temp) folder
d = tempfile.mkdtemp(prefix="oil_ui_")
r = client.post("/index", json={"folder": d})
j = r.get_json()
check("ui: index ok + count", j["ok"] is True and j["indexed"] == 3)

# ask -> grounded answer + page-level sources
r = client.post("/ask", json={"question": "retainer?"})
j = r.get_json()
check("ui: ask returns answer", j["ok"] is True and j["refused"] is False
      and "12,000" in j["answer"])
check("ui: ask returns page-level sources",
      j["sources"] == "services_agreement.md, p1")

# empty question -> 400
r = client.post("/ask", json={"question": "   "})
check("ui: empty question -> error", r.status_code == 400)

# refusal surfaces
appmod.answer = lambda q, idx, generate=None: {
    "refused": True, "answer": "", "citations": [], "reason": "not found"}
r = client.post("/ask", json={"question": "ceo salary?"})
j = r.get_json()
check("ui: refusal surfaced", j["ok"] is True and j["refused"] is True)


print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
sys.exit(1 if FAIL else 0)
