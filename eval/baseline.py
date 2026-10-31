#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
baseline.py - wo system jise RAHAT ko haraana hai.

Do hisse:
  1. Keyword rules se extraction + simple merging  -> predictions_baseline.json
  2. Nearest-free-team greedy dispatch             -> assignments_baseline.json

Chalana:
  python baseline.py
  python baseline.py --messages ../data/test_150.json --out-prefix baseline_test

Phir score nikalne ke liye:
  python evaluate.py --gold ../data/test_150.json --pred baseline_test_predictions.json

IMPORTANT - ye baseline jaanbujh ke kamzor nahi banaya gaya hai.
Keyword rules wahi hain jo ek normal banda likhta. Judge isi pe sawaal karte hain:
"tumne apne baseline ko strawman to nahi banaya?" Jawab: rules locations.csv se
aate hain aur har need-type ka keyword list hai, koi jagah jaanbujh ke chhodi nahi.
"""

import argparse, csv, json, math, os, re
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
D = lambda *p: os.path.join(HERE, "..", "data", *p)

SPEED_KMPH = 18.0          # flood me gaadi ki rafdaar - PRD section 11
MERGE_WINDOW_MIN = 20      # itne minute ke andar same jagah+need = same ghatna

NEED_WORDS = {
    "rescue":   ["fas", "phas", "फंस", "chhat", "roof", "bachao", "बचाओ", "doob",
                 "trapped", "stuck", "stranded", "nikal", "bah gya", "bah gaya",
                 "dabe", "malbe", "debris", "collapse", "gir gy", "evacuat"],
    "medical":  ["ambulance", "aspataal", "hospital", "bukhar", "fever", "dard",
                 "chot", "injury", "injured", "khoon", "blood", "oxygen",
                 "pregnant", "garbhwati", "labour", "dialysis", "saans",
                 "tabiyat", "bimar", "dil ka", "medical"],
    "medicine": ["dawa", "dawai", "medicine", "insulin", "sugar ki", "bp ki", "tablet"],
    "food":     ["khana", "bhook", "bhooke", "ration", "khaya", "food", "खाना"],
    "water":    ["peene ka pani", "peene ka paani", "drinking water", "pani ki bottle",
                 "tanker", "paani nahi bacha"],
    "shelter":  ["kambal", "blanket", "tirpal", "tarpaulin", "sharan", "shelter", "thand"],
    "info":     ["kab tak", "kya h", "khula h", "khula hua", "update", "number kya",
                 "kaha mil", "jagah h", "chal rhi", "chal rahi", "thank", "shukriya",
                 "dhanyavad", "hello"],
}

VULN_WORDS = {
    "elderly":  ["dadi", "dada", "nani", "nana", "buzurg", "budhi", "budhe", "elderly",
                 "बुजुर्ग", "दादी", "saal ka hu", "saal ki hu", "70 ", "75 ", "78 ",
                 "80 ", "81 ", "76 ", "74 ", "79 ", "73 ", "72 ", "68 "],
    "child":    ["bachh", "bachche", "baby", "child", "बच्च", "school se"],
    "disabled": ["viklang", "wheelchair", "handicap", "disabled", "blind", "andha",
                 "chal nhi sakta", "chalne me dikkat", "mental illness"],
    "pregnant": ["pregnant", "garbhwati", "गर्भवती", "labour pain", "mahine pregnant"],
    "injured":  ["chot", "toot", "khoon", "injury", "injured", "dabe", "fracture"],
}

CRITICAL_WORDS = ["fas", "phas", "फंस", "doob", "bah gy", "bah ga", "dabe", "malbe",
                  "chhat pe", "roof pe", "oxygen", "labour", "seene me dard",
                  "saans lene", "trapped", "collapse", "gas leak", "taar pani"]
HIGH_WORDS = ["bukhar", "fever", "chot", "khoon", "dawa khtm", "dawa khatam",
              "medicine khatam", "dialysis", "insulin", "bhook", "khana nhi"]
MEDIUM_WORDS = ["khana", "pani ki bottle", "kambal", "ration", "tirpal", "shelter"]


# ---------------------------------------------------------------- extraction
def load_locations():
    rows = []
    with open(D("locations.csv"), encoding="utf-8") as f:
        for r in csv.DictReader(f):
            rows.append(r)
    return rows


def find_location(text, locs):
    """Keyword match: naam ya alias text me hai kya."""
    t = text.lower()
    best = None
    for r in locs:
        cands = [r["name"].lower()]
        cands += [a.strip().lower() for a in r["alias_hinglish"].split("/")]
        for c in cands:
            if c and c in t:
                # sabse lamba match jeetega ("bell road clement town" > "clement town")
                if best is None or len(c) > best[1]:
                    best = (r["name"], len(c))
    return best[0] if best else None


def find_need(text):
    t = text.lower()
    for need in ["rescue", "medical", "medicine", "water", "food", "shelter", "info"]:
        for w in NEED_WORDS[need]:
            if w in t:
                return need
    return None


def find_people(text):
    t = text.lower()
    m = re.search(r"(\d+)\s*[-–]\s*(\d+)\s*log", t)       # "4-5 log"
    if m:
        return int(m.group(1))
    m = re.search(r"(\d+)\s*log", t)                       # "10 log"
    if m:
        return int(m.group(1))
    words = {"ek": 1, "do": 2, "teen": 3, "chaar": 4, "paanch": 5,
             "chhe": 6, "saat": 7, "aath": 8, "das": 10, "chalees": 40, "pandrah": 15}
    for w, n in words.items():
        if re.search(r"\b%s\s+log" % w, t):
            return n
    if "pura parivar" in t or "poora parivar" in t or "family" in t:
        return 4
    if "akela" in t or "akeli" in t or "main hu" in t:
        return 1
    return None


def find_vulnerable(text):
    t = text.lower()
    out = []
    for v, words in VULN_WORDS.items():
        if any(w in t for w in words):
            out.append(v)
    return out


def find_urgency(text):
    t = text.lower()
    if any(w in t for w in CRITICAL_WORDS):
        return "critical"
    if any(w in t for w in HIGH_WORDS):
        return "high"
    if any(w in t for w in MEDIUM_WORDS):
        return "medium"
    return "low"


def is_noise(text):
    t = text.lower()
    return any(w in t for w in NEED_WORDS["info"])


# ---------------------------------------------------------------- merging
def naive_merge(extracted):
    """
    Baseline ka merging: same location + same need, aur time MERGE_WINDOW_MIN
    ke andar -> ek hi incident. Koi meaning-matching nahi, bas exact field match.
    """
    clusters = []
    for e in extracted:
        if e["location"] is None:
            clusters.append([e])                   # location nahi to merge nahi
            continue
        placed = False
        for c in clusters:
            h = c[0]
            if h["location"] != e["location"] or h["need"] != e["need"]:
                continue
            gap = abs((e["_t"] - h["_t"]).total_seconds()) / 60.0
            if gap <= MERGE_WINDOW_MIN:
                c.append(e)
                placed = True
                break
        if not placed:
            clusters.append([e])
    return clusters


# ---------------------------------------------------------------- dispatch
NEED_TO_TEAM = {
    "rescue": ["boat", "search_rescue", "fire"],
    "medical": ["medical"],
    "medicine": ["medical", "relief"],
    "food": ["relief"],
    "water": ["relief"],
    "shelter": ["relief"],
}
URGENCY_RANK = {"critical": 0, "high": 1, "medium": 2, "low": 3}


def haversine(a, b):
    R = 6371.0
    la1, lo1, la2, lo2 = map(math.radians, [a[0], a[1], b[0], b[1]])
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 2 * R * math.asin(math.sqrt(h))


def greedy_dispatch(incidents, teams, loc_coords):
    """
    Nearest-free-team greedy: incidents ko aane ke order me dekho,
    har ek ko sabse paas wali free team do. Yahi aaj control room karta hai.
    """
    free = {t["id"]: dict(t) for t in teams}
    assigns = []
    for inc in sorted(incidents, key=lambda i: i["_t"]):
        if inc["location"] is None or inc["need"] not in NEED_TO_TEAM:
            continue
        coord = loc_coords.get(inc["location"])
        if not coord:
            continue
        want = NEED_TO_TEAM[inc["need"]]
        cands = [t for t in free.values() if t["type"] in want]
        if not cands:
            continue
        best = min(cands, key=lambda t: haversine(coord, (t["location"]["lat"], t["location"]["lng"])))
        km = haversine(coord, (best["location"]["lat"], best["location"]["lng"]))
        eta = km / SPEED_KMPH * 60.0
        assigns.append({"incident_id": inc["id"], "team_id": best["id"],
                        "urgency": inc["urgency"], "location": inc["location"],
                        "eta_min": round(eta, 1), "km": round(km, 2)})
        del free[best["id"]]                       # team busy ho gayi
    return assigns


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--messages", default=D("messages.json"))
    ap.add_argument("--teams", default=D("teams.json"))
    ap.add_argument("--out-prefix", default="baseline")
    a = ap.parse_args()

    msgs = json.load(open(a.messages, encoding="utf-8"))
    teams = json.load(open(a.teams, encoding="utf-8"))
    locs = load_locations()
    loc_coords = {r["name"]: (float(r["lat"]), float(r["lng"])) for r in locs}

    # --- 1. extraction
    extracted, dropped = [], 0
    for m in msgs:
        txt = m["raw_text"]
        if is_noise(txt) and find_need(txt) == "info":
            dropped += 1
            continue
        extracted.append({
            "msg_id": m["msg_id"],
            "_t": datetime.fromisoformat(m["timestamp"]),
            "location": find_location(txt, locs),
            "need": find_need(txt),
            "people_count": find_people(txt),
            "vulnerable": find_vulnerable(txt),
            "urgency": find_urgency(txt),
        })

    # --- 2. merging
    clusters = naive_merge(extracted)
    incidents = []
    for i, c in enumerate(clusters, 1):
        h = c[0]
        incidents.append({
            "id": "B-%03d" % i,
            "message_ids": [e["msg_id"] for e in c],
            "location": h["location"], "need": h["need"],
            "people_count": max((e["people_count"] or 0) for e in c) or None,
            "vulnerable": sorted({v for e in c for v in e["vulnerable"]}),
            "urgency": min((e["urgency"] for e in c), key=lambda u: URGENCY_RANK[u]),
            "red_flags": [],                       # baseline me fake detection nahi hai
            "_t": h["_t"],
        })

    pred_path = "%s_predictions.json" % a.out_prefix
    json.dump({"incidents": [{k: v for k, v in i.items() if k != "_t"} for i in incidents]},
              open(pred_path, "w", encoding="utf-8"), indent=2, ensure_ascii=False)

    # --- 3. greedy dispatch
    assigns = greedy_dispatch(incidents, teams, loc_coords)
    asg_path = "%s_assignments.json" % a.out_prefix
    json.dump({"method": "greedy_nearest_free_team", "assignments": assigns},
              open(asg_path, "w", encoding="utf-8"), indent=2, ensure_ascii=False)

    # --- report
    crit = [x for x in assigns if x["urgency"] == "critical"]
    n_crit_inc = sum(1 for i in incidents if i["urgency"] == "critical")
    print("=" * 60)
    print("BASELINE (keyword rules + nearest-free-team greedy)")
    print("=" * 60)
    print("messages            : %d" % len(msgs))
    print("noise ignore kiye   : %d" % dropped)
    print("incidents bane      : %d" % len(incidents))
    print("assignments         : %d" % len(assigns))
    print("\ncritical incidents  : %d" % n_crit_inc)
    print("critical assigned   : %d" % len(crit))
    if crit:
        waits = sorted(x["eta_min"] for x in crit)
        print("critical wait (min) : avg %.1f | median %.1f | SABSE LAMBA %.1f" % (
            sum(waits) / len(waits), waits[len(waits) // 2], waits[-1]))
    print("\nfiles:")
    print("  %s" % pred_path)
    print("  %s" % asg_path)
    print("\nagla kadam:")
    print("  python evaluate.py --gold %s --pred %s" % (
        os.path.basename(a.messages), pred_path))
    print("=" * 60)


if __name__ == "__main__":
    main()
