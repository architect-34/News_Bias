"""NDTV — National (/india) + State (/cities)."""
from .base import absolutize, dedupe_by_url, fetch, text_or_empty

SOURCES = [
    ("https://www.ndtv.com/india",  "national"),
    ("https://www.ndtv.com/cities", "state"),
]


def _parse(soup, scope: str, base_url: str) -> list[dict]:
    items: list[dict] = []
    # NDTV uses a mix of newsHdng / NwsLstPg_ttl / story_list classes.
    candidates = soup.select(
        "h2 a, h3 a, .newsHdng a, .NwsLstPg_ttl a, "
        ".story_list a, .news_Itm-cont a, a.nstory_header"
    )
    for a in candidates:
        title = text_or_empty(a)
        href = a.get("href") or ""
        if not title or len(title) < 25 or not href:
            continue
        url = absolutize(base_url, href)
        if "ndtv.com" not in url:
            continue
        snippet_el = a.find_parent().select_one("p, .newsCont, .news_Itm-cont")
        items.append({
            "title": title,
            "url": url,
            "snippet": text_or_empty(snippet_el),
            "scope": scope,
        })
    return items


def scrape() -> list[dict]:
    out: list[dict] = []
    for url, scope in SOURCES:
        soup = fetch(url)
        if soup is None:
            continue
        out.extend(_parse(soup, scope, url))
    return dedupe_by_url(out)[:40]
