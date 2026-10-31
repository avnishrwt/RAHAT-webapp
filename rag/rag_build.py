#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
rag_build.py - SOP PDFs ko chunks me todta hai aur index banata hai.

Chalana:
  pip install pdfplumber
  python rag_build.py --sop ../data/sop --out chunks.json

Kya karta hai:
  1. Har PDF ka text nikalta hai (page number ke sath)
  2. English lines rakhta hai - Hindi is PDF me garbled aati hai (font encoding tuta hua)
  3. Bullet / heading ke hisaab se chunks banata hai
  4. Har chunk pe tag: document naam, page, section heading, hazard type

Hazard tag kyun: README me likha hai ki fire ka SOP flood incident pe nahi aana chahiye.
Retrieval se pehle hazard filter lagta hai - ye RAG ka sabse common failure hai.
"""

import argparse, json, os, re, sys

try:
    import pdfplumber
except ImportError:
    sys.exit("pdfplumber chahiye:  pip install pdfplumber")

# section detect karne ke liye - in shabdon se heading pehchante hain
SECTION_HINTS = [
    (r"\bbefore\b", "before"),
    (r"\bduring\b", "during"),
    (r"\bafter\b", "after"),
    (r"\bevacuat", "evacuation"),
    (r"\bagricultur|\bcrop|\bcattle", "agriculture"),
    (r"\bshelter", "shelter"),
    (r"\bfirst aid|\bmedical|\bhealth", "medical"),
    (r"\bdo\s*n[o']?t|\bdon.?ts\b", "donts"),
]

# hazard tag - retrieval ke waqt filter hoga
HAZARD_HINTS = {
    "flood": ["flood", "water", "rain", "inundat", "drown", "submerg"],
    "fire":  ["fire", "burn", "smoke", "gas leak", "cylinder"],
    "collapse": ["collapse", "debris", "rubble", "building", "wall"],
    "landslide": ["landslide", "slope", "boulder"],
}

# kaam ka nahi - demo me checklist me nahi aana chahiye
SKIP_PATTERNS = [
    r"^page \d+ of \d+$", r"^\*&\*&\*$", r"^\s*$",
    r"^\d+$",
]


def is_english(line):
    """Devanagari wali line chhod do - is PDF me wo garbled hai."""
    if not line.strip():
        return False
    deva = sum(1 for c in line if "\u0900" <= c <= "\u097F")
    return deva < len(line) * 0.15


def clean(line):
    line = line.replace("\u2019", "'").replace("\u2018", "'")
    line = re.sub(r"^[\u2022\-\*\u25cf]\s*", "", line)      # bullet hatao
    return re.sub(r"\s+", " ", line).strip()


# Agriculture ki lines heading se nahi pakdi jatin - "After receding of flood water,
# farmers may..." ko heading-matcher "after" section me daal deta hai. Isliye content
# ke shabdon se pakadte hain. Ye lines rescue checklist me kabhi nahi aani chahiye.
AGRI_WORDS = ["crop", "rice", "seedling", "fertilizer", "nursery", "hyv", "cattle",
              "sowing", "harvest", "transplant", "varieties", "arhar", "sesame",
              "paddy", "field", "k2o", "tillering", "produce", "seeds", "farmer",
              "cultivation", "water logging"]


def guess_section(line, current):
    low = line.lower()
    if any(w in low for w in AGRI_WORDS):
        return "agriculture"
    for pat, name in SECTION_HINTS:
        if re.search(pat, low) and len(line) < 70:
            return name
    return current


def guess_hazards(text):
    low = text.lower()
    out = [h for h, words in HAZARD_HINTS.items() if any(w in low for w in words)]
    return out or ["general"]


def chunk_pdf(path):
    name = os.path.basename(path)
    chunks, section = [], "general"
    with pdfplumber.open(path) as pdf:
        for pno, page in enumerate(pdf.pages, 1):
            text = page.extract_text() or ""
            for raw in text.split("\n"):
                if not is_english(raw):
                    continue
                line = clean(raw)
                if not line or any(re.match(p, line.lower()) for p in SKIP_PATTERNS):
                    continue
                section = guess_section(line, section)
                if len(line) < 25:                 # bahut chhota - heading hai, chunk nahi
                    continue
                chunks.append({
                    "id": "%s#p%d#%d" % (name.replace(".pdf", ""), pno, len(chunks) + 1),
                    "text": line,
                    "document": name,
                    "page": pno,
                    "section": section,
                    "hazards": guess_hazards(line),
                })
    return chunks


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sop", default="../data/sop", help="PDFs wala folder")
    ap.add_argument("--out", default="chunks.json")
    a = ap.parse_args()

    if not os.path.isdir(a.sop):
        sys.exit("folder nahi mila: %s" % a.sop)
    pdfs = [os.path.join(a.sop, f) for f in sorted(os.listdir(a.sop)) if f.lower().endswith(".pdf")]
    if not pdfs:
        sys.exit("koi PDF nahi mili %s me" % a.sop)

    all_chunks = []
    for p in pdfs:
        c = chunk_pdf(p)
        print("%-40s %3d chunks" % (os.path.basename(p), len(c)))
        all_chunks.extend(c)

    json.dump(all_chunks, open(a.out, "w", encoding="utf-8"),
              indent=2, ensure_ascii=False)

    from collections import Counter
    print("\nkul chunks : %d" % len(all_chunks))
    print("sections   : %s" % dict(Counter(c["section"] for c in all_chunks)))
    print("hazards    : %s" % dict(Counter(h for c in all_chunks for h in c["hazards"])))
    print("\nsaved -> %s" % a.out)

    if len(all_chunks) < 40:
        print("\nWARNING: chunks kam hai. Checklist patli aayegi aur NOT_IN_SOP")
        print("         zyada aayega. Ek aur SOP document add karo.")


if __name__ == "__main__":
    main()
