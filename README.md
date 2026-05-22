# India Media Pulse

A specialised political-news aggregator for Indian media. Scrapes five major English-language outlets, fetches each article's full body, runs it through a transformer-based bias engine, and presents the result on a single-page dashboard — with the publisher's ownership and historical leaning always in view.

The project's goal is **transparency, not verdicts**: every score is a heuristic profile to argue with, every lexicon and weight is editable, and every methodology choice is documented in the methodology modal in the UI.

---

## Features

- **5 outlets tracked** — NDTV, The Hindu, Republic TV, Times of India, The Indian Express. National and state desks where available.
- **Full-article analysis** — articles are fetched via `trafilatura` and scored on the complete body, not just the headline.
- **ML lexical + stance scoring** — `DistilBERT-SST-2` for sentiment, zero-shot `DeBERTa-v3-MNLI` for political stance against 8 candidate labels (praises ruling, criticises opposition, highlights wrongdoing, etc.).
- **Weighted Bias Index (WBI)** across four lenses: Source weighting (S), Lexical framing (L), Ownership influence (O), Partisan polarity (P). Ownership is the dominant weight (50%) and is always present.
- **Bias Patterns** — every article is classified into one or more of: Communal Bias, Developmental Bias, Access Journalism, Linguistic Elitism.
- **Omission Map** — for Infrastructure, Mining & Energy, Markets and Communal-incident stories, the engine flags expected-but-missing critical keywords (e.g. *Adivasi*, *displacement*, *FIR*, *environmental clearance*).
- **Dark + emerald UI** — single-page Tailwind dashboard with cursor-spotlight cards, 3D tilt on hover, scroll-reveal animations, shrinking sticky header, scroll progress bar, and horizontal-scroll arrow buttons.
- **Demo mode** — if the backend isn't running, the UI loads bundled sample data so the design is still demonstrable.
- **1-hour SQLite cache** — bodies, ML outputs, and bias profiles are all persisted so the heavy work runs at most once per hour per outlet.
- **Graceful degradation** — if `transformers` or `trafilatura` aren't installed, the system falls back to the lexicon engine on headlines + snippets.

---

## Tech stack

| Layer        | Tools                                                                    |
|--------------|--------------------------------------------------------------------------|
| Backend      | Python 3.10+, FastAPI, Uvicorn                                           |
| Scraping     | `requests`, `BeautifulSoup4`, `lxml`                                     |
| Body extract | `trafilatura`                                                            |
| ML           | `transformers`, `torch` (CPU-only is fine)                               |
| Heuristics   | `vaderSentiment` (fallback), custom lexicons + regex                     |
| Storage      | SQLite (single file, no external services)                               |
| Frontend     | Single-page HTML, Tailwind CSS (via CDN), Lucide icons, Inter font       |

---

## Quick start

```bash
git clone https://github.com/<your-handle>/india-media-pulse
cd india-media-pulse

# Install dependencies
pip install -r requirements.txt

# (Optional) CPU-only PyTorch — smaller, no CUDA wheels
pip install torch --index-url https://download.pytorch.org/whl/cpu

# Run the server
uvicorn backend.main:app --reload
```

Then open `http://localhost:8000` in your browser.

**First refresh** will:
1. Download HuggingFace model weights (~700MB, cached to `~/.cache/huggingface/`)
2. Scrape headlines from all 5 outlets
3. Fan-out body fetches (8 workers in parallel)
4. Run sentiment + zero-shot stance on each body
5. Persist everything to `cache.db`

Subsequent loads within the hour are served instantly from cache.

---

## Architecture

```
URL
 │
 ▼
[body_fetcher.py] ──── parallel fetch (8 workers) ───▶ trafilatura.extract()
 │
 ▼
body text (full article)
 │
 ▼
[ml_analysis.py]
 ├── DistilBERT-SST-2     ─▶ signed sentiment (-1..+1)
 └── DeBERTa-v3 zero-shot ─▶ 8 stance labels ─▶ signed stance (-1..+1)
 │
 ▼
[bias.py: evaluate(headline, snippet, publisher, body=, ml_analysis=)]
 │
 ├── S — Source weighting  (Official : Independent : Affected ratio)
 ├── L — Lexical           (ML sentiment overlay, lexicon fallback)
 ├── O — Ownership         (publisher prior baseline + sector match)
 └── P — Partisan polarity (ML stance overlay, lexicon fallback)
 │
 ▼
WBI = adaptive(0.15·S + 0.20·L + 0.50·O + 0.15·P), sharpened
 │
 ▼
[main.py /api/articles] ──▶ JSON ──▶ [index.html dashboard]
```

---

## The Bias Engine

### The Weighted Bias Index

```
WBI = 0.15·S + 0.20·L + 0.50·O + 0.15·P
```

Weights redistribute adaptively: if a lens has no data on a given article, its share is reallocated to the lenses that did fire. Ownership is treated as always present, so it never gets down-weighted.

The raw WBI is sharpened with `sign(x)·|x|^0.55` so mild signals become more decisive without saturating at ±1.

### The four lenses

1. **S — Source weighting.** Quoted sources tagged as Official / Independent / Affected. Ratio ≥ 2:1 official-to-independent triggers the **Access Journalism** pattern.
2. **L — Lexical framing.** ML sentiment when available (DistilBERT). Otherwise a lexicon of ~80 pro-establishment terms, ~95 anti-establishment terms, and ~100 direction-neutral loaded headline verbs (*slams, blasts, lambasts, scathing, blistering*).
3. **O — Ownership influence.** Each outlet maps to its parent group's sector portfolio (Adani → energy/coal/ports; Times Group → real estate/private treaties). The publisher's historical prior is the baseline for every article; sector or conflict-topic hits add magnitude in the prior's direction.
4. **P — Partisan polarity.** Ruling-party vs opposition party detection × headline sentiment. Praise of the ruling party reads as pro-establishment; criticism of the opposition also reads as pro-establishment. The lexical score is subject-modulated using the same logic.

### Bias Patterns

| Pattern              | Trigger                                                                             |
|----------------------|-------------------------------------------------------------------------------------|
| Communal Bias        | Nationalist labels (*Urban Naxal*, *Anti-National*) or caste signals fire           |
| Developmental Bias   | Ownership / sector match with positive framing, or omissions in infra-mining-energy |
| Access Journalism    | Official-to-Independent source ratio ≥ 2:1                                          |
| Linguistic Elitism   | Loaded vocabulary intensity ≥ 1, or flagged headline-body sentiment gap             |

### Omission Map

For each detected category (Infrastructure, Mining & Energy, Stocks & Markets, Communal incident) the engine maintains a list of *expected* keywords. Any missing from the article are surfaced as "missing context" — not as a verdict, just as a checklist for the reader.

---

## Project structure

```
india-media-pulse/
├── README.md
├── requirements.txt
├── cache.db                       # created at runtime
├── backend/
│   ├── __init__.py
│   ├── main.py                    # FastAPI app + routes
│   ├── publishers.py              # Static publisher metadata + priors
│   ├── conglomerates.py           # Owner → sector lookup
│   ├── lexicons.py                # All keyword / phrase dictionaries
│   ├── bias.py                    # The Bias Engine
│   ├── ml_analysis.py             # Transformer pipelines
│   ├── body_fetcher.py            # Parallel trafilatura fetch
│   ├── database.py                # SQLite schema + cache
│   └── scrapers/
│       ├── __init__.py
│       ├── base.py                # Shared scraping primitives
│       ├── ndtv.py
│       ├── toi.py
│       ├── hindu.py
│       ├── republic.py
│       └── indian_express.py
└── frontend/
    └── index.html                 # Single-page dashboard
```

---

## Customization

### Add a publisher
1. Append an entry to `PUBLISHERS` in `backend/publishers.py` with `id`, `name`, `owner`, `bias_factor`, etc.
2. Add an entry to `CONGLOMERATE_INTERESTS` in `backend/conglomerates.py` listing the parent group's sectors and conflict topics.
3. Write a scraper module in `backend/scrapers/` exposing a `scrape() -> list[dict]` function and register it in `backend/scrapers/__init__.py`.

### Adjust the bias factors
Edit `bias_factor` (in `backend/publishers.py`) on a scale of `-1.0` (strongly left) to `+1.0` (strongly right). These are *priors*, not verdicts.

### Expand the lexicons
Add or remove terms in `backend/lexicons.py`. The lists are intentionally flat dictionaries so newsroom analysts can audit them without touching engine code.

### Re-weight the WBI
Edit `W_SOURCE`, `W_LEXICAL`, `W_OWNERSHIP`, `W_PARTISAN` constants at the top of `backend/bias.py`.

### Swap the ML models
Change `SENTIMENT_MODEL` and `ZEROSHOT_MODEL` in `backend/ml_analysis.py` to any compatible HuggingFace model. Smaller models load faster; larger ones may produce richer stance vectors.

---

## API

| Method | Path                            | Purpose                                            |
|--------|---------------------------------|----------------------------------------------------|
| GET    | `/`                             | Serves the single-page frontend                    |
| GET    | `/api/publishers`               | Static publisher metadata                          |
| GET    | `/api/articles`                 | Aggregated articles (cached, 1-hour TTL)           |
| GET    | `/api/articles?force=true`      | Force a fresh scrape + body fetch + ML pass        |
| GET    | `/api/refresh/{publisher_id}`   | Refresh a single outlet                            |

---

## Caveats

- **The bias scores are heuristic, not verdicts.** Treat the WBI and Bias Patterns as a starting point for your own scrutiny.
- **Scrapers break.** News sites change DOM frequently; expect to maintain selectors in `backend/scrapers/*.py` as outlets evolve.
- **Republic World** uses heavy client-side rendering — `requests`-based scraping returns thin HTML. Swap in Playwright or Scrapy-Splash if you need reliable Republic coverage.
- **First model load is slow.** ~700MB of HuggingFace weights downloaded on first run. Subsequent runs are fast.
- **The ownership priors are debatable.** They are derived from public reporting and academic press-freedom indices; they are not the only valid reading.
- **The sentiment + stance models were not fine-tuned on Indian English political copy.** They are competent off-the-shelf models — strong baselines, not domain experts.

---

## Roadmap

- Fine-tune a small encoder on Indian political news for better stance classification
- Add vernacular outlets (Dainik Jagran, Anandabazar Patrika) with the Regional/Translation lens activated
- Per-state filtering directly in the API rather than client-side
- Historical view — track how a story's framing shifts across outlets over time
- Reader contributions — submit corrections to publisher priors / sector lookups

---

## License

MIT. See `LICENSE` for details. Adjust to your preference before publishing.

---

## Acknowledgements

- Static publisher metadata derived from public reporting (Reuters Institute Digital News Report, RSF World Press Freedom Index, Newslaundry, The Wire's media-ownership tracking).
- Built with FastAPI, Tailwind CSS, HuggingFace Transformers, trafilatura, VADER Sentiment, and Lucide Icons.
