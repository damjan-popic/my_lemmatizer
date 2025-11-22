from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any
from collections import defaultdict
from pathlib import Path
import spacy
import json

# ---------- CONFIG ----------

BASE_DIR = Path(__file__).resolve().parent
RULES_PATH = BASE_DIR / "loris_rules_final.json"

SUPPORTED_LANGS = {"sl", "it"}  # Slovene, Italian


# ---------- Pydantic MODELS ----------

class AnalyzeRequest(BaseModel):
    lang: str  # "sl" or "it"
    text: str


class Token(BaseModel):
    text: str
    lemma: str
    pos: str
    start: int
    end: int


class Issue(BaseModel):
    rule_id: str
    category: str
    start: int
    end: int
    priority: int
    payload: Dict[str, Any]


class LorisResponse(BaseModel):
    tokens: List[Token]
    issues: List[Issue]


# ---------- LOAD spaCy MODELS ----------

print("Loading spaCy Slovenian model (sl_core_news_lg)...")
# If you prefer md/sm, change this name and make sure you've downloaded it
nlp_sl = spacy.load("sl_core_news_lg")

print("Loading spaCy Italian model (it_core_news_lg)...")
nlp_it = spacy.load("it_core_news_lg")


# ---------- LOAD RULES & BUILD INDEXES ----------

print(f"Loading rules from {RULES_PATH}...")
with RULES_PATH.open("r", encoding="utf-8") as f:
    RULES_DATA = json.load(f)

RAW_RULES: List[Dict[str, Any]] = RULES_DATA.get("rules", [])

# Indexes for fast matching
lemma_index: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
surface_index: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
surface_name_rules: List[Dict[str, Any]] = []  # multi-word toponyms etc.

for rule in RAW_RULES:
    trig = rule.get("trigger", {})
    ttype = trig.get("type")

    if ttype == "lemma":
        for lemma in trig.get("lemmas", []):
            if lemma:
                lemma_index[lemma.lower()].append(rule)

    elif ttype == "surface":
        for form in trig.get("forms", []):
            if form:
                surface_index[form].append(rule)

    elif ttype == "surface_name":
        # We'll do substring search on the full original text
        surface_name_rules.append(rule)

print(
    f"Loaded {len(RAW_RULES)} rules: "
    f"{len(lemma_index)} lemma keys, "
    f"{len(surface_index)} surface keys, "
    f"{len(surface_name_rules)} surface_name rules."
)


# ---------- NLP HELPERS ----------

def analyze_tokens(text: str, lang: str) -> List[Token]:
    """Run spaCy for the given lang and return our Token objects."""
    if lang == "sl":
        doc = nlp_sl(text)
    else:
        doc = nlp_it(text)

    tokens: List[Token] = []
    for t in doc:
        tokens.append(
            Token(
                text=t.text,
                lemma=t.lemma_,
                pos=t.pos_,
                start=t.idx,
                end=t.idx + len(t.text),
            )
        )
    return tokens


def applicable_to_lang(rule: Dict[str, Any], lang: str) -> bool:
    """Check if a rule applies to a given language code."""
    rlang = rule.get("lang")
    if rlang is None:
        return True
    if rlang == lang:
        return True
    if rlang == "it-sl" and lang in {"it", "sl"}:
        return True
    return False


# ---------- MATCHING LOGIC ----------

def match_rules(text: str, tokens: List[Token], lang: str) -> List[Issue]:
    issues: List[Issue] = []

    # 1) lemma-based rules (paronymi, prepovedani, nepravilni, odsvetovani)
    for tok in tokens:
        lemma_l = tok.lemma.lower()
        for rule in lemma_index.get(lemma_l, []):
            if not applicable_to_lang(rule, lang):
                continue
            issues.append(
                Issue(
                    rule_id=rule["id"],
                    category=rule["category"],
                    start=tok.start,
                    end=tok.end,
                    priority=rule.get("priority", 0),
                    payload=rule.get("payload", {}),
                )
            )

    # 2) surface (single-token) rules (slogovni, etc.)
    for tok in tokens:
        for rule in surface_index.get(tok.text, []):
            if not applicable_to_lang(rule, lang):
                continue
            issues.append(
                Issue(
                    rule_id=rule["id"],
                    category=rule["category"],
                    start=tok.start,
                    end=tok.end,
                    priority=rule.get("priority", 0),
                    payload=rule.get("payload", {}),
                )
            )

    # 3) surface_name rules (multi-word toponyms etc.) via substring search
    for rule in surface_name_rules:
        if not applicable_to_lang(rule, lang):
            continue
        trig = rule.get("trigger", {})
        forms = trig.get("forms", [])
        for form in forms:
            if not form:
                continue
            start_pos = 0
            while True:
                idx = text.find(form, start_pos)
                if idx == -1:
                    break
                end = idx + len(form)
                issues.append(
                    Issue(
                        rule_id=rule["id"],
                        category=rule["category"],
                        start=idx,
                        end=end,
                        priority=rule.get("priority", 0),
                        payload=rule.get("payload", {}),
                    )
                )
                start_pos = end

    # 4) Resolve overlaps for identical spans: keep highest-priority issue
    grouped: Dict[tuple, List[Issue]] = defaultdict(list)
    for iss in issues:
        grouped[(iss.start, iss.end)].append(iss)

    final_issues: List[Issue] = []
    for (start, end), group in grouped.items():
        group_sorted = sorted(group, key=lambda x: x.priority, reverse=True)
        final_issues.append(group_sorted[0])

    # Sort by position, then priority for nicer output
    final_issues.sort(key=lambda x: (x.start, -x.priority))

    return final_issues


# ---------- FASTAPI APP ----------

app = FastAPI(title="Loris / CrossTerm NLP service (spaCy-only)")


@app.get("/")
def root():
    """
    Simple health check so GET / returns 200 instead of 404.
    Handy for 'nothing happens' moments.
    """
    return {"status": "ok", "message": "NLP service is running."}


@app.post("/analyze", response_model=List[Token])
async def analyze(req: AnalyzeRequest):
    lang = req.lang.lower()
    if lang not in SUPPORTED_LANGS:
        raise HTTPException(status_code=400, detail="Unsupported language. Use 'sl' or 'it'.")
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="Text is empty.")

    tokens = analyze_tokens(req.text, lang)
    return tokens


@app.post("/loris/check", response_model=LorisResponse)
async def loris_check(req: AnalyzeRequest):
    lang = req.lang.lower()
    if lang not in SUPPORTED_LANGS:
        raise HTTPException(status_code=400, detail="Unsupported language. Use 'sl' or 'it'.")
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="Text is empty.")

    tokens = analyze_tokens(req.text, lang)
    issues = match_rules(req.text, tokens, lang)
    return LorisResponse(tokens=tokens, issues=issues)
