from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Tuple
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


class SpanMatch(BaseModel):
    """
    Span-level rule match over one or more spaCy tokens.

    token_start/token_end use Python slice semantics: token_start is inclusive,
    token_end is exclusive. token_indexes is kept for frontend convenience.
    """
    type: str
    rule_id: str
    category: str
    match_on: str
    trigger: str
    start: int
    end: int
    token_start: int
    token_end: int
    token_indexes: List[int]
    surface: str
    normalized: str
    priority: int
    payload: Dict[str, Any]


class LorisResponse(BaseModel):
    tokens: List[Token]
    issues: List[Issue]
    # New, backward-compatible field. Existing frontends can keep reading issues.
    spans: List[SpanMatch] = Field(default_factory=list)


class AnalyzeFullResponse(BaseModel):
    tokens: List[Token]
    spans: List[SpanMatch] = Field(default_factory=list)


# ---------- LOAD spaCy MODELS ----------

print("Loading spaCy Slovenian model (sl_core_news_lg)...")
# If you prefer md/sm, change this name and make sure you've downloaded it
nlp_sl = spacy.load("sl_core_news_lg")

print("Loading spaCy Italian model (it_core_news_lg)...")
nlp_it = spacy.load("it_core_news_lg")


# ---------- LOAD RULES ----------

print(f"Loading rules from {RULES_PATH}...")
with RULES_PATH.open("r", encoding="utf-8") as f:
    RULES_DATA = json.load(f)

RAW_RULES: List[Dict[str, Any]] = RULES_DATA.get("rules", [])


# ---------- NORMALIZATION / INDEX HELPERS ----------

def _norm_key(s: str) -> str:
    """Normalize user/rule text for matching: trim, squeeze whitespace, casefold."""
    return " ".join((s or "").strip().split()).casefold()


def _is_multiword(s: str) -> bool:
    """True when a rule trigger contains more than one whitespace-separated item."""
    return len((s or "").strip().split()) > 1


def _rough_token_window_cap(trigger: str, *, cushion: int = 0) -> int:
    """
    Surface names can contain punctuation that spaCy may split into separate tokens
    (e.g. d'Isonzo, Devin - Nabrežina). The cushion lets token-window matching
    still compare the original character span against the trigger.
    """
    return max(1, len((trigger or "").strip().split()) + cushion)


# Indexes for fast matching.
# Single-token triggers stay in token indexes; multi-word triggers go to span indexes.
lemma_index: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
surface_index: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

# phrase key -> [(rule, original_trigger), ...]
lemma_phrase_index: Dict[str, List[Tuple[Dict[str, Any], str]]] = defaultdict(list)
surface_phrase_index: Dict[str, List[Tuple[Dict[str, Any], str]]] = defaultdict(list)
surface_name_index: Dict[str, List[Tuple[Dict[str, Any], str]]] = defaultdict(list)

MAX_LEMMA_PHRASE_TOKENS = 1
MAX_SURFACE_PHRASE_TOKENS = 1
MAX_SURFACE_NAME_TOKENS = 1

for rule in RAW_RULES:
    trig = rule.get("trigger", {})
    ttype = trig.get("type")

    if ttype == "lemma":
        for lemma in trig.get("lemmas", []):
            if not lemma:
                continue
            key = _norm_key(lemma)
            if not key:
                continue
            if _is_multiword(lemma):
                lemma_phrase_index[key].append((rule, lemma))
                MAX_LEMMA_PHRASE_TOKENS = max(MAX_LEMMA_PHRASE_TOKENS, _rough_token_window_cap(lemma))
            else:
                lemma_index[key].append(rule)

    elif ttype == "surface":
        for form in trig.get("forms", []):
            if not form:
                continue
            key = _norm_key(form)
            if not key:
                continue
            if _is_multiword(form):
                surface_phrase_index[key].append((rule, form))
                MAX_SURFACE_PHRASE_TOKENS = max(
                    MAX_SURFACE_PHRASE_TOKENS,
                    _rough_token_window_cap(form, cushion=4),
                )
            else:
                surface_index[key].append(rule)

    elif ttype == "surface_name":
        for form in trig.get("forms", []):
            if not form:
                continue
            key = _norm_key(form)
            if not key:
                continue
            # surface_name is intentionally span-aware even for single-token names.
            surface_name_index[key].append((rule, form))
            MAX_SURFACE_NAME_TOKENS = max(
                MAX_SURFACE_NAME_TOKENS,
                _rough_token_window_cap(form, cushion=6),
            )

print(
    f"Loaded {len(RAW_RULES)} rules: "
    f"{len(lemma_index)} single-token lemma keys, "
    f"{len(lemma_phrase_index)} multi-token lemma keys, "
    f"{len(surface_index)} single-token surface keys, "
    f"{len(surface_phrase_index)} multi-token surface keys, "
    f"{len(surface_name_index)} surface_name keys."
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


def _make_issue(rule: Dict[str, Any], start: int, end: int) -> Issue:
    return Issue(
        rule_id=rule["id"],
        category=rule["category"],
        start=start,
        end=end,
        priority=rule.get("priority", 0),
        payload=rule.get("payload", {}),
    )


def _make_span(
    rule: Dict[str, Any],
    *,
    match_on: str,
    trigger: str,
    token_start: int,
    token_end: int,
    tokens: List[Token],
    text: str,
    normalized: str,
) -> SpanMatch:
    start = tokens[token_start].start
    end = tokens[token_end - 1].end
    span_type = "named_entity" if match_on == "surface_name" else "multiword_rule"
    if token_end - token_start == 1 and match_on != "surface_name":
        span_type = "token_rule"

    return SpanMatch(
        type=span_type,
        rule_id=rule["id"],
        category=rule["category"],
        match_on=match_on,
        trigger=trigger,
        start=start,
        end=end,
        token_start=token_start,
        token_end=token_end,
        token_indexes=list(range(token_start, token_end)),
        surface=text[start:end],
        normalized=normalized,
        priority=rule.get("priority", 0),
        payload=rule.get("payload", {}),
    )


def _window_surface_key(text: str, tokens: List[Token], start_i: int, end_i: int) -> str:
    """Normalized original text span for tokens[start_i:end_i]."""
    return _norm_key(text[tokens[start_i].start:tokens[end_i - 1].end])


def _window_lemma_key(tokens: List[Token], start_i: int, end_i: int) -> str:
    """Normalized lemma sequence for tokens[start_i:end_i]."""
    return _norm_key(" ".join(t.lemma for t in tokens[start_i:end_i] if t.lemma))


def _match_phrase_index(
    *,
    text: str,
    tokens: List[Token],
    lang: str,
    index: Dict[str, List[Tuple[Dict[str, Any], str]]],
    max_window_tokens: int,
    match_on: str,
) -> Tuple[List[Issue], List[SpanMatch]]:
    issues: List[Issue] = []
    spans: List[SpanMatch] = []

    if not tokens or not index:
        return issues, spans

    max_window = min(len(tokens), max(1, max_window_tokens))
    seen = set()

    for start_i in range(len(tokens)):
        for end_i in range(start_i + 1, min(len(tokens), start_i + max_window) + 1):
            if match_on == "lemma":
                key = _window_lemma_key(tokens, start_i, end_i)
            else:
                key = _window_surface_key(text, tokens, start_i, end_i)

            if not key:
                continue

            for rule, trigger in index.get(key, []):
                if not applicable_to_lang(rule, lang):
                    continue

                start = tokens[start_i].start
                end = tokens[end_i - 1].end
                dedupe_key = (rule.get("id"), match_on, start, end)
                if dedupe_key in seen:
                    continue
                seen.add(dedupe_key)

                issues.append(_make_issue(rule, start, end))
                spans.append(
                    _make_span(
                        rule,
                        match_on=match_on,
                        trigger=trigger,
                        token_start=start_i,
                        token_end=end_i,
                        tokens=tokens,
                        text=text,
                        normalized=key,
                    )
                )

    return issues, spans


def _resolve_issues_and_spans(
    issues: List[Issue],
    spans: List[SpanMatch],
) -> Tuple[List[Issue], List[SpanMatch]]:
    """
    Preserve the old behavior for exact-span conflicts: for identical start/end,
    keep the highest-priority issue. Then suppress lower/equal-priority issues that
    are fully contained in a longer issue of the same category.
    """
    grouped: Dict[Tuple[int, int], List[Issue]] = defaultdict(list)
    for iss in issues:
        grouped[(iss.start, iss.end)].append(iss)

    exact_best: List[Issue] = []
    for group in grouped.values():
        group_sorted = sorted(group, key=lambda x: x.priority, reverse=True)
        exact_best.append(group_sorted[0])

    exact_best.sort(key=lambda x: (x.start, -(x.end - x.start), -x.priority))

    final_issues: List[Issue] = []
    for iss in exact_best:
        iss_len = iss.end - iss.start
        contained_by_stronger = False
        for kept in final_issues:
            kept_len = kept.end - kept.start
            if kept.category != iss.category:
                continue
            if kept_len <= iss_len:
                continue
            if iss.start >= kept.start and iss.end <= kept.end and kept.priority >= iss.priority:
                contained_by_stronger = True
                break
        if not contained_by_stronger:
            final_issues.append(iss)

    final_issues.sort(key=lambda x: (x.start, -x.priority, -(x.end - x.start)))

    surviving_issue_keys = {(i.rule_id, i.category, i.start, i.end) for i in final_issues}
    span_by_key: Dict[Tuple[str, str, int, int, str], SpanMatch] = {}
    for sp in spans:
        if (sp.rule_id, sp.category, sp.start, sp.end) not in surviving_issue_keys:
            continue
        key = (sp.rule_id, sp.category, sp.start, sp.end, sp.match_on)
        current = span_by_key.get(key)
        if current is None or sp.priority > current.priority:
            span_by_key[key] = sp

    final_spans = list(span_by_key.values())
    final_spans.sort(key=lambda x: (x.start, -x.priority, -(x.end - x.start), x.match_on))
    return final_issues, final_spans


# ---------- MATCHING LOGIC ----------

def match_rules(text: str, tokens: List[Token], lang: str) -> Tuple[List[Issue], List[SpanMatch]]:
    issues: List[Issue] = []
    spans: List[SpanMatch] = []

    # 1) lemma-based single-token rules (paronymi, prepovedani, nepravilni, odsvetovani)
    for tok in tokens:
        lemma_key = _norm_key(tok.lemma)
        if not lemma_key:
            continue
        for rule in lemma_index.get(lemma_key, []):
            if not applicable_to_lang(rule, lang):
                continue
            issues.append(_make_issue(rule, tok.start, tok.end))

    # 2) surface single-token rules (slogovni, etc.)
    for tok in tokens:
        surface_key = _norm_key(tok.text)
        if not surface_key:
            continue
        for rule in surface_index.get(surface_key, []):
            if not applicable_to_lang(rule, lang):
                continue
            issues.append(_make_issue(rule, tok.start, tok.end))

    # 3) multi-token lemma rules, e.g. "compact disc", "okoristiti se"
    phrase_issues, phrase_spans = _match_phrase_index(
        text=text,
        tokens=tokens,
        lang=lang,
        index=lemma_phrase_index,
        max_window_tokens=MAX_LEMMA_PHRASE_TOKENS,
        match_on="lemma",
    )
    issues.extend(phrase_issues)
    spans.extend(phrase_spans)

    # 4) multi-token surface rules, e.g. "z otroci", "odpri lučke"
    phrase_issues, phrase_spans = _match_phrase_index(
        text=text,
        tokens=tokens,
        lang=lang,
        index=surface_phrase_index,
        max_window_tokens=MAX_SURFACE_PHRASE_TOKENS,
        match_on="surface",
    )
    issues.extend(phrase_issues)
    spans.extend(phrase_spans)

    # 5) surface_name rules: token-aware span matching instead of raw text.find().
    phrase_issues, phrase_spans = _match_phrase_index(
        text=text,
        tokens=tokens,
        lang=lang,
        index=surface_name_index,
        max_window_tokens=MAX_SURFACE_NAME_TOKENS,
        match_on="surface_name",
    )
    issues.extend(phrase_issues)
    spans.extend(phrase_spans)

    return _resolve_issues_and_spans(issues, spans)


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


@app.post("/analyze-full", response_model=AnalyzeFullResponse)
async def analyze_full(req: AnalyzeRequest):
    """
    Token analysis plus span-level LORIS/MWU matches.

    /analyze stays token-only for old clients. This endpoint gives frontends
    and LingHub a stable place to catch multi-word units, toponyms, and other
    rule spans without overloading token objects.
    """
    lang = req.lang.lower()
    if lang not in SUPPORTED_LANGS:
        raise HTTPException(status_code=400, detail="Unsupported language. Use 'sl' or 'it'.")
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="Text is empty.")

    tokens = analyze_tokens(req.text, lang)
    _, spans = match_rules(req.text, tokens, lang)
    return AnalyzeFullResponse(tokens=tokens, spans=spans)


@app.post("/loris/check", response_model=LorisResponse)
async def loris_check(req: AnalyzeRequest):
    lang = req.lang.lower()
    if lang not in SUPPORTED_LANGS:
        raise HTTPException(status_code=400, detail="Unsupported language. Use 'sl' or 'it'.")
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="Text is empty.")

    tokens = analyze_tokens(req.text, lang)
    issues, spans = match_rules(req.text, tokens, lang)
    return LorisResponse(tokens=tokens, issues=issues, spans=spans)
