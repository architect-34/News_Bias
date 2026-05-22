"""Per-publisher scraper modules. Each exposes `scrape() -> list[dict]`."""
from . import ndtv, toi, hindu, republic, indian_express

SCRAPERS = {
    "ndtv": ndtv.scrape,
    "toi": toi.scrape,
    "thehindu": hindu.scrape,
    "republic": republic.scrape,
    "indianexpress": indian_express.scrape,
}
