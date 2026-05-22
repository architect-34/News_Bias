"""India Media Pulse — FastAPI entrypoint."""
from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from . import bias as bias_mod
from . import body_fetcher
from . import database as db
from . import ml_analysis
from .publishers import PUBLISHERS, all_publishers
from .scrapers import SCRAPERS

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s — %(message)s")
log = logging.getLogger("imp")

FRONTEND_DIR = Path(__file__).parent.parent / "frontend"

app = FastAPI(title="India Media Pulse", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _startup() -> None:
    db.init_db()
    log.info("DB initialised at %s", db.DB_PATH)
    log.info("body fetcher available: %s", body_fetcher.is_available())
    log.info("ML analysis available:   %s", ml_analysis.is_available())
    # Pre-load the transformer models so the first refresh isn't a cold start.
    # Comment out if you want lazy loading on first article.
    if ml_analysis.is_available():
        try:
            ml_analysis.warmup()
        except Exception as e:
            log.warning("ML warmup failed (will retry per-request): %s", e)


def _enrich(raw: list[dict], publisher: dict) -> list[dict]:
    """
    Per article: fetch full body, run ML on body, then score with the engine.
    Falls back to title+snippet + lexicon scoring when body or ML are absent.
    """
    if not raw:
        return []

    # 1) Fan-out body fetches in parallel.
    urls = [a["url"] for a in raw]
    bodies = body_fetcher.fetch_bodies_parallel(urls, max_workers=8) if body_fetcher.is_available() else {}

    # 2) Per-article: run ML (sequential — model isn't thread-safe for inference)
    #    and then the heuristic bias engine on the combined text.
    out = []
    for art in raw:
        url = art["url"]
        body = bodies.get(url, "")
        # ML analysis on full body if present, otherwise on title+snippet.
        ml_input = body if body else f"{art['title']}. {art.get('snippet', '')}"
        ml_out = ml_analysis.analyze_text(ml_input) if ml_analysis.is_available() else None

        meta = bias_mod.evaluate(
            art["title"],
            art.get("snippet", ""),
            publisher,
            body=body or None,
            ml_analysis=ml_out,
        )
        out.append({
            **art,
            **meta,
            "body": body or None,
            "ml_analysis": ml_out,
        })
    return out


def _refresh_publisher(pub_id: str) -> list[dict]:
    """Scrape + body-fetch + ML-analyse + score + cache one publisher."""
    publisher = PUBLISHERS[pub_id]
    try:
        raw = SCRAPERS[pub_id]()
    except Exception as e:  # pragma: no cover — defensive
        log.exception("scraper crashed for %s: %s", pub_id, e)
        raw = []
    enriched = _enrich(raw, publisher)
    db.replace_articles(pub_id, enriched)
    log.info("refreshed %s — %d articles (bodies fetched, ML analysed)", pub_id, len(enriched))
    return db.load_articles(pub_id)


def _get_publisher_articles(pub_id: str, force: bool = False) -> list[dict]:
    if not force and db.cache_is_fresh(pub_id):
        cached = db.load_articles(pub_id)
        if cached:
            return cached
    return _refresh_publisher(pub_id)


# ---------- API ----------

@app.get("/api/publishers")
def api_publishers():
    return {"publishers": all_publishers()}


@app.get("/api/articles")
def api_articles(force: bool = False):
    """All articles across publishers, grouped for the homepage."""
    by_publisher: dict[str, list[dict]] = {}
    for pub_id in PUBLISHERS:
        by_publisher[pub_id] = _get_publisher_articles(pub_id, force=force)

    flat = [a for items in by_publisher.values() for a in items]

    national = [a for a in flat if a["scope"] == "national"]
    state_articles = [a for a in flat if a["scope"] == "state" or a.get("state")]

    # Group state articles by detected state.
    by_state: dict[str, list[dict]] = {}
    for a in state_articles:
        s = a.get("state") or "Unspecified"
        by_state.setdefault(s, []).append(a)
    by_state = dict(sorted(by_state.items(), key=lambda kv: (-len(kv[1]), kv[0])))

    return JSONResponse({
        "publishers": all_publishers(),
        "national": national[:60],
        "by_state": by_state,
        "counts": {pid: len(arts) for pid, arts in by_publisher.items()},
    })


@app.get("/api/refresh/{publisher_id}")
def api_refresh(publisher_id: str):
    if publisher_id not in PUBLISHERS:
        return JSONResponse({"error": "unknown publisher"}, status_code=404)
    arts = _refresh_publisher(publisher_id)
    return {"publisher_id": publisher_id, "count": len(arts)}


# ---------- Frontend ----------

@app.get("/")
def root():
    return FileResponse(FRONTEND_DIR / "index.html")


if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")
