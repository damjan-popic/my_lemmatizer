# Multi-word-unit / span-layer changes

## Slovensko

Ta različica lematizatorja uvaja eksplicitno plast za večbesedne enote oziroma razpone čez več tokenov. Prejšnja logika je pravila LORIS ujemala skoraj izključno token po tokenu, zato sprožilci z več besedami, na primer `z otroci`, `odpri lučke`, `okoristiti se` ali `compact disc`, niso bili zanesljivo dosegljivi. Večbesedni toponimi so bili obravnavani ločeno kot surovo iskanje po nizu, kar ni bilo dovolj povezano s tokeni.

### Kaj se je spremenilo

1. **Ločeni indeksi za enobesedne in večbesedne sprožilce**

   Pri nalaganju `loris_rules_final.json` se sprožilci zdaj razdelijo v:

   - `lemma_index` za en token;
   - `surface_index` za en token;
   - `lemma_phrase_index` za večtokenalne lemske sprožilce;
   - `surface_phrase_index` za večtokenalne površinske sprožilce;
   - `surface_name_index` za večbesedna lastna imena oziroma toponime.

   To odpravi problem, da se je niz `z otroci` iskal kot `tok.text`, čeprav spaCy vrne dva tokena: `z` in `otroci`.

2. **Ujemanje z oknom tokenov**

   Večbesedni sprožilci se zdaj iščejo z drsečim oknom čez tokenizirano besedilo. Za površinske sprožilce se primerja normaliziran izsek izvirnega besedila; za lemske sprožilce se primerja zaporedje lem.

   Primer:

   ```text
   input:  Okoristil se je z izkušnjami.
   leme:   okoristiti se biti z izkušnja
   match:  okoristiti se
   ```

3. **Normalizacija pri primerjavi**

   Ujemanje uporablja `casefold()` in strnjeno presledkovno normalizacijo. Zato se `Z otroci` ujame z istim pravilom kot `z otroci`, več zaporednih presledkov pa ne blokira ujemanja.

4. **Nova plast `spans`**

   Odgovor `/loris/check` še vedno vsebuje stari polji `tokens` in `issues`, dodano pa je novo polje `spans`. To je mesto, kjer frontend ujame večbesedne enote.

   Primer oblike:

   ```json
   {
     "tokens": [
       {"text": "z", "lemma": "z", "pos": "ADP", "start": 0, "end": 1},
       {"text": "otroci", "lemma": "otrok", "pos": "NOUN", "start": 2, "end": 8}
     ],
     "issues": [
       {
         "rule_id": "slogovni_z otroci",
         "category": "slogovni",
         "start": 0,
         "end": 8,
         "priority": 70,
         "payload": {"Pravilno": "z otroki"}
       }
     ],
     "spans": [
       {
         "type": "multiword_rule",
         "rule_id": "slogovni_z otroci",
         "category": "slogovni",
         "match_on": "surface",
         "trigger": "z otroci",
         "start": 0,
         "end": 8,
         "token_start": 0,
         "token_end": 2,
         "token_indexes": [0, 1],
         "surface": "z otroci",
         "normalized": "z otroci",
         "priority": 70,
         "payload": {"Pravilno": "z otroki"}
       }
     ]
   }
   ```

5. **Nov endpoint `/analyze-full`**

   `/analyze` ostaja nespremenjen in vrača samo seznam tokenov. Novi endpoint `/analyze-full` vrača:

   ```json
   {
     "tokens": [...],
     "spans": [...]
   }
   ```

   To je uporabno, če frontend potrebuje tokenizacijo in večbesedne razpone, ne pa nujno celotnega seznama `issues`.

6. **Reševanje prekrivanj**

   Sistem še vedno ohranja staro logiko za konflikte z istim `start`/`end`: pri istem razponu obdrži pravilo z višjo prioriteto. Dodano je tudi zaviranje krajših ujemanj iste kategorije, kadar jih pokrije daljše pravilo z enako ali višjo prioriteto.

### Kako to vpliva na frontend

Obstoječi frontend, ki bere samo:

```js
response.tokens
response.issues
```

lahko deluje naprej. Polje `issues` je namerno ostalo v stari obliki.

Nov ali popravljen frontend pa naj za večbesedne enote bere:

```js
response.spans
```

Za označevanje besedila uporabi:

```js
span.start
span.end
```

Za povezovanje s tokeni uporabi:

```js
span.token_indexes
// ali
span.token_start
span.token_end
```

Za odločitev, kako je bil razpon najden, uporabi:

```js
span.match_on
// "surface", "lemma", "surface_name"
```

Za UI je priporočljivo:

- `issues` uporabljati kot seznam opozoril;
- `spans` uporabljati kot natančno plast za označevanje razponov;
- pri večbesednih opozorilih poudariti celoten `span.start`–`span.end`, ne posameznih tokenov;
- pri `surface_name` prikazati razpon kot lastno ime/toponim.

---

## English

This version of the lemmatizer adds an explicit span layer for multi-word units. Previously, most LORIS rules were matched token by token, which meant that triggers such as `z otroci`, `odpri lučke`, `okoristiti se`, or `compact disc` were not reliably reachable. Multi-word toponyms were handled separately as raw string search, not as token-connected spans.

### What changed

1. **Separate indexes for single-token and multi-token triggers**

   While loading `loris_rules_final.json`, triggers are now split into:

   - `lemma_index` for one-token lemma triggers;
   - `surface_index` for one-token surface triggers;
   - `lemma_phrase_index` for multi-token lemma triggers;
   - `surface_phrase_index` for multi-token surface triggers;
   - `surface_name_index` for names/toponyms.

   This fixes the bug where `z otroci` was looked up as a single `tok.text`, even though spaCy returns two tokens: `z` and `otroci`.

2. **Token-window matching**

   Multi-word triggers are now matched with a sliding window over tokenized text. Surface triggers compare a normalized slice of the original text; lemma triggers compare the normalized lemma sequence.

   Example:

   ```text
   input:   Okoristil se je z izkušnjami.
   lemmas:  okoristiti se biti z izkušnja
   match:   okoristiti se
   ```

3. **Normalized matching**

   Matching uses `casefold()` and whitespace normalization. `Z otroci` therefore matches the same rule as `z otroci`, and repeated spaces do not block a match.

4. **New `spans` layer**

   `/loris/check` still returns the old `tokens` and `issues`, but now also returns `spans`. This is the frontend catch point for multi-word units.

5. **New `/analyze-full` endpoint**

   `/analyze` remains unchanged and returns only tokens. `/analyze-full` returns:

   ```json
   {
     "tokens": [...],
     "spans": [...]
   }
   ```

6. **Overlap handling**

   The old exact-span conflict rule is preserved: when several issues have the same `start`/`end`, the highest-priority issue wins. The resolver also suppresses shorter same-category matches when a longer match with equal or higher priority covers them.

### Frontend impact

Existing frontend code that reads only:

```js
response.tokens
response.issues
```

can continue working. The `issues` shape was kept stable on purpose.

New or upgraded frontend code should catch multi-word-unit data at:

```js
response.spans
```

Use:

```js
span.start
span.end
```

for text highlighting, and:

```js
span.token_indexes
span.token_start
span.token_end
```

for token-level anchoring.

Use:

```js
span.match_on
```

to know whether the span was matched by `surface`, `lemma`, or `surface_name`.
