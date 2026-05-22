"""
Six-Lens bias engine for India Media Pulse.

This module replaces the earlier Left/Right binary with a multi-dimensional
`BiasProfile`. Per article we compute:

  Lens 1 — Statist / Nationalist narrative      → statist_score
  Lens 2 — Caste & representation               → caste_signals
  Lens 3 — Lexical framing                      → lexical_score (L)
  Lens 4 — Ownership influence                  → ownership_score (O)
  Lens 5 — Regional / translation gap           → vernacular_flag
  Lens 6 — Visual / placement bias              → headline_body_gap

Plus source-categorisation (S) — Official : Independent : Affected ratio.

The Weighted Bias Index (WBI) is:

    WBI = w1·S + w2·L + w3·O          (w3 highest, per spec)

All scores are signed in [-1, +1] where positive = state-aligned / pro-
establishment and negative = adversarial / dissenting.

The function returns a flat dict that contains both the legacy fields (so the
existing card UI still works) and the new `bias_profile` sub-object that the
new UI consumes.
"""
from __future__ import annotations

import re

from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

from . import lexicons as lex
from .conglomerates import (
    CONGLOMERATE_INTERESTS,
    conflict_topics_for,
    sectors_for,
)

_analyzer = SentimentIntensityAnalyzer()

# ---------- WBI weights ----------
# Four lenses contribute to the WBI: Source (S), Lexical (L), Ownership (O),
# Partisan polarity (P). Ownership is ALWAYS present (uses publisher prior as
# a baseline when no sector match), and carries 50% of the WBI by design —
# the corpus is short Indian-English political copy where who-owns-the-press
# is the most stable signal.
W_SOURCE    = 0.15   # w1
W_LEXICAL   = 0.20   # w2
W_OWNERSHIP = 0.50   # w3  (dominant — see comment above)
W_PARTISAN  = 0.15   # w4

# Volatility exponent. We sharpen scores away from zero with sign(x)·|x|^V
# so that mild signals become more decisive without saturating at ±1.
# V = 0.55 means: raw 0.10 → 0.30, raw 0.50 → 0.69, raw 1.00 → 1.00.
VOLATILITY_EXPONENT = 0.55


def _sharpen(x: float, exponent: float = VOLATILITY_EXPONENT) -> float:
    """Push a signed value away from zero without saturating."""
    if x == 0:
        return 0.0
    sign = 1.0 if x > 0 else -1.0
    return sign * (abs(x) ** exponent)

# ---------- Party keyword scan (carry-over, used for tagging UI chips) -----
PARTY_KEYWORDS = {
    "BJP":      [r"\bBJP\b", r"\bBharatiya Janata\b"],
    "INC":      [r"\bCongress\b", r"\bINC\b"],
    "AAP":      [r"\bAAP\b", r"\bAam Aadmi\b"],
    "TMC":      [r"\bTMC\b", r"\bTrinamool\b"],
    "DMK":      [r"\bDMK\b"],
    "AIADMK":   [r"\bAIADMK\b"],
    "SP":       [r"\bSamajwadi\b"],
    "BSP":      [r"\bBSP\b", r"\bBahujan Samaj\b"],
    "CPI(M)":   [r"\bCPI\(M\)\b", r"\bCPM\b"],
    "Shiv Sena": [r"\bShiv Sena\b"],
    "NCP":      [r"\bNCP\b"],
}

STATES = [
    "Maharashtra", "Uttar Pradesh", "Delhi", "Karnataka", "Tamil Nadu",
    "West Bengal", "Bihar", "Gujarat", "Rajasthan", "Madhya Pradesh",
    "Kerala", "Telangana", "Andhra Pradesh", "Punjab", "Haryana",
    "Odisha", "Assam", "Jharkhand", "Chhattisgarh", "Uttarakhand",
    "Himachal Pradesh", "Goa", "Manipur", "Tripura", "Meghalaya",
    "Nagaland", "Mizoram", "Arunachal Pradesh", "Sikkim",
    "Jammu and Kashmir", "Ladakh",
]
CITY_TO_STATE = {
    "Mumbai": "Maharashtra", "Pune": "Maharashtra", "Nagpur": "Maharashtra",
    "Lucknow": "Uttar Pradesh", "Varanasi": "Uttar Pradesh", "Noida": "Uttar Pradesh",
    "Bengaluru": "Karnataka", "Bangalore": "Karnataka",
    "Chennai": "Tamil Nadu", "Coimbatore": "Tamil Nadu",
    "Kolkata": "West Bengal", "Hyderabad": "Telangana",
    "Ahmedabad": "Gujarat", "Surat": "Gujarat",
    "Jaipur": "Rajasthan",
    "Bhopal": "Madhya Pradesh", "Indore": "Madhya Pradesh",
    "Thiruvananthapuram": "Kerala", "Kochi": "Kerala",
    "Patna": "Bihar", "Bhubaneswar": "Odisha",
    "Guwahati": "Assam", "Chandigarh": "Punjab",
    "Gurgaon": "Haryana", "Gurugram": "Haryana",
    "Srinagar": "Jammu and Kashmir",
}


# ---------------------------------------------------------------------------
# Carry-over helpers.
# ---------------------------------------------------------------------------
def detect_parties(text: str) -> list[str]:
    hits = []
    for label, patterns in PARTY_KEYWORDS.items():
        for p in patterns:
            if re.search(p, text, flags=re.IGNORECASE):
                hits.append(label)
                break
    return hits


def detect_state(text: str) -> str | None:
    for s in STATES:
        if re.search(rf"\b{re.escape(s)}\b", text, flags=re.IGNORECASE):
            return s
    for city, state in CITY_TO_STATE.items():
        if re.search(rf"\b{re.escape(city)}\b", text, flags=re.IGNORECASE):
            return state
    return None


def score_sentiment(text: str) -> float:
    if not text:
        return 0.0
    return _analyzer.polarity_scores(text)["compound"]


# ---------------------------------------------------------------------------
# Lens 4 (S) — Source weighting.
# Counts substring occurrences of official / independent / affected source
# patterns, computes the Official : Independent ratio, and emits a signed
# *statist bias* score in [-1, +1].
# ---------------------------------------------------------------------------
def score_sources(text: str) -> dict:
    lowered = text.lower()
    counts = {kind: 0 for kind in lex.SOURCE_PATTERNS}
    matched: dict[str, list[str]] = {kind: [] for kind in lex.SOURCE_PATTERNS}

    for kind, patterns in lex.SOURCE_PATTERNS.items():
        for p in patterns:
            n = lowered.count(p.lower())
            if n:
                counts[kind] += n
                matched[kind].append(p)

    official = counts["Official"]
    independent = counts["Independent"]
    affected = counts["Affected"]

    # Ratio with a +1 smoothing to avoid divide-by-zero.
    ratio = official / max(independent, 1)

    # Statist bias score in [-1, +1]:
    #   ratio > 3   → 'access journalism' territory → +0.7..+1.0
    #   ratio ~ 1   → balanced → 0
    #   independent > official → adversarial framing → negative
    if ratio >= 3:
        statist = min(1.0, 0.6 + 0.1 * (ratio - 3))
    elif ratio >= 1:
        statist = 0.2 * (ratio - 1)
    elif independent + affected > 0:
        statist = -min(1.0, 0.3 * (independent + affected) - 0.2)
    else:
        statist = 0.0  # no quoted sources detected

    return {
        "counts": counts,
        "ratio_official_to_independent": round(ratio, 2),
        "score": round(statist, 3),  # S
        "matched": {k: v[:5] for k, v in matched.items()},
    }


# ---------------------------------------------------------------------------
# Lens 3 (L) — Lexical framing.
# Scans for loaded adjectives + framing pairs. Returns a signed score where
# positive = state-aligned, negative = dissent-aligned.
# ---------------------------------------------------------------------------
def score_lexical(text: str) -> dict:
    pro_hits = lex.find_any(text, lex.EMOTIVE_PRO_ESTABLISHMENT)
    anti_hits = lex.find_any(text, lex.EMOTIVE_ANTI_ESTABLISHMENT)
    # Direction-neutral intensity markers (slams / blasts / lambasts / scathing).
    verb_hits = lex.find_any(text, lex.HEADLINE_LOADED_VERBS)

    pair_hits = []
    pair_score = 0.0
    for loaded, neutral, sign in lex.LEXICAL_PAIRS + lex.PROTEST_FRAMING:
        if re.search(rf"\b{re.escape(loaded)}\b", text, flags=re.IGNORECASE):
            # If the neutral counterpart is *also* present, the article is
            # contrasting framings — half-credit only.
            neutral_present = bool(
                re.search(rf"\b{re.escape(neutral)}\b", text, flags=re.IGNORECASE)
            )
            multiplier = 0.5 if neutral_present else 1.0
            pair_hits.append({"loaded": loaded, "neutral_present": neutral_present})
            pair_score += sign * 0.25 * multiplier

    # Adjective net score: each pro tilts +0.3, each anti tilts -0.3.
    # Bumped from 0.2 → 0.3 to amplify volatility per the user spec.
    adj_score = 0.3 * len(pro_hits) - 0.3 * len(anti_hits)

    raw = adj_score + pair_score
    # Apply volatility sharpener — small lexical signals become decisive.
    score = max(-1.0, min(1.0, _sharpen(raw)))

    # Total lexical-loading evidence — used to gate Linguistic Elitism.
    intensity = len(pro_hits) + len(anti_hits) + len(pair_hits) + len(verb_hits)

    return {
        "score": round(score, 3),  # L (signed)
        "intensity": intensity,    # unsigned count of all loaded markers
        "pro_establishment": pro_hits,
        "anti_establishment": anti_hits,
        "loaded_verbs": verb_hits,
        "pair_hits": pair_hits,
    }


# ---------------------------------------------------------------------------
# Lens 4 (O) — Ownership influence.
# Combines:
#   (a) sector match — does the article cover a sector the owner is in?
#   (b) conflict topic match — does it touch a known reputational risk?
#   (c) framing direction — if a sector match exists AND lexical framing is
#       pro-establishment, the conflict score is amplified.
# ---------------------------------------------------------------------------
def score_ownership(publisher_id: str, text: str, lexical_score: float,
                     publisher_prior: float = 0.0) -> dict:
    """
    Ownership lens (O) — ALWAYS contributes a score.

    Even when the article doesn't touch the owner's sector portfolio, the
    publisher's historical bias factor is folded in as a baseline. This is
    why W_OWNERSHIP is the dominant weight: the structural fact of *who
    owns the press* should colour every story it publishes.

    Sector / conflict-topic hits add magnitude on top of the baseline, with
    framing direction (positive lexical → amplify, negative → dampen).
    """
    sectors = sectors_for(publisher_id)
    conflicts = conflict_topics_for(publisher_id)

    sector_hits = lex.find_any(text, sectors)
    conflict_hits = lex.find_any(text, conflicts)

    # Baseline = publisher's historical prior, slightly compressed so a
    # single article never gets ±1 just from publisher identity.
    baseline = 0.75 * publisher_prior

    if not sector_hits and not conflict_hits:
        return {
            "score": round(max(-1.0, min(1.0, baseline)), 3),
            "sector_hits": [],
            "conflict_topic_hits": [],
            "sector_match": False,
            "baseline_only": True,
        }

    # Sector or conflict-topic match — add magnitude in the prior's direction.
    boost = min(0.5, 0.2 * len(sector_hits) + 0.3 * len(conflict_hits))
    direction = 1.0 if baseline >= 0 else -1.0

    if lexical_score > 0.1:
        amplifier = 1.0 + min(0.5, lexical_score)
    elif lexical_score < -0.1:
        amplifier = max(0.5, 1.0 + lexical_score)
    else:
        amplifier = 1.0

    score = baseline + direction * boost * amplifier
    return {
        "score": round(max(-1.0, min(1.0, score)), 3),
        "sector_hits": sector_hits,
        "conflict_topic_hits": conflict_hits,
        "sector_match": bool(sector_hits),
        "baseline_only": False,
    }


# ---------------------------------------------------------------------------
# Lens 1 — Statist / nationalist narrative labels.
# ---------------------------------------------------------------------------
def detect_nationalist_signals(text: str) -> dict:
    labels = [l for l in lex.NATIONALIST_LABELS
              if re.search(rf"\b{re.escape(l)}\b", text, flags=re.IGNORECASE)]
    official_certainty = lex.count_patterns(text, lex.STATIST_VERBS["official_certainty"])
    dissent_qualified  = lex.count_patterns(text, lex.STATIST_VERBS["dissent_qualified"])

    # Signed signal: more 'official said' + 'alleged' = more statist framing.
    signal = 0.15 * official_certainty + 0.15 * dissent_qualified + 0.4 * len(labels)
    signal = min(1.0, signal)

    return {
        "labels": labels,
        "official_certainty_count": official_certainty,
        "dissent_qualified_count":  dissent_qualified,
        "score": round(signal, 3),
    }


# ---------------------------------------------------------------------------
# Lens 2 — Caste & representation signals.
# Conservative: we only fire if the article is *about* caste/community and
# also contains meritocracy framing OR passive-voice violence reporting OR
# only-dominant-surname quotes.
# ---------------------------------------------------------------------------
def detect_caste_signals(text: str) -> dict:
    context_present = any(
        re.search(rf"\b{re.escape(c)}\b", text, flags=re.IGNORECASE)
        for c in lex.CASTE_CONTEXT_CUES
    )
    meritocracy = lex.count_patterns(text, lex.MERITOCRACY_TROPES)
    passive_violence = lex.count_patterns(text, lex.PASSIVE_VIOLENCE_PATTERNS)

    # Crude surname presence check (used to flag *absence* of marginalised voices).
    words = set(re.findall(r"[A-Z][a-z]+", text))
    dominant_quoted = sorted(words & lex.DOMINANT_SURNAMES)
    marginalised_quoted = sorted(words & lex.MARGINALISED_SURNAMES)

    # Fires when the story is *about* caste/community and the framing carries
    # any of: meritocracy rhetoric, passive-voice violence, or visibly skewed
    # representation (dominant surnames present without any marginalised ones).
    # The surname clause is now treated as a *boost*, not a sole trigger, since
    # surnames rarely appear in snippets.
    fires = (
        context_present and (
            meritocracy > 0
            or passive_violence > 0
        )
    )
    if not fires and context_present and dominant_quoted and not marginalised_quoted:
        # Weaker signal, still useful but flagged separately so the UI can
        # decide whether to display.
        fires = True

    return {
        "context_present": context_present,
        "meritocracy_count": meritocracy,
        "passive_violence_count": passive_violence,
        "dominant_surnames_quoted": dominant_quoted,
        "marginalised_surnames_quoted": marginalised_quoted,
        "fires": fires,
    }


# ---------------------------------------------------------------------------
# Partisan Polarity lens (P) — ruling vs opposition party + sentiment polarity.
#
#   Same words mean opposite things depending on who's the subject:
#     "BJP delivers historic landmark scheme"     → pro-establishment
#     "Congress delivers historic landmark scheme" → anti-establishment
#
#   We classify the subject as ruling / opposition / both / neither and then
#   flip the sign of the headline sentiment accordingly. The result is a
#   signed score in [-1, +1] where positive = pro-ruling-party framing.
# ---------------------------------------------------------------------------
def _matches_any(text: str, patterns: list[str]) -> bool:
    return any(re.search(p, text, flags=re.IGNORECASE) for p in patterns)


def score_partisan_polarity(text: str, headline_sentiment: float) -> dict:
    ruling = _matches_any(text, lex.RULING_PARTY_PATTERNS)
    opposition = _matches_any(text, lex.OPPOSITION_PARTY_PATTERNS)

    if ruling and not opposition:
        target = "ruling"
        score = headline_sentiment            # positive about ruling = pro-est
    elif opposition and not ruling:
        target = "opposition"
        score = -headline_sentiment           # positive about opposition = anti-est
    elif ruling and opposition:
        target = "both"                       # partisan-conflict story
        score = 0.5 * headline_sentiment      # softened — both sides framed
    else:
        target = "none"
        score = 0.0

    # Sharpen the score so mild sentiment becomes a more decisive partisan signal.
    score = max(-1.0, min(1.0, _sharpen(score)))

    return {
        "score": round(score, 3),  # P
        "target": target,
        "ruling_mentioned": ruling,
        "opposition_mentioned": opposition,
    }


# ---------------------------------------------------------------------------
# Lens 6 — Headline vs body sentiment gap (proxy for placement bias).
# ---------------------------------------------------------------------------
def headline_body_gap(headline: str, body: str) -> dict:
    h = score_sentiment(headline)
    b = score_sentiment(body) if body else 0.0
    gap = abs(h - b)
    sign_flip = (h > 0.1 and b < -0.1) or (h < -0.1 and b > 0.1)
    flagged = gap >= lex.HEADLINE_BODY_GAP_THRESHOLD or sign_flip

    return {
        "headline_sentiment": round(h, 3),
        "body_sentiment":     round(b, 3),
        "gap":                round(gap, 3),
        "sign_flip":          sign_flip,
        "flagged":            flagged,
    }


# ---------------------------------------------------------------------------
# OmissionMap — flag expected critical keywords that are missing.
# ---------------------------------------------------------------------------
def detect_category(text: str) -> str | None:
    for cat, rules in lex.CATEGORY_RULES.items():
        if lex.find_any(text, rules["triggers"]):
            return cat
    return None


def compute_omissions(text: str, category: str | None) -> list[str]:
    if not category:
        return []
    expected = lex.CATEGORY_RULES[category]["expected_keywords"]
    missing = []
    for kw in expected:
        if not re.search(rf"\b{re.escape(kw)}\b", text, flags=re.IGNORECASE):
            missing.append(kw)
    return missing


# ---------------------------------------------------------------------------
# Weighted Bias Index + pattern classification.
# ---------------------------------------------------------------------------
def compute_wbi(s: float, l: float, o: float, p: float = 0.0) -> float:
    """Static-weight WBI (kept for callers that don't track data presence)."""
    raw = W_SOURCE * s + W_LEXICAL * l + W_OWNERSHIP * o + W_PARTISAN * p
    return round(max(-1.0, min(1.0, _sharpen(raw))), 3)


def compute_wbi_adaptive(
    s: float, l: float, o: float, p: float,
    s_present: bool, l_present: bool, o_present: bool, p_present: bool,
) -> tuple[float, dict]:
    """
    Adaptive WBI — redistribute weight from lenses with no data to lenses
    that did fire, then sharpen the result for volatility.

    Rationale: on headline+snippet input, several lenses frequently fire 0.
    Keeping their base weights when they contribute 0 drags the WBI toward 0
    even when other lenses are screaming.
    """
    weights = {
        "source":    W_SOURCE    if s_present else 0.0,
        "lexical":   W_LEXICAL   if l_present else 0.0,
        "ownership": W_OWNERSHIP if o_present else 0.0,
        "partisan":  W_PARTISAN  if p_present else 0.0,
    }
    total = sum(weights.values())
    if total == 0:
        return 0.0, {k: 0.0 for k in weights}

    weights = {k: v / total for k, v in weights.items()}
    raw = (weights["source"] * s + weights["lexical"] * l
           + weights["ownership"] * o + weights["partisan"] * p)
    return round(max(-1.0, min(1.0, _sharpen(raw))), 3), {k: round(v, 3) for k, v in weights.items()}


def classify_patterns(scores: dict, signals: dict, omissions: list[str]) -> list[str]:
    """
    Map the lens outputs into the four high-level patterns:
        • Communal Bias
        • Developmental Bias
        • Access Journalism
        • Linguistic Elitism

    Thresholds are tuned for headline+snippet density, NOT full article bodies,
    so they are deliberately more permissive than the spec's defaults.
    """
    patterns: list[str] = []
    src = signals["sources"]
    lx  = signals["lexical"]
    own = signals["ownership"]
    hb  = signals["headline_body"]

    # ── Communal Bias ─────────────────────────────────────────────────────
    if signals["nationalist"]["labels"] or signals["caste"]["fires"]:
        patterns.append("Communal Bias")

    # ── Access Journalism ────────────────────────────────────────────────
    # Lowered from 3:1 → 2:1, plus a "no independent voice at all" fallback.
    official = src["counts"]["Official"]
    independent = src["counts"]["Independent"]
    ratio = src["ratio_official_to_independent"]
    if ratio >= 2 or (official >= 2 and independent == 0):
        patterns.append("Access Journalism")

    # ── Developmental Bias ───────────────────────────────────────────────
    # Lowered ownership threshold 0.2 → 0.1; lowered omission count 3 → 2.
    is_infra_topic = signals["category"] in ("Infrastructure", "Mining & Energy")
    if own["sector_match"] and scores["ownership"] > 0.1:
        patterns.append("Developmental Bias")
    elif is_infra_topic and len(omissions) >= 2:
        patterns.append("Developmental Bias")

    # ── Linguistic Elitism ───────────────────────────────────────────────
    # Lowered intensity gate 2 → 1, and added a strong-sentiment fallback so
    # an emotive headline registers even if the dictionary missed every word.
    headline_sentiment = abs(hb["headline_sentiment"])
    if (
        lx["intensity"] >= 1
        or hb["flagged"]
        or headline_sentiment >= 0.4
    ):
        patterns.append("Linguistic Elitism")

    return patterns


# ---------------------------------------------------------------------------
# Legacy mapping — translate WBI + publisher prior into a single bias_label
# and colour so the existing card UI keeps working.
# ---------------------------------------------------------------------------
def _legacy_band(weighted: float) -> tuple[str, str]:
    # Green for right-leaning to match the dark/emerald frontend theme.
    if weighted < -0.2:
        return "Left-leaning", "#EF4444"      # red-500
    if weighted > 0.2:
        return "Right-leaning", "#22C55E"     # green-500
    return "Neutral / Centrist", "#71717A"    # zinc-500


# ---------------------------------------------------------------------------
# Public entrypoint — accepts full body + optional ML output.
# ---------------------------------------------------------------------------
def evaluate(headline: str, snippet: str, publisher: dict,
              body: str | None = None, ml_analysis: dict | None = None) -> dict:
    """
    Score one article. New optional args:
      body         — full article text from trafilatura (when available)
      ml_analysis  — pre-computed transformer output {sentiment_signed,
                     stance_signed, stance_scores, …}; see ml_analysis.py.

    When `body` is provided, every lexicon/regex scan runs against it
    (headline + body) rather than headline + 1-line snippet. When
    `ml_analysis` is provided, the ML sentiment + stance scores override
    the lexicon-based lexical and partisan scores.
    """
    publisher_id = publisher["id"]
    prior        = publisher.get("bias_factor", 0.0)

    # Analyse against the fullest text we have. Fall back to snippet if no body.
    primary_text = body if body else snippet or ""
    haystack = f"{headline}. {primary_text}"

    # ---- per-lens calculations ------------------------------------------
    sources    = score_sources(haystack)

    # Lexical: prefer ML sentiment when present; otherwise lexicon scan.
    lexical    = score_lexical(haystack)
    if ml_analysis and ml_analysis.get("sentiment_signed") is not None:
        # Overlay: keep lexicon evidence (pro/anti/verb hits, intensity) for
        # pattern classification, but use ML sentiment as the signed score.
        lexical["score"]      = _sharpen(ml_analysis["sentiment_signed"])
        lexical["ml_overlay"] = True
        # Bump intensity so Linguistic Elitism gates fire on high-confidence ML.
        if abs(ml_analysis["sentiment_signed"]) > 0.5:
            lexical["intensity"] = max(lexical["intensity"], 1)
    else:
        lexical["ml_overlay"] = False

    ownership  = score_ownership(publisher_id, haystack, lexical["score"], prior)
    nationalist = detect_nationalist_signals(haystack)
    caste      = detect_caste_signals(haystack)
    hb_gap     = headline_body_gap(headline, primary_text)
    category   = detect_category(haystack)
    omissions  = compute_omissions(haystack, category)

    # Partisan polarity — prefer ML zero-shot stance when present.
    partisan   = score_partisan_polarity(haystack, hb_gap["headline_sentiment"])
    if ml_analysis and ml_analysis.get("stance_signed") is not None:
        partisan["score"] = _sharpen(ml_analysis["stance_signed"])
        partisan["ml_overlay"] = True
        # If the lexicon detected no party target but ML has a confident
        # stance, mark target = ml_inferred so the lens contributes weight.
        if partisan["target"] == "none" and abs(ml_analysis["stance_signed"]) > 0.15:
            partisan["target"] = "ml_inferred"
    else:
        partisan["ml_overlay"] = False

    # ---- WBI (adaptive, four lenses) -------------------------------------
    s = sources["score"]
    l = lexical["score"]
    o = ownership["score"]
    p = partisan["score"]

    # Subject-modulate L for the WBI. The lexicon measures language tone, not
    # political polarity — "Congress slammed" is anti-OPPOSITION (i.e. pro-
    # establishment) even though "slammed" is in the anti list. Flip when the
    # detected subject is the opposition; soften when both sides appear.
    target = partisan["target"]
    if target == "opposition":
        l_for_wbi = -l
    elif target == "both":
        l_for_wbi = 0.5 * l
    else:
        l_for_wbi = l

    s_present = sum(sources["counts"].values()) > 0
    l_present = lexical["intensity"] > 0 or lexical["ml_overlay"]
    o_present = True  # Ownership is ALWAYS present (baseline = publisher prior).
    p_present = target != "none"
    wbi, effective_weights = compute_wbi_adaptive(
        s, l_for_wbi, o, p, s_present, l_present, o_present, p_present
    )

    # Light prior blend — most of the prior is already baked into O.
    weighted = round(max(-1.0, min(1.0, _sharpen(0.9 * wbi + 0.1 * prior))), 3)

    # ---- legacy fields ---------------------------------------------------
    legacy_label, legacy_color = _legacy_band(weighted)
    sentiment = hb_gap["headline_sentiment"]

    # ---- patterns --------------------------------------------------------
    signals = {
        "sources":      sources,
        "lexical":      lexical,
        "ownership":    ownership,
        "partisan":     partisan,
        "nationalist":  nationalist,
        "caste":        caste,
        "headline_body": hb_gap,
        "category":     category,
        "vernacular":   publisher_id in lex.VERNACULAR_OUTLETS,
    }
    patterns = classify_patterns(
        {"source": s, "lexical": l, "ownership": o},
        signals,
        omissions,
    )

    profile = {
        "wbi": wbi,
        "weights": {
            "source":    W_SOURCE,
            "lexical":   W_LEXICAL,
            "ownership": W_OWNERSHIP,
            "partisan":  W_PARTISAN,
        },
        "effective_weights": effective_weights,
        "data_present": {
            "source":    s_present,
            "lexical":   l_present,
            "ownership": o_present,
            "partisan":  p_present,
        },
        "scores": {
            "source_bias":         s,
            "lexical_bias":        l,
            "ownership_conflict":  o,
            "partisan_polarity":   p,
            "statist_signal":      nationalist["score"],
            "caste_signal":        1.0 if caste["fires"] else 0.0,
            "headline_body_gap":   hb_gap["gap"],
        },
        "patterns":  patterns,
        "signals":   signals,
        "omissions": omissions,
        "category":  category,
        "parent":    CONGLOMERATE_INTERESTS.get(publisher_id, {}).get("parent", ""),
        "partisan_target": partisan["target"],
        "ml": {
            "used":          bool(ml_analysis),
            "body_analysed": bool(body),
            "body_chars":    len(body) if body else 0,
            "stance":        ml_analysis.get("stance_scores", {}) if ml_analysis else {},
            "confidence":    ml_analysis.get("sentiment_confidence", 0.0) if ml_analysis else 0.0,
        },
    }

    return {
        # legacy
        "parties":        detect_parties(haystack),
        "state":          detect_state(haystack),
        "sentiment":      round(sentiment, 3),
        "weighted_bias":  weighted,
        "bias_label":     legacy_label,
        "bias_color":     legacy_color,
        # new
        "bias_profile":   profile,
    }
