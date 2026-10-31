#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
rag_checklist.py - incident ke liye SOP-grounded checklist banata hai.

Chalana:
  python rag_checklist.py --demo                      # sample incidents pe
  python rag_checklist.py --incident incident.json    # ek incident file se
  python rag_checklist.py --demo --no-llm             # sirf retrieval dekho

Teen hisse:
  1. RETRIEVE - incident fields se query banao, BM25 se top-k chunks nikalo
  2. GUARD    - best score threshold se neeche -> NOT_IN_SOP, escalate to officer
  3. GENERATE - LLM checklist likhe, har item pe passage id; bina valid id
                wala item DROP kar do

Teesra step sabse important hai. LLM apne aap se step jod deta hai jo SOP me
likha hi nahi - us item ka passage id invalid hoga, aur hum use hata denge.
Brief me yahi failure mode likha hai.

BM25 pure python hai - koi pip install nahi chahiye. Embeddings optional hai
(sentence-transformers mila to use ho jayega, warna BM25 se hi kaam chalega).
"""

import argparse, json, math, os, re, sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
CHUNKS = os.path.join(HERE, "chunks.json")

SCORE_THRESHOLD = 1.5     # isse neeche -> NOT_IN_SOP (tune karna padega)
TOP_K = 5

# Ye sections kisi bhi rescue/relief checklist me nahi aane chahiye.
# IMD ki flood PDF ka aadha hissa kheti ka hai; bina is filter ke
# "apply N-fertilizer to crops" buzurg ke rescue pe top result aa jata hai.
DROP_SECTIONS = ("agriculture",)

# Ye needs khud me khaas hain - SOP me inka naam seedha milta hai.
# "rescue" aur "medical" itne generic hain ki kisi bhi line se match ho jate hain.
CONCRETE_NEEDS = ("food", "water", "shelter", "medicine")

STOP = set("""a an the is are was were be been being of to in on at for with by from
and or not no do dont don't as it its this that these those your you we they if when
should must may can will shall into over under after before during""".split())


# ------------------------------------------------------------------ BM25
def tok(s):
    return [w for w in re.findall(r"[a-z]+", s.lower()) if w not in STOP and len(w) > 2]


class BM25:
    """Classic BM25. Keyword matching - meaning nahi samajhta, par fast aur
    koi install nahi chahiye. Hinglish query ke liye English keywords nikalte hain."""

    def __init__(self, docs, k1=1.5, b=0.75):
        self.docs = docs
        self.k1, self.b = k1, b
        self.toks = [tok(d["text"]) for d in docs]
        self.len = [len(t) for t in self.toks]
        self.avg = sum(self.len) / len(self.len) if self.len else 0
        self.df = Counter()
        for t in self.toks:
            self.df.update(set(t))
        self.N = len(docs)

    def idf(self, w):
        n = self.df.get(w, 0)
        return math.log(1 + (self.N - n + 0.5) / (n + 0.5))

    def score(self, query, i):
        s, tf = 0.0, Counter(self.toks[i])
        for w in tok(query):
            f = tf.get(w, 0)
            if not f:
                continue
            denom = f + self.k1 * (1 - self.b + self.b * self.len[i] / (self.avg or 1))
            s += self.idf(w) * f * (self.k1 + 1) / denom
        return s

    def search(self, query, k=TOP_K, hazard=None, drop_sections=()):
        idx = list(range(self.N))
        # section filter: agriculture ki salah kabhi rescue checklist me nahi aani chahiye.
        # Bina iske "apply N-fertilizer to crops" top result aa jata hai buzurg ke rescue pe.
        if drop_sections:
            keep = [i for i in idx if self.docs[i]["section"] not in drop_sections]
            if keep:
                idx = keep
        if hazard:
            # hazard filter: fire ka SOP flood incident pe nahi aana chahiye
            keep = [i for i in idx
                    if hazard in self.docs[i]["hazards"] or "general" in self.docs[i]["hazards"]]
            if keep:
                idx = keep
        scored = sorted(((self.score(query, i), i) for i in idx), reverse=True)
        return [(s, self.docs[i]) for s, i in scored[:k] if s > 0]


# ------------------------------------------------------------------ query
HAZARD_OF_NEED = {"rescue": "flood", "medical": "general", "medicine": "general",
                  "food": "general", "water": "general", "shelter": "shelter"}


def build_query(inc):
    """
    Incident ke fields se search query. PRD section 6 ka format:
    "rescue elderly person from rooftop, water 5 ft, boat team"
    """
    # Generic padding JAANBUJH KE nahi daala. Pehle query me har incident ke liye
    # "evacuate people from flood water" jud jata tha, jisse dialysis wala case bhi
    # flood passages se match kar jata tha aur NOT_IN_SOP kabhi fire nahi hota tha.
    # Ab query sirf incident ki KHAAS cheezon se banti hai.
    bits = []
    if inc.get("need"):
        bits.append({"rescue": "evacuate shelter",
                     "medical": "first aid injury treatment",
                     "medicine": "medicine supply",
                     "food": "food",
                     "water": "drinking water",
                     "shelter": "shelter"}.get(inc["need"], inc["need"]))
    for v in inc.get("vulnerable", []):
        bits.append({"elderly": "elderly old person",
                     "child": "children",
                     "disabled": "disabled person unable to move",
                     "pregnant": "pregnant woman",
                     "injured": "injured bleeding"}.get(v, v))
    if inc.get("hazard"):
        bits.append(inc["hazard"])
    if inc.get("people_count") and inc["people_count"] > 5:
        bits.append("group evacuation")
    return " ".join(bits) or "flood safety"


def hazard_for(inc):
    h = (inc.get("hazard") or "").lower()
    if "fire" in h or "gas" in h:
        return "fire"
    if "collapse" in h or "debris" in h or "wall" in h:
        return "collapse"
    if "landslide" in h:
        return "landslide"
    return HAZARD_OF_NEED.get(inc.get("need"), "flood")


# ------------------------------------------------------------------ LLM
PROMPT = """You are writing a field checklist for a disaster rescue team in India.

Use ONLY the numbered passages below. Do not add any step from your own knowledge,
even if it seems obviously correct and important.

Incident:
{incident}

Passages:
{passages}

Return ONLY a JSON array, no markdown fences, no preamble. Each element:
  {{"step": "<short imperative instruction for the rescue team>",
    "passage_id": "<the id of the passage this came from>"}}

Rules:
- Maximum 6 steps.
- Every step must be traceable to one passage. If you cannot trace it, leave it out.
- Keep each step under 18 words.
- If no passage is relevant, return []
"""


def call_gemini(prompt, model="gemini-2.0-flash"):
    """Gemini call. API key .env ya environment se - kabhi code me nahi."""
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        raise RuntimeError("GEMINI_API_KEY set nahi hai (env ya .env me daalo)")
    import json as _json
    from urllib import request as _rq
    url = ("https://generativelanguage.googleapis.com/v1beta/models/"
           "%s:generateContent?key=%s" % (model, key))
    body = {"contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.1}}
    req = _rq.Request(url, data=_json.dumps(body).encode(),
                      headers={"Content-Type": "application/json"}, method="POST")
    with _rq.urlopen(req, timeout=30) as r:
        data = _json.loads(r.read())
    return data["candidates"][0]["content"]["parts"][0]["text"]


def parse_items(raw):
    txt = re.sub(r"^```(?:json)?|```$", "", raw.strip(), flags=re.M).strip()
    try:
        out = json.loads(txt)
        return out if isinstance(out, list) else []
    except json.JSONDecodeError:
        return []


# ------------------------------------------------------------------ main flow
def make_checklist(inc, bm25, use_llm=True, threshold=SCORE_THRESHOLD,
                   require_specific=True):
    query = build_query(inc)
    hazard = hazard_for(inc)
    hits = bm25.search(query, k=TOP_K, hazard=hazard, drop_sections=DROP_SECTIONS)

    # SPECIFICITY GUARD
    # BM25 sirf shabd milata hai, matlab nahi samajhta. "first aid injury" query
    # "Take the emergency kit, first aid box" se match kar jati hai - jabki wo line
    # evacuation ki hai, ilaaj ki nahi. Isliye: top chunk me incident ki KHAAS baat
    # (hazard ya vulnerable) ka koi shabd hona chahiye. Sirf need-type ke generic
    # shabd match hue to ye SOP ka jawab nahi hai.
    if require_specific and hits:
        parts = [inc.get("hazard") or ""] + list(inc.get("vulnerable") or [])
        # "food", "water", "shelter", "medicine" khud me khaas hain - inka naam
        # SOP me seedha milta hai. "rescue" aur "medical" bahut generic hain,
        # isliye unhe evidence nahi maanta.
        if inc.get("need") in CONCRETE_NEEDS:
            parts.append(inc["need"])
        specific = set(tok(" ".join(parts)))
        if specific:
            top_words = set()
            for _, c in hits[:3]:
                top_words |= set(tok(c["text"]))
            if not (specific & top_words):
                hits = []

    result = {"incident_id": inc.get("id", "?"), "query": query, "hazard": hazard,
              "retrieved": [{"id": c["id"], "score": round(s, 2),
                             "document": c["document"], "page": c["page"],
                             "section": c["section"], "text": c["text"]}
                            for s, c in hits]}

    if not hits or hits[0][0] < threshold:
        result["status"] = "NOT_IN_SOP"
        result["message"] = "Not in SOP, escalate to officer"
        result["items"] = []
        return result

    if not use_llm:
        result["status"] = "RETRIEVED_ONLY"
        result["items"] = [{"step": c["text"], "passage_id": c["id"]} for _, c in hits]
        return result

    passages = "\n".join("[%s] %s" % (c["id"], c["text"]) for _, c in hits)
    desc = json.dumps({k: inc.get(k) for k in
                       ("location", "need", "people_count", "vulnerable", "hazard")},
                      ensure_ascii=False)
    try:
        raw = call_gemini(PROMPT.format(incident=desc, passages=passages))
    except Exception as e:
        result["status"] = "LLM_ERROR"
        result["error"] = str(e)
        result["items"] = [{"step": c["text"], "passage_id": c["id"]} for _, c in hits]
        return result

    valid_ids = {c["id"] for _, c in hits}
    items, dropped = [], []
    for it in parse_items(raw):
        if isinstance(it, dict) and it.get("passage_id") in valid_ids:
            items.append(it)
        else:
            dropped.append(it)          # LLM ne apne se bana diya -> HATAO

    result["status"] = "OK" if items else "NOT_IN_SOP"
    result["items"] = items
    result["dropped_ungrounded"] = dropped
    return result


DEMO = [
    {"id": "INC-01", "location": "Society Area, Clement Town", "need": "rescue",
     "people_count": 1, "vulnerable": ["elderly"], "hazard": "water ~5 ft"},
    {"id": "INC-17", "location": "Graphic Era Hill University Campus", "need": "food",
     "people_count": 40, "vulnerable": ["child"], "hazard": None},
    {"id": "INC-25", "location": "Nehru Colony", "need": "rescue",
     "people_count": 5, "vulnerable": [], "hazard": "gas leak"},
    {"id": "INC-09", "location": "Mothrowala", "need": "rescue",
     "people_count": 2, "vulnerable": ["injured"], "hazard": "wall collapse, debris"},
]


def show(r):
    print("\n" + "=" * 62)
    print("%s   [%s]" % (r["incident_id"], r["status"]))
    print("query  : %s" % r["query"])
    print("hazard : %s" % r["hazard"])
    if r["status"] == "NOT_IN_SOP" and not r["items"]:
        print("\n  >> Not in SOP, escalate to officer")
        if r["retrieved"]:
            print("  (best score %.2f, threshold %.2f)" % (r["retrieved"][0]["score"], SCORE_THRESHOLD))
        return
    print("\nchecklist:")
    for i, it in enumerate(r["items"], 1):
        src = next((c for c in r["retrieved"] if c["id"] == it["passage_id"]), None)
        tag = "%s p%d / %s" % (src["document"], src["page"], src["section"]) if src else "?"
        print("  %d. %s" % (i, it["step"]))
        print("     source: %s" % tag)
    if r.get("dropped_ungrounded"):
        print("\n  DROPPED (SOP me nahi tha, LLM ne apne se jod diya): %d" % len(r["dropped_ungrounded"]))
        for d in r["dropped_ungrounded"][:3]:
            print("     - %s" % (d.get("step") if isinstance(d, dict) else d))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--chunks", default=CHUNKS)
    ap.add_argument("--incident", help="ek incident ka json file")
    ap.add_argument("--demo", action="store_true")
    ap.add_argument("--no-llm", action="store_true", help="sirf retrieval, LLM nahi")
    ap.add_argument("--threshold", type=float, default=SCORE_THRESHOLD)
    ap.add_argument("--out", help="result json me likho")
    a = ap.parse_args()

    if not os.path.exists(a.chunks):
        sys.exit("chunks.json nahi mila. Pehle chalao:  python rag_build.py")
    chunks = json.load(open(a.chunks, encoding="utf-8"))
    bm25 = BM25(chunks)
    print("index: %d chunks" % len(chunks))

    incidents = DEMO if a.demo or not a.incident else [json.load(open(a.incident, encoding="utf-8"))]
    results = [make_checklist(i, bm25, use_llm=not a.no_llm, threshold=a.threshold)
               for i in incidents]
    for r in results:
        show(r)

    ok = sum(1 for r in results if r["status"] in ("OK", "RETRIEVED_ONLY"))
    print("\n" + "=" * 62)
    print("checklist bani: %d / %d    NOT_IN_SOP: %d" % (
        ok, len(results), sum(1 for r in results if r["status"] == "NOT_IN_SOP")))
    if a.out:
        json.dump(results, open(a.out, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
        print("saved -> %s" % a.out)


if __name__ == "__main__":
    main()
