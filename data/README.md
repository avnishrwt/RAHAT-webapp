# RAHAT test dataset — kya hai, kaise bana, kya limitation hai

Ye file padh le ek baar. Iske baad dataset ke kisi bhi sawaal ka jawab de payega.

---

## 1. Ek line me

200 Hinglish help messages, har ek ka sahi jawab pehle se likha hua.
Ye do kaam karta hai: **demo ka flood** aur **evaluation ka answer key**.

---

## 2. Isme kya hai

Geography asli Dehradun ki hai: Clement Town / GEHU ke aas-paas ka area, aur Rispana-Bindal basin — Dehradun ke sach me flood-prone ilake. Coordinates approximate hain; 2-3 jagah Google Maps pe verify karni hai kyunki optimizer inhi se distance nikaalta hai.

| | Count |
|---|---|
| Messages | 200 |
| Incidents (noise chhod ke) | 83 |
| Fake messages | 20 |
| Noise (non-emergency) | 25 |
| Jagah (area ke andar) | 16 |
| Jagah (area ke bahar, fakes ke liye) | 3 |

Channels: WhatsApp 100, SMS 86, helpline transcript 14
Burst window: 02:00 se 02:37 (37 minute)

---

## 3. Paanch block, aur har block kis cheez ka test hai

**Ye sabse zaroori section hai. Judge yahi poochega.**

| Block | Messages | Kyun daala |
|---|---|---|
| A — Duplicate clusters | 110 | Ek hi ghatna ke 2-5 message. Test: system inko **jod** paata hai? |
| B — Lone victims | 25 | Akela banda, ek hi message, koi aur report nahi kar raha. Test: priority **girti to nahi**? |
| C — Fakes | 20 | Test: fake **pakadta** hai? |
| D — Vague | 20 | Location ya need missing. Test: follow-up sawaal poochta hai, ya guess maar deta hai? |
| E — Noise | 25 | "kab tak barish rukegi". Test: faltu message ko emergency to nahi bana raha? |

---

## 4. Teen design decisions — inhi pe sawaal aayega

### (a) Near-miss pairs — 6 jode

INC-01 aur INC-02 **dono Society Area, Clement Town** ke hain. Par INC-01 me ek dadi upar phasi hai, INC-02 me 4 log chhat pe hain. **Alag ghatna.**

Aise 6 pair banaye: INC-01/02, 03/04, 05/06, 07/08, 09/10, 11/12.

**Kyun:** agar dataset me sirf saaf-saaf alag incidents hote, to system ka false-merge rate 0% aata — par wo number jhootha hota, kyunki galti karne ka mauka hi nahi diya. Near-miss pairs ke bina merge ka score meaningless hai.

### (b) Fakes teen type ke, ek type ke nahi

| Type | Kaise | Kya test karta hai |
|---|---|---|
| Copy-paste spam | **bilkul same text**, 6 alag sender, 2 min me | near-duplicate + timing detection |
| Out of area | Doiwala, Vikasnagar, Rishikesh — flood zone se bahar | geo boundary check |
| Serial reporter | **ek hi sender**, 3 alag jagah ki alag emergency | sender reputation |

PRD section 6.4 me yahi teen red flags likhe hain. Dataset teeno ko test karta hai.

### (c) Lone victims alag block kyun

RAHAT ka sabse bada claim ye hai: *"akela report karne wale ki priority nahi girti."*

Us claim ko test karne ke liye **akele log chahiye** dataset me. Isliye 25 aise messages hain jinka koi doosra confirmation nahi — buzurg, disabled, pregnant, akela bachha.

Agar system inko neeche dhakel de, to claim jhootha hai — aur dataset ye pakad lega.

---

## 5. Dev / test split — ye sabse important

```
dev_50.json    → 50 messages → Mayank prompt tuning ke liye
test_150.json  → 150 messages → LOCKED, hour 26 tak koi nahi dekhega
```

**Kyun:** agar Mayank unhi messages ko dekh ke prompt banaye jin pe final score nikalna hai, to wo exam se pehle question paper dene jaisa hai. Score aayega 95%, par wo ratta hai, samajh nahi.

**Aur ek cheez:** saare 6 near-miss pairs (INC-01 se INC-12) **test set me hain, dev me ek bhi nahi.** Matlab Mayank wo tricky cases dekh hi nahi sakta. Final eval me unhi se pata chalega ki system sach me alag ghatna pehchanta hai ya pattern ratt liya.

---

## 6. Labelling rules (poora `labelling_guide.md` me)

Sabse zyada confusion in teen pe hoti hai:

| Rule | Kya |
|---|---|
| `critical` vs `high` | Sawaal: *agle 1 ghante me koi na pahuncha to kya hoga?* Maut/serious injury → critical. Warna high. |
| `"4-5 log"` | Hamesha **4**. Chhota number. Over-estimate nahi karna. |
| Missing field | `null`. **Kabhi guess nahi.** Agar hum guess karenge to extractor ko galat reward milega. |

Ek aur: **buzurg hone se urgency apne aap nahi badhti.** Buzurg + khana = `medium` + `vulnerable: elderly`. Buzurg + paani me phasa = `critical`. Priority aur vulnerability alag field hain — PRD section 6 ka core idea yahi hai.

---

## 7. Limitations — ye khud bolna, judge ke poochne se pehle

Ye bolne se credibility **badhti** hai, ghatti nahi.

1. **Synthetic data hai, asli nahi.** Asli flood ke messages isse zyada tedhe, adhoore aur confusing hote hain.
2. **Messages AI se draft kiye, team ne edit kiye.** Isliye score thoda upar aa sakta hai — LLM ka likha text LLM ke liye padhna aasan hota hai. Asli deployment me accuracy kam hogi.
3. **Ek hi district, ek hi disaster type** (flood). Landslide ya earthquake pe test nahi kiya.
4. **Timestamps compressed hain** — 37 minute me 200 messages. Asli flood me burst isse bada aur lamba hota hai.
5. **Ground truth ek hi team ne banaya.** Ideal me 2 log alag-alag label karte aur agreement check hota.

Agla kadam: asli 112/ERSS message log pe validate karna, pilot ke dauraan.

---

## 8. Files

| File | Kya karti hai |
|---|---|
| `messages.json` | Master — 200 messages |
| `dev_50.json` | Mayank ke liye |
| `test_150.json` | Locked, final eval ke liye |
| `teams.json` | 8 rescue team — optimizer isi pe chalega |
| `alert.json` | IMD red alert — Surge Mode trigger |
| `locations.csv` | 18 jagah lat/lng ke saath |
| `labelling_guide.md` | Labelling rules |
| `incident_plan.md` | 83 incidents ka blueprint |
