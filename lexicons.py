"""
Lexicons for the Six Lenses bias engine.

Everything here is intentionally a flat, editable dictionary so that newsroom
analysts and researchers can audit and amend the rules without touching engine
code. Keep entries short and word-boundary safe.
"""
from __future__ import annotations

import re

# ---------------------------------------------------------------------------
# Lens 1 — Statist / Nationalist narrative labels.
# Presence of these phrases in headlines/snippets is a strong communal-bias
# signal regardless of the surrounding sentiment.
# ---------------------------------------------------------------------------
NATIONALIST_LABELS = [
    "Urban Naxal", "Naxal sympathiser", "Anti-National", "anti-national",
    "Desh-drohi", "Tukde Tukde", "Khan Market gang", "Andolanjeevi",
    "love jihad", "land jihad", "vote jihad", "Hindu rashtra",
    "appeasement politics", "vote bank politics", "minority appeasement",
    "presstitute", "fifth column", "Maoist", "ISI-backed", "foreign hand",
]

# Phrases that frame government statements as accepted fact vs. dissent as claims.
STATIST_VERBS = {
    "official_certainty": [
        r"\bgovernment said\b", r"\bofficial sources said\b",
        r"\bofficials confirmed\b", r"\bpolice said\b",
        r"\bcentre announced\b", r"\bcentre clarified\b",
    ],
    "dissent_qualified": [
        r"\balleged\b", r"\bclaimed\b", r"\baccused\b",
        r"\bso-called\b", r"\bpurported(ly)?\b",
    ],
}

# ---------------------------------------------------------------------------
# Lens 2 — Caste & representation.
# This is a *signal* layer, not a verdict. We flag (a) the rhetoric of
# 'merit-based' framing and (b) passive constructions when reporting violence.
# Surname lists are deliberately short and indicative — used only to spot the
# *absence* of marginalised-community voices when quoted-source counts permit.
# ---------------------------------------------------------------------------
DOMINANT_SURNAMES = {
    "Sharma", "Gupta", "Iyer", "Iyengar", "Kapoor", "Khanna", "Mehta",
    "Aggarwal", "Agarwal", "Bansal", "Chaturvedi", "Mishra", "Tiwari",
    "Pandey", "Trivedi", "Dube", "Dubey", "Joshi", "Kulkarni", "Deshpande",
    "Nair", "Menon", "Reddy", "Rao", "Bhandari",
}
MARGINALISED_SURNAMES = {
    "Valmiki", "Paswan", "Manjhi", "Murmu", "Soren", "Hembrom", "Tudu",
    "Oraon", "Munda", "Mahato", "Ravidas", "Athawale", "Khairlanji",
    "Meghwal", "Bhil", "Gond", "Kharia", "Santhal", "Lambada", "Yerukula",
}

MERITOCRACY_TROPES = [
    r"\bmerit\b", r"\bmerit-?based\b", r"\bdeserving candidate\b",
    r"\bquota culture\b", r"\bcaste politics\b", r"\bdiluting standards\b",
]

# Passive constructions that diffuse agency in violence / displacement reporting.
PASSIVE_VIOLENCE_PATTERNS = [
    r"\bwas (allegedly )?(killed|attacked|beaten|assaulted|lynched|stripped)\b",
    r"\bwere (allegedly )?(killed|attacked|beaten|assaulted|lynched|stripped)\b",
    r"\b(found|seen) lynched\b",
    r"\bclash (broke out|erupted)\b",
    r"\b(life|lives) lost\b",
    # Indian-context demolition/displacement framing — agency removed.
    r"\bhomes (were|got|stood) (razed|demolished|destroyed|flattened|bulldozed)\b",
    r"\bhouses (were|got|stood) (razed|demolished|destroyed|flattened|bulldozed)\b",
    r"\b(was|were) (forcibly )?(displaced|evicted|removed|uprooted)\b",
    r"\b(families|residents|villagers) (were|got) (displaced|evicted|removed)\b",
    r"\bbulldozer (action|drive|raj)\b",
]

# Caste-context cue words. If any of these are present in a story we treat
# passive-voice or meritocracy framing as caste-relevant.
CASTE_CONTEXT_CUES = [
    "Dalit", "Adivasi", "Tribal", "SC/ST", "Scheduled Caste",
    "Scheduled Tribe", "OBC", "reservation", "Bahujan", "Mahadalit",
]

# ---------------------------------------------------------------------------
# Lens 3 — Lexical framing pairs.
# Each pair is (loaded_term, neutral_alternative). Presence of the loaded term
# without the neutral phrasing nearby increases the lexical score in the
# direction the term implies.
# ---------------------------------------------------------------------------
LEXICAL_PAIRS = [
    # framing word, neutral counterpart, sign (-1 = sympathetic, +1 = state-aligned)
    ("agitation",       "movement",        +1),
    ("riot",            "clash",           +1),
    ("mob",             "crowd",           +1),
    ("encounter",       "shooting",        +1),
    ("infiltrator",     "migrant",         +1),
    ("rabble-rousing",  "campaigning",     +1),
    ("ill-conceived",   "untested",        -1),
    ("draconian",       "stringent",       -1),
    ("crackdown",       "enforcement",     -1),
    ("propaganda",      "messaging",       -1),
    ("witch-hunt",      "investigation",   -1),
]

# Emotive adjectives & framing verbs, split by direction.
# Lists are intentionally large (~75–100 entries each) so that even one-line
# snippets in short Indian English headlines reliably produce lexicon hits.
EMOTIVE_PRO_ESTABLISHMENT = [
    # adjectives — strength / decisiveness
    "historic", "landmark", "decisive", "bold", "transformative",
    "visionary", "iron-fisted", "resolute", "unprecedented", "stellar",
    "game-changing", "watershed", "monumental", "sweeping", "robust",
    "swift", "mega", "spectacular", "record-breaking", "milestone",
    "masterstroke", "master stroke", "strong", "firm",
    "remarkable", "exemplary", "outstanding", "phenomenal", "extraordinary",
    "powerful", "mighty", "dominant", "supreme", "triumphant",
    "successful", "dynamic", "youthful", "progressive", "fast-tracked",
    "groundbreaking", "trailblazing", "pioneering", "iconic", "indelible",
    "iron", "steely", "unflinching", "unwavering", "unstoppable",
    # framing verbs — praise / accomplishment
    "hails", "hailed", "lauds", "lauded", "praises", "praised",
    "applauded", "celebrated", "extolled", "embraces", "embraced",
    "endorses", "endorsed", "backs", "backed", "credits", "credited",
    "recognises", "recognised", "honoured", "honored",
    "ushers in", "ushered in", "unveiled", "kickstarted", "kick-started",
    "championed", "spearheaded", "trumpets", "trumpeted",
    # framing verbs — momentum / win
    "delivers", "delivered", "achieves", "achieved",
    "boosts", "boosted", "boost", "thrives", "thrived",
    "prospers", "prospered", "flourishes", "flourished",
    "soars", "soared", "surge", "surges", "surged", "doubles", "doubled",
    "skyrockets", "skyrocketed", "scales", "scaled",
    "transforms", "transformed", "rolls out", "rolled out",
    "triumphs", "triumphed", "scores", "scored",
    "wins big", "scores big", "clean sweep", "landslide",
    "rallies behind", "stern action", "tough stance", "firm stand",
    "sweeps", "swept", "clinches", "clinched", "secures", "secured",
    "anointed", "crowned", "ascends",
    # adverbs of conviction
    "decisively", "emphatically", "convincingly", "comprehensively",
    "resoundingly",
]

EMOTIVE_ANTI_ESTABLISHMENT = [
    # adjectives — critical
    "ill-conceived", "draconian", "authoritarian", "controversial",
    "divisive", "ill-thought-out", "hasty", "rushed",
    "tone-deaf", "reckless", "knee-jerk", "shocking", "disturbing",
    "alarming", "troubling", "concerning", "embarrassing",
    "humiliating", "damning", "stinging", "scathing", "blistering",
    "explosive", "deeply flawed", "fundamentally flawed",
    "poorly thought out", "outrageous", "shameful", "disgraceful",
    "appalling", "unconstitutional", "anti-democratic", "anti-people",
    "biased", "partisan", "vindictive", "sinister",
    "questionable", "dubious", "murky", "opaque",
    # critical verbs
    "slams", "slammed", "blasts", "blasted",
    "decries", "decried", "denounces", "denounced",
    "condemns", "condemned", "criticises", "criticised",
    "criticizes", "criticized", "panned", "ridicules",
    "ridiculed", "mocked", "lambasts", "lambasted",
    "berates", "berated", "censures", "censured",
    "rebukes", "rebuked", "rebuffs", "rebuffed",
    "snubs", "snubbed", "shames", "shamed",
    "disgraces", "disgraced", "humiliates", "humiliated",
    "rejects", "rejected", "dismisses", "dismissed",
    "trashes", "trashed", "skewers", "skewered",
    "demolishes", "demolished", "shreds", "shredded",
    # impact framing
    "fiasco", "debacle", "scandal", "blunder", "crisis", "chaos",
    "mess", "shambles", "in tatters", "in disarray",
    "faces flak", "under fire", "rocked", "stunned",
    "questions raised", "raises concerns", "raises questions",
    "backlash", "outcry", "outrage", "uproar", "anger", "fury",
    "furore", "stormy", "tense",
    # accountability framing
    "betrayal", "betrayed", "abandoned", "neglected", "ignored",
    "weaponised", "politicised", "communalised",
    "stalled", "delayed", "scrapped", "shelved",
    "broke down", "fell apart", "crumbled", "collapsed",
    "cornered", "trapped", "ensnared",
    "exposed", "unmasked", "unravelled",
]

# Direction-neutral intensity markers — every loaded headline verb we know.
# These bump `lex_intensity` (driving Linguistic Elitism) but don't push the
# signed lexical score themselves.
HEADLINE_LOADED_VERBS = [
    "slam", "slams", "slammed",
    "blast", "blasts", "blasted",
    "rap", "raps", "rapped",
    "fume", "fumes", "fumed",
    "rake up", "rakes up", "raked up",
    "expose", "exposes", "exposed",
    "gun for", "guns for", "gunned for",
    "hit out", "hits out", "hit back", "hits back",
    "lash out", "lashes out", "lashed out",
    "target", "targets", "targeted",
    "pull up", "pulls up", "pulled up",
    "lambast", "lambasts", "lambasted",
    "skewer", "skewers", "skewered",
    "trash", "trashes", "trashed",
    "ridicule", "ridicules", "ridiculed",
    "mock", "mocks", "mocked",
    "taunt", "taunts", "taunted",
    "jab at", "jabs at", "jabbed at",
    "thrash", "thrashes", "thrashed",
    "berate", "berates", "berated",
    "censure", "censures", "censured",
    "rebuke", "rebukes", "rebuked",
    "snub", "snubs", "snubbed",
    "torpedo", "torpedoes", "torpedoed",
    "demolish", "demolishes", "demolished",
    "shred", "shreds", "shredded",
    "dismantle", "dismantles", "dismantled",
    "obliterate", "obliterates", "obliterated",
    "outclass", "outclasses", "outclassed",
    "outwit", "outwits", "outwitted",
    "outmaneuver", "outmaneuvers", "outmaneuvered",
    "trump", "trumps", "trumped",
    "humble", "humbles", "humbled",
    "stun", "stuns", "stunned",
    "shock", "shocks", "shocked",
    "rattle", "rattles", "rattled",
    "fluster", "flusters", "flustered",
    "unnerve", "unnerves", "unnerved",
    "corner", "corners", "cornered",
    "embarrass", "embarrasses", "embarrassed",
    "shame", "shames", "shamed",
    "unmask", "unmasks", "unmasked",
    "trumpet", "trumpets", "trumpeted",
    "stinging", "scathing", "blistering",
    "explosive", "damning",
    # praise verbs
    "hail", "hails", "hailed",
    "laud", "lauds", "lauded",
    "applaud", "applauds", "applauded",
    "anoint", "anoints", "anointed",
    "endorse", "endorses", "endorsed",
    "tout", "touts", "touted",
]

# ---------------------------------------------------------------------------
# Partisan Polarity lens (P) — ruling vs opposition party detection.
# Used to interpret sentiment direction: praise of the ruling party is
# pro-establishment, praise of the opposition is anti-establishment, etc.
# Update these sets as alignments shift.
# ---------------------------------------------------------------------------
RULING_PARTY_PATTERNS = [
    # NDA / Centre
    r"\bBJP\b", r"\bBharatiya Janata\b", r"\bNDA\b",
    r"\bModi\b", r"\bNarendra Modi\b", r"\bAmit Shah\b",
    r"\bUnion Minister\b", r"\bCabinet\b", r"\bPMO\b",
    r"\bYogi\b", r"\bAdityanath\b",
    r"\bJD\(U\)\b", r"\bJDU\b", r"\bNitish Kumar\b",
    r"\bTDP\b", r"\bTelugu Desam\b", r"\bNaidu\b",
    r"\bShiv Sena \(Shinde\)\b", r"\bEknath Shinde\b",
    r"\bRSS\b", r"\bSangh Parivar\b",
]
OPPOSITION_PARTY_PATTERNS = [
    # INDIA bloc + others
    r"\bCongress\b", r"\bINC\b", r"\bRahul Gandhi\b", r"\bSonia Gandhi\b",
    r"\bKharge\b", r"\bPriyanka Gandhi\b", r"\bUPA\b", r"\bINDIA bloc\b",
    r"\bAAP\b", r"\bAam Aadmi\b", r"\bKejriwal\b", r"\bAtishi\b",
    r"\bTMC\b", r"\bTrinamool\b", r"\bMamata\b", r"\bBanerjee\b",
    r"\bDMK\b", r"\bStalin\b",
    r"\bSamajwadi\b", r"\bSP\b", r"\bAkhilesh\b",
    r"\bRJD\b", r"\bRashtriya Janata Dal\b", r"\bTejashwi\b", r"\bLalu\b",
    r"\bCPI\(M\)\b", r"\bCPM\b", r"\bCPI\b", r"\bLeft Front\b",
    r"\bNCP\b", r"\bSharad Pawar\b",
    r"\bShiv Sena \(UBT\)\b", r"\bUddhav\b", r"\bThackeray\b",
    r"\bBSP\b", r"\bMayawati\b",
]

# Lexical pairs framing protest violence — Indian-media specific.
PROTEST_FRAMING = [
    # (loaded, neutral, sign)
    ("protester shot",          "police opened fire",       +1),
    ("violence by protesters",  "police lathi-charge",      +1),
    ("law and order disturbed", "demonstrations held",      +1),
]

# ---------------------------------------------------------------------------
# Lens 4 — Source categorisation patterns.
# Used to compute the Official : Independent : Affected ratio. Patterns are
# substrings checked case-insensitively against headline + snippet.
# ---------------------------------------------------------------------------
SOURCE_PATTERNS = {
    "Official": [
        "police said", "police told", "official said", "officials said",
        "officials confirmed", "spokesperson", "ministry of",
        "government said", "government sources", "centre said", "PMO",
        "minister said", "Lok Sabha", "Rajya Sabha", "press release",
        "ED said", "CBI said", "NIA said", "ITBP", "BSF", "CRPF",
        "DGP", "SSP", "SP said", "Home Ministry",
    ],
    "Independent": [
        "professor", "academic", "analyst said", "expert said",
        "researcher", "researchers", "NGO", "civil society",
        "activist said", "activists said", "lawyer said", "advocate said",
        "rights group", "fact-checker", "think tank", "policy researcher",
        "economist said", "historian said",
    ],
    "Affected": [
        "victim", "victims", "family said", "family told", "resident said",
        "residents said", "displaced", "villagers said", "farmers said",
        "workers said", "labourers said", "survivor said", "kin said",
        "mother said", "father said", "wife said", "husband said",
    ],
}

# ---------------------------------------------------------------------------
# Lens 5 — Regional / translation gap.
# We mark vernacular outlets so the engine can apply a heavier communal-rhetoric
# scan. None of the 5 English outlets in this project are vernacular, but the
# field is left in so the lookup is the single source of truth.
# ---------------------------------------------------------------------------
VERNACULAR_OUTLETS: set[str] = set()  # e.g. {"dainik_jagran", "ananda_bazar"}

# ---------------------------------------------------------------------------
# Lens 6 — Visual / placement bias (proxy: headline vs body sentiment gap).
# A gap above this threshold flags "Headline Management".
# Lowered from 0.40 → 0.25 because we only see snippets, not full bodies, so
# the signal magnitude is smaller than the engine was originally tuned for.
# ---------------------------------------------------------------------------
HEADLINE_BODY_GAP_THRESHOLD = 0.25

# ---------------------------------------------------------------------------
# Article categorisation — used to drive the OmissionMap.
# Each category lists (a) trigger keywords and (b) keywords that *should*
# appear in any honest treatment of the topic. Absence => flagged omission.
# ---------------------------------------------------------------------------
CATEGORY_RULES = {
    "Infrastructure": {
        "triggers": [
            "highway", "expressway", "metro", "dam", "power plant",
            "construction", "project", "Gati Shakti", "Bharatmala",
            "Sagarmala", "industrial corridor", "SEZ", "smart city",
        ],
        "expected_keywords": [
            "Adivasi", "displacement", "land acquisition",
            "environmental clearance", "rehabilitation", "tribal",
            "forest rights", "gram sabha",
        ],
    },
    "Stocks & Markets": {
        "triggers": [
            "Sensex", "Nifty", "stocks", "shares", "IPO", "SEBI",
            "market cap", "FPI", "retail investor",
        ],
        "expected_keywords": [
            "regulatory failure", "SEBI probe", "manipulation",
            "retail investor", "round-tripping", "promoter pledge",
        ],
    },
    "Mining & Energy": {
        "triggers": [
            "coal", "mining", "oil block", "thermal power", "solar park",
            "renewable", "lignite", "iron ore", "bauxite",
        ],
        "expected_keywords": [
            "Adivasi", "displacement", "forest clearance", "PESA",
            "gram sabha", "environmental cost", "rehabilitation",
        ],
    },
    "Communal incident": {
        "triggers": [
            "riot", "communal", "lynching", "mob", "hate crime",
            "religious clash",
        ],
        "expected_keywords": [
            "FIR", "victim's family", "post-mortem", "police inaction",
            "bystander", "named accused",
        ],
    },
}

# ---------------------------------------------------------------------------
# Helpers.
# ---------------------------------------------------------------------------
def find_any(text: str, terms: list[str]) -> list[str]:
    """Return all `terms` whose word-bounded form appears in `text`."""
    found = []
    for t in terms:
        if re.search(rf"\b{re.escape(t)}\b", text, flags=re.IGNORECASE):
            found.append(t)
    return found


def count_patterns(text: str, patterns: list[str]) -> int:
    """Count regex pattern hits in text (case-insensitive)."""
    return sum(1 for p in patterns if re.search(p, text, flags=re.IGNORECASE))
