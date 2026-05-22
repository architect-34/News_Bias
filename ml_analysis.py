"""
ML-based article analysis using HuggingFace transformers.

Two pipelines:
  1. Sentiment        — DistilBERT finetuned on SST-2 (binary positive/negative)
  2. Zero-shot stance — DeBERTa-v3-base MNLI, classifying the article against
                        political-stance candidate labels.

Both are loaded lazily on first use and cached for the process lifetime.
On the first call the transformers library will download model weights
(~700MB total) into ~/.cache/huggingface/hub/. Subsequent calls are fast.

If `transformers` or `torch` aren't installed the module reports unavailable
and bias.py falls back to the lexicon path.
"""
from __future__ import annotations

import logging
from functools import lru_cache

log = logging.getLogger("ml")

_HAS_TRANSFORMERS = False
try:
    from transformers import pipeline  # type: ignore
    _HAS_TRANSFORMERS = True
except ImportError:
    log.warning("transformers not installed — ML analysis disabled")


# Candidate labels for zero-shot political-stance classification.
# Each label describes a stance the article might take. The classifier
# emits an independent probability for each (multi_label=True).
POLITICAL_STANCE_LABELS = [
    "praises the ruling party or government",
    "criticises the ruling party or government",
    "praises the opposition parties",
    "criticises the opposition parties",
    "neutral factual reporting",
    "raises concerns about communal or caste tensions",
    "covers corporate or business interests favourably",
    "highlights corporate or government wrongdoing",
]

# Model identifiers — kept small to keep first-run downloads tolerable.
SENTIMENT_MODEL = "distilbert-base-uncased-finetuned-sst-2-english"  # ~250MB
ZEROSHOT_MODEL  = "MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli"      # ~440MB

# Most HF transformer classifiers have a 512-token input limit; ~1500 chars
# of English text fits comfortably while still capturing the framing.
MAX_INPUT_CHARS = 1500


def is_available() -> bool:
    return _HAS_TRANSFORMERS


@lru_cache(maxsize=1)
def _sentiment_pipe():
    if not _HAS_TRANSFORMERS:
        return None
    log.info("loading sentiment pipeline (%s) …", SENTIMENT_MODEL)
    return pipeline("sentiment-analysis", model=SENTIMENT_MODEL, device=-1, truncation=True)


@lru_cache(maxsize=1)
def _zeroshot_pipe():
    if not _HAS_TRANSFORMERS:
        return None
    log.info("loading zero-shot pipeline (%s) …", ZEROSHOT_MODEL)
    return pipeline("zero-shot-classification", model=ZEROSHOT_MODEL, device=-1)


def analyze_text(text: str) -> dict | None:
    """
    Run both pipelines on `text` and return a flat dict:
        {
          "sentiment_signed":    float in [-1, +1],
          "sentiment_label":     "POSITIVE" | "NEGATIVE",
          "sentiment_confidence": float in [0, 1],
          "stance_scores":       {label: probability, ...},
          "stance_signed":       float in [-1, +1],
                                 # +1 = strongly pro-establishment,
                                 # -1 = strongly anti-establishment
        }
    Returns None if ML is unavailable or the input is empty.
    """
    if not _HAS_TRANSFORMERS or not text:
        return None

    excerpt = text[:MAX_INPUT_CHARS]

    # ---------- sentiment ----------
    try:
        out = _sentiment_pipe()(excerpt)
        sentiment = out[0] if isinstance(out, list) else out
        signed = sentiment["score"] if sentiment["label"] == "POSITIVE" else -sentiment["score"]
    except Exception as e:
        log.warning("sentiment inference failed: %s", e)
        sentiment, signed = None, 0.0

    # ---------- stance (zero-shot) ----------
    try:
        zs = _zeroshot_pipe()(
            excerpt,
            candidate_labels=POLITICAL_STANCE_LABELS,
            multi_label=True,
        )
        stance = dict(zip(zs["labels"], zs["scores"]))
    except Exception as e:
        log.warning("zero-shot inference failed: %s", e)
        stance = {}

    # Map stance labels to a single signed score.
    # Pro = praise ruling + criticise opposition + corporate-favourable framing.
    # Anti = criticise ruling + praise opposition + wrongdoing-spotlight framing.
    pro = (
        stance.get("praises the ruling party or government", 0.0)
        + stance.get("criticises the opposition parties", 0.0)
        + 0.5 * stance.get("covers corporate or business interests favourably", 0.0)
    )
    anti = (
        stance.get("criticises the ruling party or government", 0.0)
        + stance.get("praises the opposition parties", 0.0)
        + 0.5 * stance.get("highlights corporate or government wrongdoing", 0.0)
    )
    stance_signed = max(-1.0, min(1.0, pro - anti))

    return {
        "sentiment_signed":      round(signed, 3),
        "sentiment_label":       sentiment["label"] if sentiment else None,
        "sentiment_confidence":  round(sentiment["score"], 3) if sentiment else 0.0,
        "stance_scores":         {k: round(v, 3) for k, v in stance.items()},
        "stance_signed":         round(stance_signed, 3),
    }


def warmup() -> None:
    """Eagerly load both models so the first real request isn't a cold start."""
    if not _HAS_TRANSFORMERS:
        return
    _sentiment_pipe()
    _zeroshot_pipe()
    log.info("ML pipelines warm")
