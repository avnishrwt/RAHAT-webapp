#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
rag_eval.py - RAG checklist ko naapta hai.

Chalana:
  python rag_eval.py --no-llm                 # sirf retrieval naapo (LLM ke bina)
  python rag_eval.py                          # poora, Gemini ke sath
  python rag_eval.py --threshold 2.0          # threshold tune karne ke liye

Teen cheez naapta hai (brief ka requirement):

1. GROUNDING RATE - LLM ne jitne step likhe, unme se kitne sach me apne
   cited passage se aaye. Jo nahi aaye wo drop ho gaye. Ye RAG ka sabse
   important number hai: 1.00 ka matlab LLM ne apne se kuch nahi joda.

2. NOT_IN_SOP ACCURACY - jab SOP me jawab hai hi nahi, tab system "escalate
   to officer" bolta hai ya jhooti checklist bana deta hai?
   Jhooti checklist banana sabse khatarnak failure hai - rescue team galat
   step follow karegi.

3. COVERAGE - kis need type pe SOP silent hai. Isse pata chalta hai ki
   kaunsa document aur chahiye.
"""

import argparse, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from rag_checklist import BM25, make_checklist, SCORE_THRESHOLD   # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--chunks", default=os.path.join(HERE, "chunks.json"))
    ap.add_argument("--incidents", default=os.path.join(HERE, "rag_test_incidents.json"))
    ap.add_argument("--no-llm", action="store_true")
    ap.add_argument("--threshold", type=float, default=SCORE_THRESHOLD)
    ap.add_argument("--out", help="poore results json me")
    a = ap.parse_args()

    if not os.path.exists(a.chunks):
        sys.exit("chunks.json nahi mila. Pehle: python rag_build.py")

    chunks = json.load(open(a.chunks, encoding="utf-8"))
    tests = json.load(open(a.incidents, encoding="utf-8"))
    bm25 = BM25(chunks)

    print("=" * 66)
    print("RAG EVALUATION")
    print("chunks: %d   incidents: %d   threshold: %.2f   LLM: %s" % (
        len(chunks), len(tests), a.threshold, "no" if a.no_llm else "yes"))
    print("=" * 66)

    results = []
    for t in tests:
        r = make_checklist(t, bm25, use_llm=not a.no_llm, threshold=a.threshold)
        r["expect_in_sop"] = t["expect_in_sop"]
        r["note"] = t.get("note", "")
        results.append(r)

    # --- 1. grounding
    kept = sum(len(r["items"]) for r in results)
    dropped = sum(len(r.get("dropped_ungrounded", [])) for r in results)
    produced = kept + dropped
    grounding = kept / produced if produced else 1.0

    # --- 2. NOT_IN_SOP accuracy
    tp = tn = fp = fn = 0
    wrong = []
    for r in results:
        said_not = (r["status"] == "NOT_IN_SOP")
        should_not = not r["expect_in_sop"]
        if should_not and said_not:
            tn += 1                                   # sahi escalate kiya
        elif should_not and not said_not:
            fp += 1                                   # JHOOTI CHECKLIST - khatarnak
            wrong.append(("jhooti checklist bani", r))
        elif not should_not and said_not:
            fn += 1                                   # tha SOP me, par escalate kar diya
            wrong.append(("bina zaroorat escalate", r))
        else:
            tp += 1

    acc = (tp + tn) / len(results) if results else 0.0

    print("\n--- 1. GROUNDING " + "-" * 47)
    if a.no_llm:
        print("(LLM off hai - grounding ka matlab tabhi hai jab LLM chale)")
    print("LLM ne step likhe    : %d" % produced)
    print("passage se grounded  : %d" % kept)
    print("DROP kiye (ungrounded): %d" % dropped)
    print("GROUNDING RATE       : %.3f" % grounding)
    print("  1.00 = LLM ne apne se ek bhi step nahi joda")

    print("\n--- 2. NOT_IN_SOP " + "-" * 46)
    print("sahi checklist bani       : %d" % tp)
    print("sahi escalate kiya        : %d" % tn)
    print("JHOOTI CHECKLIST          : %d   <- sabse khatarnak" % fp)
    print("bina zaroorat escalate    : %d" % fn)
    print("accuracy                  : %.3f" % acc)

    if wrong:
        print("\n  galtiyan:")
        for why, r in wrong[:8]:
            print("    %-6s %-26s %s" % (r["incident_id"], why, r["note"][:34]))

    # --- 3. coverage
    print("\n--- 3. COVERAGE (kis need pe SOP chup hai) " + "-" * 21)
    by_need = {}
    for r, t in zip(results, tests):
        n = t["need"]
        d = by_need.setdefault(n, [0, 0])
        d[0] += 1
        if r["status"] != "NOT_IN_SOP":
            d[1] += 1
    for n, (tot, ok) in sorted(by_need.items()):
        bar = "#" * int(ok / tot * 20) + "." * (20 - int(ok / tot * 20))
        print("  %-10s %d/%d  %s" % (n, ok, tot, bar))

    print("\n" + "=" * 66)
    print("PITCH ME YE JAATA HAI:")
    print("  grounding rate     : %.3f" % grounding)
    print("  NOT_IN_SOP accuracy: %.3f" % acc)
    print("  jhooti checklist   : %d / %d" % (fp, len(results)))
    print("=" * 66)
    print("\nAgar koi need type 0/N dikha raha hai, uska SOP document missing hai.")
    print("Pitch me ye honestly bolna - ye limitation hai, failure nahi.")

    if a.out:
        json.dump({"grounding_rate": grounding, "not_in_sop_accuracy": acc,
                   "false_checklists": fp, "results": results},
                  open(a.out, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
        print("\nsaved -> %s" % a.out)


if __name__ == "__main__":
    main()
