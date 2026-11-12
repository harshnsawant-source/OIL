"""Minimal local web UI for OIL. The UI itself runs on 127.0.0.1 only. Point it at a
folder, ask, get a grounded answer with page citations (or an honest "not found").
The answer model is local by default, and in that mode nothing leaves the machine.
OIL_MODEL=cloud sends retrieved passages to a cloud model: demos on non-confidential
data only. The page badge shows which mode is active.
"""

import os

from flask import Flask, request, jsonify

from oil.ingest import load_folder
from oil.index import DocIndex
from oil.answer import answer, format_citations
from oil.llm import local_generate, cloud_generate

app = Flask(__name__)

# Single in-memory index for this session (one user, local).
_state = {"index": None, "folder": None}


def _mode():
    return "cloud" if os.environ.get("OIL_MODEL", "local").lower() == "cloud" else "local"


def _generate():
    return cloud_generate if _mode() == "cloud" else local_generate


BADGES = {
    "local": '<span class="badge">local · nothing leaves this machine</span>',
    "cloud": '<span class="badge warn">cloud · passages are sent to a cloud model · '
             'non-confidential data only</span>',
}


PAGE = """<!doctype html>
<html><head><meta charset="utf-8"><title>OIL — Private Document Q&A</title>
<style>
 body{font-family:system-ui,sans-serif;max-width:760px;margin:40px auto;padding:0 16px;color:#1a1a1a}
 h1{font-size:20px} .muted{color:#666;font-size:13px}
 input,button{font-size:15px;padding:8px} input{width:100%;box-sizing:border-box;margin:6px 0}
 button{cursor:pointer;background:#1a1a1a;color:#fff;border:0;border-radius:6px;padding:9px 16px}
 #answer{white-space:pre-wrap;background:#f6f6f6;border-radius:8px;padding:14px;margin-top:12px}
 .sources{font-size:13px;color:#333;margin-top:8px} .refused{color:#a40000}
 .badge{font-size:12px;color:#0a7d33;border:1px solid #0a7d33;border-radius:4px;padding:2px 6px}
 .badge.warn{color:#a40000;border-color:#a40000}
</style></head><body>
<h1>OIL — Private Document Q&amp;A __BADGE__</h1>
<p class="muted">Answers come only from your documents, cited to the source page. If the
answer isn't in your documents, it says so — it does not guess.</p>

<input id="folder" placeholder="Path to a folder of documents (PDF, Word, Excel, text, images)">
<button onclick="doIndex()">Index folder</button>
<div id="status" class="muted"></div>

<input id="q" placeholder="Ask a question about your documents" onkeydown="if(event.key==='Enter')doAsk()">
<button onclick="doAsk()">Ask</button>
<div id="answer"></div>
<div id="sources" class="sources"></div>

<script>
async function post(url, body){
  const r = await fetch(url,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
  return r.json();
}
async function doIndex(){
  document.getElementById('status').textContent='Indexing…';
  const d = await post('/index',{folder:document.getElementById('folder').value});
  document.getElementById('status').textContent = d.ok ? ('Indexed '+d.indexed+' passages from '+d.folder) : ('Error: '+d.error);
}
async function doAsk(){
  document.getElementById('answer').textContent='Thinking…';
  document.getElementById('sources').textContent='';
  const d = await post('/ask',{question:document.getElementById('q').value});
  const a = document.getElementById('answer');
  if(!d.ok){ a.textContent='Error: '+d.error; return; }
  if(d.refused){ a.innerHTML='<span class="refused">Not found in your documents.</span>'; return; }
  a.textContent = d.answer;
  document.getElementById('sources').textContent = 'Sources: '+d.sources;
}
</script></body></html>"""


@app.get("/")
def home():
    # Read the mode on every request so the badge can never disagree with what /ask does.
    return PAGE.replace("__BADGE__", BADGES[_mode()])


@app.post("/index")
def do_index():
    folder = ((request.json or {}).get("folder") or "").strip()
    if not folder or not os.path.isdir(folder):
        return jsonify({"ok": False, "error": "folder not found"}), 400
    idx = DocIndex()
    stats = idx.build(load_folder(folder))
    _state["index"] = idx
    _state["folder"] = folder
    return jsonify({"ok": True, "indexed": stats["indexed"], "folder": folder})


@app.post("/ask")
def do_ask():
    if _state["index"] is None:
        return jsonify({"ok": False, "error": "index a folder first"}), 400
    question = ((request.json or {}).get("question") or "").strip()
    if not question:
        return jsonify({"ok": False, "error": "empty question"}), 400
    r = answer(question, _state["index"], generate=_generate())
    return jsonify({
        "ok": True,
        "refused": r["refused"],
        "answer": r["answer"],
        "citations": r["citations"],
        "sources": format_citations(r["citations"]),
        "reason": r["reason"],
        "mode": _mode(),
    })


def main():
    app.run(host="127.0.0.1", port=5000, debug=False)


if __name__ == "__main__":
    main()
