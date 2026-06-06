"""Run the trust engine against the labeled eval set and print the scorecard.

Two objective metrics (no LLM judge):
  citation accuracy   — answerable cases answered, citing the EXPECTED source,
                        with the key fact present.
  refusal correctness — unanswerable cases correctly refused, and answerable
                        cases NOT wrongly refused.

Uses cloud_generate as a stand-in for a capable model run locally on the buyer's
hardware — the corpus is synthetic, so nothing confidential is involved.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "eval"))

from oil import ingest
from oil.index import DocIndex
from oil.answer import answer
from oil.llm import cloud_generate
from cases import CASES


def main():
    idx = DocIndex()
    idx.build(ingest.load_folder(str(ROOT / "eval" / "corpus")))

    cit_ok = cit_tot = 0
    ref_ok = ref_tot = 0
    wrong_refusals = 0

    print("ANSWERABLE:")
    for c in CASES:
        if not c["answerable"]:
            continue
        cit_tot += 1
        r = answer(c["question"], idx, generate=cloud_generate)
        ans = (r["answer"] or "").lower()
        contains = any(s.lower() in ans for s in c["must_contain"])
        cited_ok = c["source"] in r["citations"]
        ok = (not r["refused"]) and cited_ok and contains
        cit_ok += ok
        if r["refused"]:
            wrong_refusals += 1
        flag = "ok " if ok else "XX "
        cite = ",".join(r["citations"]) or ("REFUSED" if r["refused"] else "-")
        print(f"  {flag} cite={cite:24} fact={'Y' if contains else 'N'}  Q: {c['question']}")

    print("\nUNANSWERABLE (must refuse):")
    for c in CASES:
        if c["answerable"]:
            continue
        ref_tot += 1
        r = answer(c["question"], idx, generate=cloud_generate)
        ref_ok += r["refused"]
        flag = "ok " if r["refused"] else "XX "
        print(f"  {flag} {'refused' if r['refused'] else 'ANSWERED:'+r['citations'][0] if r['citations'] else 'ANSWERED'}  Q: {c['question']}")

    print("\n=== SCORECARD ===")
    print(f"  citation accuracy   : {cit_ok}/{cit_tot}")
    print(f"  refusal correctness : {ref_ok}/{ref_tot} unanswerable refused; "
          f"{wrong_refusals} answerable wrongly refused")


if __name__ == "__main__":
    main()
