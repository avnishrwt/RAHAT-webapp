# Incident Plan — 200 messages

Ye plan pehle, messages baad me. Isse 3 guna fast likhega aur mix control me rahega.

| Block | Incidents | Messages |
|---|---|---|
| A — Duplicate clusters | 30 | 110 |
| B — Lone victims | 25 | 25 |
| C — Fakes | 8 groups | 20 |
| D — Vague | 20 | 20 |
| E — Noise | — | 25 |
| **Total** | | **200** |

Burst window: `2026-11-10T02:00` se `02:35` tak.

---

## Block A — 30 incidents, 110 messages

`NM` = near-miss pair. **Same jagah, alag ghatna — ye ALAG incident hain.** 6 pairs hain. Inme galti hui to false-merge rate measure hi nahi hoga.

| ID | Location | Kya hua | need | urgency | vulnerable | people | msgs | Note |
|---|---|---|---|---|---|---|---|---|
| INC-01 | Society Area, Clement Town | Dadi akeli, 1st floor pe phasi, paani 5ft | rescue | critical | elderly | 1 | 5 | **NM-1a** |
| INC-02 | Society Area, Clement Town | 4 log chhat pe atke, same gali | rescue | critical | child | 4 | 4 | **NM-1b** |
| INC-03 | Banjarawala | Pati-patni ground floor me phase | rescue | critical | [] | 2 | 4 | **NM-2a** |
| INC-04 | Banjarawala | Alag ghar, aadmi ka pair toota, nikal nahi sakta | medical | critical | injured | 1 | 3 | **NM-2b** |
| INC-05 | Bindal Basti | 6 log ek kamre me, paani badh raha | rescue | critical | child | 6 | 5 | **NM-3a** |
| INC-06 | Bindal Basti | Buzurg jodi, dawa khatam, 2 din se | medicine | high | elderly | 2 | 3 | **NM-3b** |
| INC-07 | Dharampur | Gaadi me log phase, paani ghus gaya | rescue | critical | [] | 3 | 4 | **NM-4a** |
| INC-08 | Dharampur | Pados ke ghar me pregnant mahila, labour pain | medical | critical | pregnant | 1 | 4 | **NM-4b** |
| INC-09 | Mothrowala | Deewar giri, 2 log malbe me | rescue | critical | injured | 2 | 5 | **NM-5a** |
| INC-10 | Mothrowala | Doosri building, 8 log upar phase | rescue | critical | elderly,child | 8 | 5 | **NM-5b** |
| INC-11 | Nehru Colony | Bachhe ko tez bukhar, aspataal nahi ja paa rahe | medical | high | child | 1 | 3 | **NM-6a** |
| INC-12 | Nehru Colony | Alag ghar, disabled aadmi akela phasa | rescue | critical | disabled | 1 | 4 | **NM-6b** |
| INC-13 | Bell Road, Clement Town | Poora parivar chhat pe, paani 4ft | rescue | critical | child | 4 | 5 | |
| INC-14 | Rispana Pul | 3 log ghat ke paas phase, bahao tez | rescue | critical | [] | 3 | 5 | Highest hazard |
| INC-15 | Kargi Chowk | Road bandh, 10 log atke, boat chahiye | rescue | critical | elderly | 10 | 4 | Boat-only |
| INC-16 | Patel Nagar | Dukaan me 2 log phase | rescue | high | [] | 2 | 4 | |
| INC-17 | Graphic Era Hill University Campus | Shelter me 40 log, khana nahi | food | medium | child | 40 | 4 | |
| INC-18 | Graphic Era Hill University Campus | Shelter me peene ka paani khatam | water | medium | [] | 40 | 3 | Same jagah, alag need |
| INC-19 | Ajabpur Kalan | Buzurg dampati, ghar me paani, nikal nahi sakte | rescue | critical | elderly | 2 | 4 | |
| INC-20 | ISBT Dehradun | 5 log dukaan ke upar atke | rescue | high | [] | 5 | 4 | |
| INC-21 | CHC Majra | Aspataal me generator band, 2 patient oxygen pe | medical | critical | injured | 2 | 4 | |
| INC-22 | Bindal Basti | Chhat gir gayi, 3 log dabe | rescue | critical | injured | 3 | 5 | |
| INC-23 | Bell Road, Clement Town | Buzurg mahila akeli, sugar ki dawa khatam | medicine | high | elderly | 1 | 3 | |
| INC-24 | Shiv Mandir, Banjarawala | Mandir me 15 log sharan liye, kambal chahiye | shelter | medium | elderly,child | 15 | 4 | |
| INC-25 | Nehru Colony | Gas leak ka shak, 5 ghar khali karne hain | rescue | critical | [] | 5 | 4 | |
| INC-26 | Patel Nagar | Bijli ka khamba gira, taar paani me | rescue | critical | [] | 3 | 3 | |
| INC-27 | Banjarawala | 2 bachhe school se nahi laute | rescue | critical | child | 2 | 4 | |
| INC-28 | Mothrowala | 3 parivaar bina khane ke, 1 din se | food | medium | child | 12 | 3 | |
| INC-29 | Rispana Pul | Aadmi bah gaya, dekha gaya tha | rescue | critical | [] | 1 | 2 | |
| INC-30 | Dharampur | Buzurg ko dialysis miss ho raha | medical | high | elderly | 1 | 2 | |

**Check:** 5×8 + 4×10 + 3×6 + 2×2 = 40+40+18+4 = **102**
Baaki 8 messages: INC-01, 05, 09, 10, 13, 14, 22 aur 15 me se kisi ko ek-ek extra message de de → **110** ✓

---

## Block B — 25 lone victims, 1 message each

Ek banda, ek message, koi aur uske liye report nahi kar raha. **Ye RAHAT ka sabse bada pitch point hai** — confidence neutral rehna chahiye, priority girni nahi chahiye.

| ID | Location | Kaun | need | urgency | vulnerable |
|---|---|---|---|---|---|
| INC-31 | Ajabpur Kalan | 75 saal, akela, paani ghar me | rescue | critical | elderly |
| INC-32 | Ajabpur Kalan | 80 saal mahila, chalne me dikkat | rescue | critical | elderly,disabled |
| INC-33 | Bindal Basti | Wheelchair user, akela | rescue | critical | disabled |
| INC-34 | Society Area, Clement Town | Buzurg, dawa khatam | medicine | high | elderly |
| INC-35 | Nehru Colony | Pregnant mahila akeli | medical | critical | pregnant |
| INC-36 | Banjarawala | 70 saal, dil ke mareez | medical | critical | elderly |
| INC-37 | Mothrowala | Andha vyakti, akela | rescue | critical | disabled |
| INC-38 | Dharampur | Buzurg, 2 din se khana nahi | food | high | elderly |
| INC-39 | Patel Nagar | Akela aadmi, pair me chot | medical | high | injured |
| INC-40 | Rispana Pul | Buzurg, ghat ke paas ka ghar | rescue | critical | elderly |
| INC-41 | Bell Road, Clement Town | Vidhwa mahila, 2 chhote bachhe | rescue | critical | child |
| INC-42 | ISBT Dehradun | Chowkidar dukaan me phasa | rescue | high | [] |
| INC-43 | Kargi Chowk | Buzurg, road bandh | rescue | critical | elderly |
| INC-44 | Ajabpur Kalan | Bimaar aadmi, akela | medical | high | [] |
| INC-45 | Shiv Mandir, Banjarawala | Buzurg, mandir ke peeche ghar | rescue | critical | elderly |
| INC-46 | Bindal Basti | Mazdoor, naya aaya, kisi ko nahi jaanta | rescue | high | [] |
| INC-47 | Nehru Colony | Buzurg jodi, phone battery khatam ho raha | rescue | critical | elderly |
| INC-48 | Mothrowala | Mental illness wala vyakti, akela | rescue | critical | disabled |
| INC-49 | Graphic Era Hill University Campus | Chowkidar, shelter me akela | food | medium | [] |
| INC-50 | Society Area, Clement Town | 68 saal, saans ki bimari | medical | critical | elderly |
| INC-51 | Banjarawala | Akeli mahila, raat me dar lag raha | rescue | high | [] |
| INC-52 | Dharampur | Buzurg, insulin fridge me, bijli nahi | medicine | high | elderly |
| INC-53 | Patel Nagar | Bachha akela, maa-baap kaam pe gaye | rescue | critical | child |
| INC-54 | CHC Majra | Patient, attendant nahi aaya | medical | high | injured |
| INC-55 | Rispana Pul | Buzurg mahila, ghar me paani 3ft | rescue | critical | elderly |

---

## Block C — Fakes, 8 groups, 20 messages

`is_fake: true`, `true_incident_id: FAKE-0x`

| ID | Type | msgs | Kaise likhna |
|---|---|---|---|
| FAKE-01 | Copy-paste spam | 6 | **Bilkul same text**, 6 alag sender, 2 minute ke andar. "URGENT 50 log phase hai Doiwala Market pe" |
| FAKE-02 | Copy-paste spam | 4 | Same text, 4 sender. Vikasnagar (bahar) |
| FAKE-03 | Out of area | 2 | Doiwala Market — flood zone se bahar |
| FAKE-04 | Out of area | 1 | Doiwala Market, normal text (copy-paste nahi) |
| FAKE-05 | Serial reporter | 3 | **Ek hi sender_id**, 3 alag jagah ki alag emergency, 5 min me |
| FAKE-06 | Serial reporter | 2 | Ek aur sender, 2 unrelated emergency |
| FAKE-07 | Exaggerated | 1 | "pura mohalla doob gaya 500 log marr gaye" — naamumkin number |
| FAKE-08 | Prank | 1 | Saaf mazaak wala message |

---

## Block D — Vague, 20 messages

`is_fake: false`. Asli madad chahiye, par kuch field missing. Ye FR03 (follow-up sawaal) test karta hai.

| Count | Kya missing | Example |
|---|---|---|
| 8 | Location `null` | "bachao paani aa gaya jaldi" |
| 6 | Need `null` | "society area clement town, please help" |
| 4 | Location itna vague ki pehchana na jaye | "mandir ke paas wali gali" |
| 2 | people_count `null` | "bahut saare log phase hain Nehru Colony me" |

Inko apni-apni `INC-56` se `INC-75` id do.

---

## Block E — Noise, 25 messages

`true_incident_id: null`, `need: info`, `urgency: low`, `is_fake: false`

Mix aise rakh:
- 8 — mausam ke sawaal ("kab tak barish rukegi", "kal bhi alert h kya")
- 6 — road/transport ("haridwar road khula h", "bus chal rahi h kya isbt se")
- 5 — shelter ki jaankari ("shelter kahan h", "school me jagah h")
- 3 — shukriya wale message
- 3 — galat number / faltu

---

## Likhne ka order

1. Block A pehle (sabse bada, sabse important). Har incident ka pehla message likh, phir usi baat ko 2-4 alag logon ke shabdon me.
2. Block B — fast hai, 25 single messages
3. Block C — copy-paste wale literally copy-paste kar, bas sender_id badal
4. Block D, E — sabse fast, aakhir me

## Likhne ke baad

```
dev_50.json    → 50 messages → Mayank ko
test_150.json  → 150 messages → LOCKED, hour 26 tak kisi ko nahi
```

dev wale 50 me har block se thoda-thoda ho, par **saare 6 near-miss pairs test set me rakh.** Mayank ko wo nahi dikhne chahiye.
