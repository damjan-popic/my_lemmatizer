# my_lemmatizer

FastAPI service for Slovenian/Italian token analysis and LORIS rule checking. LingHub normally calls this service; browser frontends should usually call LingHub, not this service directly.

Current main port in the deployment examples: `8001`.

---

## English

### What changed in this package

This version includes the MWU/span-layer work and the new approved LORIS import.

1. **Multi-word LORIS rules are now matchable.**
   - Single-token lemma triggers still go through `lemma_index`.
   - Single-token surface triggers still go through `surface_index`.
   - Multi-token lemma triggers now go through `lemma_phrase_index`.
   - Multi-token surface triggers now go through `surface_phrase_index`.
   - `surface_name` triggers are token-window matches, not raw `text.find()` substring matches.

2. **Multi-token lemma rules also have an exact-surface fallback.**
   This matters for spreadsheet-approved terms such as `na štiri roke`, `v okviru`, or `v sklopu`. Their display form may be the actual user-facing error string even when spaCy’s lemma sequence differs slightly. The rule is still reported as `match_on: "lemma"`, but the window can match either the lemma sequence or the exact normalized surface phrase.

3. **New endpoint:**

   ```http
   POST /analyze-full
   ```

   It returns both token data and span-level LORIS/MWU matches:

   ```json
   {
     "tokens": [...],
     "spans": [...]
   }
   ```

4. **Changed endpoint, backward-compatible:**

   ```http
   POST /loris/check
   ```

   It still returns `tokens` and `issues`, and now also returns `spans`. `spans` now covers token-level rules as `type: "token_rule"` and multi-word rules as `type: "multiword_rule"`, so a new frontend can use `spans` as the richer rendering source while `issues` remains the compact compatibility list:

   ```json
   {
     "tokens": [...],
     "issues": [...],
     "spans": [...]
   }
   ```

5. **New LORIS entries imported from the approved spreadsheet.**
   Source workbook: `Loris_novi vnosi_Final_1.2.xlsx`.
   Canonical source sheet: `Termini_EMZ`, rows `2–90`.

   Import result:

   - approved rows read: `89`
   - existing paronym rules refreshed: `25`
   - new paronym rules added: `64`
   - final number of LORIS rules: `1798`

   The import is an **upsert**, not a blind append. Existing paronym lemma triggers are updated instead of duplicated. See `LORIS_IMPORT_REPORT.md` for the exact row-by-row report.

6. **Source/audit data added:**

   ```text
   data/loris_imports/termini_emz_2026-06-12.json
   LORIS_IMPORT_REPORT.md
   ```

7. **Deployment helpers added:**

   ```text
   requirements.txt
   deployment/my-lemmatizer.service
   ```

---

### API contract for LingHub/front-end developers

The browser frontend should usually call LingHub on port `8010`. LingHub then calls this service internally. The schema below matters because LingHub forwards it.

#### `POST /analyze`

Token-only endpoint. Existing behavior is unchanged.

Request:

```json
{
  "lang": "sl",
  "text": "Lev je moj sinček."
}
```

Response:

```json
[
  {
    "text": "Lev",
    "lemma": "Lev",
    "pos": "PROPN",
    "start": 0,
    "end": 3
  }
]
```

#### `POST /analyze-full`

Use this when the caller needs tokens plus rich LORIS rule spans but not the simplified `issues` list. `spans` includes single-token rules (`token_rule`) and multi-token rules (`multiword_rule`).

Response shape:

```json
{
  "tokens": [
    {
      "text": "na",
      "lemma": "na",
      "pos": "ADP",
      "start": 0,
      "end": 2
    }
  ],
  "spans": [
    {
      "type": "multiword_rule",
      "rule_id": "paronym_na_štiri_roke",
      "category": "paronym",
      "match_on": "lemma",
      "trigger": "na štiri roke",
      "start": 0,
      "end": 13,
      "token_start": 0,
      "token_end": 3,
      "token_indexes": [0, 1, 2],
      "surface": "na štiri roke",
      "normalized": "na štiri roke",
      "priority": 100,
      "payload": {
        "Izhodisce": "na štiri roke",
        "Iscete": "a quattro mani",
        "SteMislili": "štiriročno; dva, dve / v dvoje / oba, obe"
      }
    }
  ]
}
```

#### `POST /loris/check`

This is the main LORIS endpoint. Existing UIs can keep reading `issues`. New MWU-aware UIs should additionally read `spans`.

Response fields:

- `tokens`: token-level NLP output.
- `issues`: compact warning list, kept for backward compatibility.
- `spans`: richer rule-span list for multi-word units, named entities, and token anchoring.

Frontend dedupe hint:

```js
const issues = response.issues ?? [];
const spans = response.spans ?? [];

// If you render both, avoid duplicate cards/highlights with this key:
const key = item => `${item.rule_id}:${item.start}:${item.end}`;
```

Important span details:

- `start` and `end` are character offsets in the original input text.
- `token_start` is inclusive.
- `token_end` is exclusive.
- `token_indexes` is included for convenience.
- `match_on` can be `lemma`, `surface`, or `surface_name`.
- `payload` is user-facing rule content. Do **not** assume all payload keys exist; blank spreadsheet cells and `/` markers are omitted.

---

### Local development with `venv`

From the repo root:

```bash
cd /path/to/my_lemmatizer
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip wheel setuptools
pip install -r requirements.txt
python -m spacy download sl_core_news_lg
python -m spacy download it_core_news_lg
```

Run locally:

```bash
source .venv/bin/activate
uvicorn app:app --host 127.0.0.1 --port 8001 --reload
```

Health check:

```bash
curl http://127.0.0.1:8001/health
```

LORIS check example:

```bash
curl -s -X POST http://127.0.0.1:8001/loris/check \
  -H 'Content-Type: application/json' \
  -d '{"lang":"sl","text":"To smo naredili na štiri roke."}' | python -m json.tool
```

---

### Production deployment with `systemctl`

The included template assumes this layout:

```text
/opt/my_lemmatizer
/opt/my_lemmatizer/.venv
```

Install/update code:

```bash
sudo mkdir -p /opt/my_lemmatizer
sudo rsync -a --delete ./ /opt/my_lemmatizer/
sudo chown -R www-data:www-data /opt/my_lemmatizer
```

Create the virtual environment as the deployment user or adjust ownership after installing:

```bash
cd /opt/my_lemmatizer
sudo -u www-data python3 -m venv .venv
sudo -u www-data .venv/bin/python -m pip install --upgrade pip wheel setuptools
sudo -u www-data .venv/bin/pip install -r requirements.txt
sudo -u www-data .venv/bin/python -m spacy download sl_core_news_lg
sudo -u www-data .venv/bin/python -m spacy download it_core_news_lg
```

Install the service file:

```bash
sudo cp /opt/my_lemmatizer/deployment/my-lemmatizer.service /etc/systemd/system/my-lemmatizer.service
sudo systemctl daemon-reload
sudo systemctl enable --now my-lemmatizer.service
```

Check status and logs:

```bash
sudo systemctl status my-lemmatizer.service
sudo journalctl -u my-lemmatizer.service -f
```

Restart after code or JSON changes:

```bash
sudo systemctl restart my-lemmatizer.service
```

Reload service file changes:

```bash
sudo systemctl daemon-reload
sudo systemctl restart my-lemmatizer.service
```

---

## Slovenščina

### Kaj se je spremenilo v tem paketu

Ta različica vključuje podporo za večbesedne enote/razpone in nov uvoz potrjenih LORIS vnosov.

1. **Večbesedna LORIS pravila se zdaj dejansko lahko ujamejo.**
   - Enobesedni lemski sprožilci ostanejo v `lemma_index`.
   - Enobesedni površinski sprožilci ostanejo v `surface_index`.
   - Večbesedni lemski sprožilci so zdaj v `lemma_phrase_index`.
   - Večbesedni površinski sprožilci so zdaj v `surface_phrase_index`.
   - `surface_name` sprožilci se iščejo z okni tokenov, ne več z navadnim `text.find()`.

2. **Večbesedna lemska pravila imajo tudi natančen površinski fallback.**
   To je pomembno za potrjene izraze, kot so `na štiri roke`, `v okviru` ali `v sklopu`. Prikazna oblika iz preglednice je pogosto tudi dejanska napačna uporabniška oblika, čeprav se notranje zaporedje lem lahko nekoliko razlikuje. Pravilo je še vedno označeno kot `match_on: "lemma"`, vendar se lahko okno ujame po zaporedju lem ali po natančni normalizirani površinski obliki.

3. **Nov endpoint:**

   ```http
   POST /analyze-full
   ```

   Vrne `tokens` in `spans`.

4. **Spremenjen endpoint, združljiv za nazaj:**

   ```http
   POST /loris/check
   ```

   Še vedno vrača `tokens` in `issues`, zdaj pa doda še `spans`.

5. **Uvoženi so novi LORIS vnosi iz potrjene preglednice.**
   Izvorna datoteka: `Loris_novi vnosi_Final_1.2.xlsx`.
   Kanonični list: `Termini_EMZ`, vrstice `2–90`.

   Rezultat uvoza:

   - prebranih potrjenih vrstic: `89`
   - posodobljenih obstoječih pravil `paronym`: `25`
   - dodanih novih pravil `paronym`: `64`
   - končno število LORIS pravil: `1798`

   Uvoz je **upsert**, ne slepo dodajanje. Če je lemski sprožilec že obstajal, se obstoječe pravilo posodobi in se ne podvoji. Podrobnosti so v `LORIS_IMPORT_REPORT.md`.

---

### Kaj mora vedeti frontend razvijalec

Frontend naj praviloma kliče LingHub na portu `8010`, ne neposredno tega servisa. LingHub ta servis kliče interno in posreduje relevantne podatke.

Glavno pravilo za prikaz:

```js
const issues = response.issues ?? [];
const spans = response.spans ?? [];
```

Če uporabljaš samo stari UI, lahko še vedno bereš `issues`. Če želiš pravilen prikaz večbesednih enot, beri `spans`.

Za označevanje v besedilu uporabi:

```js
span.start
span.end
```

Za sidranje na tokene uporabi:

```js
span.token_indexes
span.token_start
span.token_end // ekskluziven indeks
```

`payload` je namenjen prikazu uporabniku. Ne predpostavljaj, da obstajajo vsa polja (`Iscete`, `SteMislili`, `Npr`, `Vslo`). Prazne celice in znaki `/` iz preglednice so izpuščeni.

---

### Lokalna namestitev z `venv`

```bash
cd /path/to/my_lemmatizer
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip wheel setuptools
pip install -r requirements.txt
python -m spacy download sl_core_news_lg
python -m spacy download it_core_news_lg
uvicorn app:app --host 127.0.0.1 --port 8001 --reload
```

Preverjanje:

```bash
curl http://127.0.0.1:8001/health
```

---

### Produkcijska namestitev s `systemctl`

Predpostavljena pot:

```text
/opt/my_lemmatizer
```

Ukazi:

```bash
sudo mkdir -p /opt/my_lemmatizer
sudo rsync -a --delete ./ /opt/my_lemmatizer/
sudo chown -R www-data:www-data /opt/my_lemmatizer

cd /opt/my_lemmatizer
sudo -u www-data python3 -m venv .venv
sudo -u www-data .venv/bin/python -m pip install --upgrade pip wheel setuptools
sudo -u www-data .venv/bin/pip install -r requirements.txt
sudo -u www-data .venv/bin/python -m spacy download sl_core_news_lg
sudo -u www-data .venv/bin/python -m spacy download it_core_news_lg

sudo cp /opt/my_lemmatizer/deployment/my-lemmatizer.service /etc/systemd/system/my-lemmatizer.service
sudo systemctl daemon-reload
sudo systemctl enable --now my-lemmatizer.service
sudo systemctl status my-lemmatizer.service
```

Logi:

```bash
sudo journalctl -u my-lemmatizer.service -f
```
