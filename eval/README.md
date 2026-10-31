# rag/ — SOP checklist system

Team phone pe jo checklist dikhti hai, wo yahan se banti hai. LLM apni yaadasht se
jawab nahi deta — sirf official SOP text se, aur har step pe source section.

## Chalana

```bash
pip install pdfplumber

python rag_build.py --sop ../data/sop --out chunks.json   # PDF -> chunks
python rag_checklist.py --demo --no-llm                   # retrieval dekho
python rag_checklist.py --demo                            # Gemini ke sath
python rag_eval.py --no-llm                               # numbers nikalo
```

API key environment me: `GEMINI_API_KEY`. **Kabhi code me nahi, kabhi GitHub pe nahi.**

---

## Teen file

| File | Kaam |
|---|---|
| `rag_build.py` | PDF → chunks, har chunk pe document + page + section + hazard tag |
| `rag_checklist.py` | query → retrieve → guard → LLM → grounding check |
| `rag_eval.py` | 20 test incidents pe grounding rate aur NOT_IN_SOP accuracy |

---

## Pipeline me chaar guard hain

Har guard ek asli failure se aaya hai jo testing me dikha. Judge ko yahi batana.

**1. Agriculture filter** — IMD ki flood PDF ka aadha hissa kheti ka hai. Bina filter
ke buzurg ke rescue pe top result aata tha: *"Apply excess N-fertilizer to crops."*
Agriculture content ko keyword se pakadte hain, heading se nahi — kyunki
*"After receding of flood water, farmers may…"* ko heading-matcher "after" section me
daal deta tha.

**2. Hazard filter** — fire ka SOP flood incident pe nahi aana chahiye. Chunk pe
hazard tag lagta hai, retrieval se pehle filter hota hai.

**3. Specificity guard** — BM25 sirf shabd milata hai, matlab nahi. Test me ye mila:

```
dialysis wala case (SOP me nahi)  → 6.56  "Take the emergency kit, first aid box…"
buzurg rescue (SOP me hai)        → 3.70  "Evacuate immediately to safe places"
```

Galat case ko sahi se **zyada** score mila, kyunki "first aid" query ne "first aid box"
se match kar liya — jabki wo line evacuation ki hai, ilaaj ki nahi. Threshold se ye
theek nahi hota. Isliye rule: top-3 chunks me incident ki **khaas** baat (hazard ya
vulnerable, ya food/water/shelter/medicine jaisa concrete need) ka shabd hona chahiye.
Sirf generic match = `NOT_IN_SOP`.

Is guard se jhooti checklist **10 se 3** aa gayi.

**4. Grounding check** — LLM har step pe passage id deta hai. Jis step ka id retrieved
set me nahi hai, wo **drop** ho jata hai. Isse LLM apne aap se step nahi jod sakta.

---

## Abhi ke numbers (sirf IMD flood PDF pe, 59 chunks)

```
grounding rate      : 1.000
NOT_IN_SOP accuracy : 0.700
jhooti checklist    : 3 / 20

coverage by need:
  rescue    7/11
  food      1/1
  water     0/1
  shelter   1/1
  medicine  1/1
  medical   0/5     <- SOP me medical kuch hai hi nahi
```

**Medical 0/5 bug nahi hai — ye sahi hai.** IMD ki do's-and-don'ts citizen advice hai;
usme cardiac, dialysis, delivery ya oxygen ka kuch likha hi nahi. System sahi keh raha
hai *"Not in SOP, escalate to officer."* Yahi hona chahiye.

---

## Limitation — ye khud bolna

**Ek hi document hai, aur wo citizen advice hai, field SOP nahi.** "Flood water me
mat jao" citizen ke liye theek hai; boat team ko to jaana hi hai. Isliye rescue coverage
7/11 pe atki hai aur medical zero hai.

Ye 0.700 accuracy **is corpus ka ceiling hai**, system ka nahi. Document add karne se
seedha upar jayega — threshold tune karne se nahi.

Jo add karna chahiye:
- NDMA **Temporary Shelters** guideline → shelter/food/water coverage
- NDMA **Disability Inclusive DRR** → R-17 jaisa case (abhi jhooti checklist bana raha hai)
- NDMA **Boat Safety** → boat team ke actual steps

Ek bhi add karke `rag_build.py` dobara chala dena, numbers khud badh jayenge.

---

## Judge Q&A

**"LLM hallucinate nahi karega?"**
Har step pe passage id hai. Jis step ka id retrieved passages me nahi, wo drop ho jata
hai — code me, prompt me nahi. Grounding rate 1.000 hai.

**"SOP me jawab na ho to?"**
`NOT_IN_SOP` → "escalate to officer". 20 test incidents me 7 aise the, saaton pe sahi
escalate kiya. 3 pe galti hui — wo honestly report kar rahe hain.

**"Embeddings kyun nahi, BM25 kyun?"**
BM25 pure python hai, koi install nahi, aur explainable hai — kaunsa shabd match hua
dikh jata hai. Embeddings next step hai; pipeline me retriever badalna ek function ka
kaam hai.

---

## 2-line explanation (brief ka 2-minute test)

- **rag_build.py** — "PDF ko line-level chunks me todta hai, har chunk pe document, page,
  section aur hazard tag lagata hai taaki retrieval se pehle filter ho sake."
- **rag_checklist.py** — "incident fields se query banta hai, BM25 top-5 nikalta hai,
  specificity guard generic match ko reject karta hai, phir LLM sirf un passages se
  checklist likhta hai aur bina valid passage id wala step drop ho jata hai."
- **rag_eval.py** — "20 incidents, aadhe jinka jawab SOP me hai aur aadhe jinka nahi;
  grounding rate aur NOT_IN_SOP accuracy dono naapta hai."
