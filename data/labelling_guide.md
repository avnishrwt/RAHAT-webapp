# Labelling Guide — RAHAT test set

Ye guide isliye hai ki 200 messages likhte-likhte hour 3 pe tu bhool na jaye ki hour 1 pe kya rule lagaya tha.
Jahan confusion ho, yahin dekh. Rule badalna pade to **yahin badal aur pehle ke labels bhi theek kar.**

> Pehle Mayank se field names confirm kar lena (PRD page 12-13). Agar wo `needs` (list) use kar raha hai aur tu `need` (string), to eval script sab galat dikhayega.

---

## 1. urgency — sabse zyada confusion yahin hoti hai

| Value | Matlab | Example |
|---|---|---|
| `critical` | Jaan ka khatra **abhi**. Agla 1 ghanta nahi nikalega | paani me phasa, chhat pe atka, saans nahi aa rahi, bah raha hai, malbe ke neeche |
| `high` | Serious hai, par abhi maut ka khatra nahi. Paani/halat **badh rahi** hai | ground floor me paani ghus raha, buzurg ko BP/sugar ki dawa khatam, bachhe ko tez bukhar |
| `medium` | Zaroorat hai, intezaar kar sakta hai | khana, peene ka paani, kambal, normal dawa |
| `low` | Sirf jaankari/sawal. Koi rescue nahi chahiye | "kab tak barish rukegi", "road khula h kya", "shelter kahan h" |

**Tie-breaker:** agar `critical` aur `high` me confusion ho —
poochh: *agli 1 ghanta koi na pahuncha to kya hoga?* Maut/serious injury → `critical`. Warna `high`.

**Dhyan:** buzurg hone se urgency apne aap nahi badhti. `vulnerable` alag field hai.
Buzurg + khana chahiye = `medium` + `vulnerable: ["elderly"]`. Buzurg + paani me phasa = `critical`.

---

## 2. need

Allowed: `rescue`, `medical`, `food`, `water`, `medicine`, `shelter`, `info`

- Ek se zyada lage to **main need** likh (jo pehle chahiye). Rescue hamesha jeetega.
- Message me need clear nahi → `null` (ye vague block me aayega)
- Noise/sawal → `info`

---

## 3. people_count

- Number saaf likha ho → wahi
- `"4-5 log"` → **4** (hamesha chhota number, over-estimate nahi karna)
- `"pura parivar"` → **4**
- `"hum sab"` / `"bahut log"` → `null`
- Sirf bhejne wala khud → **1**
- Bilkul pata nahi → `null`

**Rule: guess mat kar. `null` likhna galat nahi hai, galat number likhna galat hai.**

---

## 4. vulnerable

List hai. Allowed: `elderly`, `child`, `disabled`, `pregnant`, `injured`
Koi nahi → `[]` (khali list, `null` nahi)

- `elderly` tab jab umar 60+ ya "dadi/nana/buzurg/budhe" likha ho
- `child` tab jab "bachha/baby/chhota" ya umar 12 se kam
- `injured` tabhi jab chot ka zikr ho, bimari ka nahi
- "akela rehta hai" — ye vulnerable nahi hai. Ye lone-victim block ka hissa hai, label nahi.

---

## 5. location

- `locations.csv` ka **exact `name`** copy kar. Apne se mat likh.
- Message me alias/typo ho sakta hai (`rampur gali no 3`), par **label me hamesha `Society Area, Clement Town`**
- Location bilkul nahi → `null`
- Sirf landmark ("mandir ke peeche") aur jagah pehchani ja sakti ho → poora name likh
- Landmark itna vague ki pata na chale → `null`

---

## 6. true_incident_id

- Same ghatna ke sab messages = **same** id
- **Alag ghatna, same gali = ALAG id.** Ye near-miss hai, isme galti mat karna
- Fake → `FAKE-xx`
- Noise → `null`

**Test:** do message same incident tabhi hain jab ek hi rescue team ek baar ja ke dono ko cover kar le. Warna alag.

---

## 7. is_fake

`true` sirf in teen cases me:
1. Same text, bahut saare numbers se, minute bhar me
2. Location affected area ke **bahar** (`inside_area = no`)
3. Serial jhoothi report (ek hi sender bar-bar alag-alag jagah ki emergency)

Message agar sirf vague ya adhoora hai → `is_fake: false`. **Vague ≠ fake.**

---

## 8. Missing fields

Koi bhi field pata na chale → `null`. Kabhi guess mat karna.
PRD ka rule yahi hai, aur extractor ko bhi yahi karna hai. Agar tu guess karega to extractor ko galat tarike se punish/reward karega.

---

## 9. Likhte waqt

- Roman Hindi + thodi Devanagari + English mix
- Typos, "plz", "bhai", "jaldi", CAPS panic rakho
- Address ki jagah landmark
- Fuzzy numbers: "4-5 log", "pura parivar"
- Duplicates 2-15 minute ke andar aate hain; pura burst ~30 minute ka
- **AI se bulk mat banwana.** LLM ka likha message LLM aasani se padh leta hai → score fake-high, asli messages pe system phategaa

---

## 10. Format

```json
{
  "msg_id": "MSG-001",
  "channel": "whatsapp",
  "sender_id": "S-014",
  "timestamp": "2026-11-10T02:04:11",
  "raw_text": "society area clement town me dadi ji fasi hui h upar, paani bht h",
  "true_incident_id": "INC-01",
  "location": "Society Area, Clement Town",
  "need": "rescue",
  "people_count": 1,
  "vulnerable": ["elderly"],
  "urgency": "critical",
  "is_fake": false
}
```

`channel`: `sms` | `whatsapp` | `voice` | `helpline`
`sender_id`: har insaan ka alag. Duplicate ke liye alag sender. Fake copy-paste ke liye 15 alag sender.
