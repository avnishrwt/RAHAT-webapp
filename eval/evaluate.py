#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
evaluate.py - RAHAT ka output labels se compare karta hai aur asli numbers deta hai.

Chalana:
  python evaluate.py --gold ../data/test_150.json --pred predictions.json
  python evaluate.py --gold ../data/dev_50.json  --pred predictions.json --verbose

predictions.json ka format (Mayank/Avnish ko YE banana hai):
{
  "incidents": [
    {
      "id": "P-001",
      "message_ids": ["MSG-004", "MSG-071", "MSG-100"],
      "location": "Bell Road, Clement Town",
      "need": "rescue",
      "people_count": 4,
      "vulnerable": ["child"],
      "urgency": "critical",
      "red_flags": []
    }
  ]
}

Note: pred incident ki id kuch bhi ho sakti hai. Hum sirf dekhte hain ki
kaunse messages ek saath group hue - gold id se match karne ki zaroorat nahi.
"""

import argparse, json, sys
from collections import defaultdict
from itertools import combinations

FIELDS = ["location", "need", "people_count", "vulnerable", "urgency"]


# ---------------------------------------------------------------- helpers
def norm(field, v):
    """Compare karne se pehle value ko ek jaisa banao."""
    if v is None or v == "":
        return None
    if field == "vulnerable":
        if not v:
            return None                      # khali list = kuch nahi
        return tuple(sorted(str(x).strip().lower() for x in v))
    if field == "people_count":
        try:
            return int(v)
        except (TypeError, ValueError):
            return None
    return str(v).strip().lower()


def msg_to_pred(preds):
    """message_id -> uska predicted incident."""
    out = {}
    for inc in preds.get("incidents", []):
        for mid in inc.get("message_ids", []):
            out[mid] = inc
    return out


# ---------------------------------------------------------------- field F1
def field_scores(gold, m2p, verbose=False):
    """
    Har field ke liye precision / recall / F1.
      precision = sahi / jitne predict kiye (non-null)
      recall    = sahi / jitne gold me the (non-null)
    Noise messages (true_incident_id null) yahan nahi gine jate.
    """
    stats = {f: {"tp": 0, "pred": 0, "gold": 0} for f in FIELDS}
    mistakes = defaultdict(list)

    for g in gold:
        if g["true_incident_id"] is None:
            continue                               # noise alag se dekhenge
        p = m2p.get(g["msg_id"])
        for f in FIELDS:
            gv = norm(f, g.get(f))
            pv = norm(f, p.get(f)) if p else None
            if gv is not None:
                stats[f]["gold"] += 1
            if pv is not None:
                stats[f]["pred"] += 1
            if gv is not None and gv == pv:
                stats[f]["tp"] += 1
            elif gv != pv and verbose:
                mistakes[f].append((g["msg_id"], gv, pv, g["raw_text"][:45]))

    rows = {}
    for f, s in stats.items():
        p = s["tp"] / s["pred"] if s["pred"] else 0.0
        r = s["tp"] / s["gold"] if s["gold"] else 0.0
        f1 = 2 * p * r / (p + r) if (p + r) else 0.0
        rows[f] = {"precision": p, "recall": r, "f1": f1, **s}
    return rows, mistakes


# ---------------------------------------------------------------- merging
def merge_scores(gold, m2p, near_miss_pairs):
    """
    Pairwise merging. Har do messages ka joda dekhte hain:
      TP = gold me same incident, pred me bhi same      (sahi joda)
      FP = gold me alag, pred me same                   (GALAT JODA - false merge)
      FN = gold me same, pred me alag                   (jodna reh gaya)
    """
    rel = [g for g in gold if g["true_incident_id"] is not None]
    tp = fp = fn = 0
    false_merges = []
    near_miss_fp = 0

    for a, b in combinations(rel, 2):
        same_gold = a["true_incident_id"] == b["true_incident_id"]
        pa, pb = m2p.get(a["msg_id"]), m2p.get(b["msg_id"])
        same_pred = pa is not None and pb is not None and id(pa) == id(pb)

        if same_gold and same_pred:
            tp += 1
        elif same_gold and not same_pred:
            fn += 1
        elif not same_gold and same_pred:
            fp += 1
            pair = frozenset((a["true_incident_id"], b["true_incident_id"]))
            false_merges.append((a["msg_id"], b["msg_id"],
                                 a["true_incident_id"], b["true_incident_id"]))
            if pair in near_miss_pairs:
                near_miss_fp += 1

    prec = tp / (tp + fp) if (tp + fp) else 0.0
    rec = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
    fmr = fp / (tp + fp) if (tp + fp) else 0.0      # jode hue pairs me se kitne galat
    return {"tp": tp, "fp": fp, "fn": fn, "precision": prec, "recall": rec,
            "f1": f1, "false_merge_rate": fmr, "near_miss_fp": near_miss_fp,
            "examples": false_merges[:5]}


# ---------------------------------------------------------------- fakes + noise
def fake_scores(gold, m2p):
    """Fake pakda ya nahi - red_flags khali nahi hai to pakda maana."""
    tp = fn = fp = tn = 0
    missed = []
    for g in gold:
        p = m2p.get(g["msg_id"])
        flagged = bool(p.get("red_flags")) if p else False
        if g["is_fake"] and flagged:
            tp += 1
        elif g["is_fake"] and not flagged:
            fn += 1
            missed.append((g["msg_id"], g["raw_text"][:45]))
        elif not g["is_fake"] and flagged:
            fp += 1
        else:
            tn += 1
    catch = tp / (tp + fn) if (tp + fn) else 0.0
    false_alarm = fp / (fp + tn) if (fp + tn) else 0.0
    return {"caught": tp, "missed": fn, "false_alarm": fp,
            "catch_rate": catch, "false_alarm_rate": false_alarm,
            "missed_examples": missed[:5]}


def noise_scores(gold, m2p):
    """Noise message incident nahi banna chahiye."""
    total = wrong = 0
    examples = []
    for g in gold:
        if g["true_incident_id"] is not None:
            continue
        total += 1
        if g["msg_id"] in m2p:
            wrong += 1
            examples.append((g["msg_id"], g["raw_text"][:45]))
    return {"total": total, "became_incident": wrong,
            "correctly_ignored": total - wrong,
            "examples": examples[:5]}


def lone_victim_scores(gold, m2p):
    """
    Lone victim = ek hi message wala incident, fake nahi.
    Check: system ne inko nikala bhi ya chhod diya?
    """
    counts = defaultdict(int)
    for g in gold:
        if g["true_incident_id"] and not g["is_fake"]:
            counts[g["true_incident_id"]] += 1
    lone = [g for g in gold
            if g["true_incident_id"] and not g["is_fake"]
            and counts[g["true_incident_id"]] == 1]
    found = sum(1 for g in lone if g["msg_id"] in m2p)
    crit = [g for g in lone if g["urgency"] == "critical"]
    crit_found = sum(1 for g in crit if g["msg_id"] in m2p)
    return {"total": len(lone), "extracted": found,
            "recall": found / len(lone) if lone else 0.0,
            "critical_total": len(crit), "critical_extracted": crit_found}


# ---------------------------------------------------------------- report
def bar(x, width=24):
    n = int(round(x * width))
    return "#" * n + "." * (width - n)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gold", required=True)
    ap.add_argument("--pred", required=True)
    ap.add_argument("--verbose", action="store_true", help="galtiyon ki list dikhao")
    ap.add_argument("--json-out", help="result ek json file me likho")
    a = ap.parse_args()

    gold = json.load(open(a.gold, encoding="utf-8"))
    preds = json.load(open(a.pred, encoding="utf-8"))
    m2p = msg_to_pred(preds)

    # 6 near-miss pairs - README section 4(a)
    near_miss = {frozenset(("INC-%02d" % i, "INC-%02d" % (i + 1)))
                 for i in range(1, 12, 2)}

    fields, mistakes = field_scores(gold, m2p, a.verbose)
    merge = merge_scores(gold, m2p, near_miss)
    fakes = fake_scores(gold, m2p)
    noise = noise_scores(gold, m2p)
    lone = lone_victim_scores(gold, m2p)

    covered = sum(1 for g in gold if g["msg_id"] in m2p)

    print("=" * 66)
    print("RAHAT EVALUATION   gold=%s (%d messages)" % (a.gold.split("/")[-1], len(gold)))
    print("=" * 66)
    print("\nMessages jo system ne process kiye: %d / %d" % (covered, len(gold)))

    print("\n--- 1. EXTRACTION (field-level) " + "-" * 32)
    print("%-14s %8s %8s %8s   %s" % ("field", "prec", "recall", "F1", "gold n"))
    macro = 0.0
    for f in FIELDS:
        r = fields[f]
        macro += r["f1"]
        print("%-14s %8.3f %8.3f %8.3f   %4d  %s" % (
            f, r["precision"], r["recall"], r["f1"], r["gold"], bar(r["f1"])))
    macro /= len(FIELDS)
    print("%-14s %26.3f" % ("MACRO F1", macro))

    print("\n--- 2. MERGING (duplicate clusters) " + "-" * 28)
    print("pairwise precision : %.3f" % merge["precision"])
    print("pairwise recall    : %.3f" % merge["recall"])
    print("pairwise F1        : %.3f" % merge["f1"])
    print("FALSE-MERGE RATE   : %.3f   <- do alag ghatna galti se jud gayi" % merge["false_merge_rate"])
    print("  near-miss pairs me false merge: %d" % merge["near_miss_fp"])
    print("  (TP %d / FP %d / FN %d)" % (merge["tp"], merge["fp"], merge["fn"]))
    if merge["examples"]:
        print("  galat jude hue (pehle 5):")
        for ma, mb, ia, ib in merge["examples"]:
            print("    %s + %s  (%s vs %s)" % (ma, mb, ia, ib))

    print("\n--- 3. FAKES " + "-" * 51)
    print("catch rate      : %.3f  (%d/%d pakde)" % (
        fakes["catch_rate"], fakes["caught"], fakes["caught"] + fakes["missed"]))
    print("false alarm rate: %.3f  (%d asli messages galti se flag hue)" % (
        fakes["false_alarm_rate"], fakes["false_alarm"]))
    if fakes["missed_examples"]:
        print("  nahi pakde (pehle 5):")
        for mid, txt in fakes["missed_examples"]:
            print("    %s  %s" % (mid, txt))

    print("\n--- 4. LONE VICTIMS (RAHAT ka main claim) " + "-" * 22)
    print("lone incidents nikale: %d / %d  (recall %.3f)" % (
        lone["extracted"], lone["total"], lone["recall"]))
    print("critical lone victims: %d / %d" % (
        lone["critical_extracted"], lone["critical_total"]))
    print("NOTE: fake catch rate upar hai. Dono saath dekhna - agar fake")
    print("      pakadne me lone victim recall gir raha hai, to trade-off hai.")

    print("\n--- 5. NOISE " + "-" * 51)
    print("noise messages      : %d" % noise["total"])
    print("galti se incident bane: %d" % noise["became_incident"])
    print("sahi ignore hue     : %d" % noise["correctly_ignored"])
    if noise["examples"]:
        for mid, txt in noise["examples"]:
            print("    %s  %s" % (mid, txt))

    if a.verbose and mistakes:
        print("\n--- EXTRACTION GALTIYAN " + "-" * 40)
        for f in FIELDS:
            if not mistakes[f]:
                continue
            print("\n[%s]" % f)
            for mid, gv, pv, txt in mistakes[f][:8]:
                print("  %s  gold=%-28s pred=%-28s" % (mid, gv, pv))
                print("        %s" % txt)

    print("\n" + "=" * 66)
    print("PITCH ME YE TEEN NUMBER JAATE HAIN:")
    print("  extraction macro F1 : %.3f" % macro)
    print("  merge F1            : %.3f" % merge["f1"])
    print("  false-merge rate    : %.3f" % merge["false_merge_rate"])
    print("=" * 66)

    if a.json_out:
        json.dump({"fields": fields, "merge": merge, "fakes": fakes,
                   "noise": noise, "lone": lone, "macro_f1": macro},
                  open(a.json_out, "w", encoding="utf-8"),
                  indent=2, ensure_ascii=False, default=str)
        print("\nsaved -> %s" % a.json_out)


if __name__ == "__main__":
    main()
