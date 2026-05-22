"""Times of India — National (/india) + State (/city)."""
from .base import absolutize, dedupe_by_url, fetch, text_or_empty

SOURCES = [
    ("https://timesofindia.indiatimes.com/india", "national"),
    ("https://timesofindia.indiatimes.com/city",  "state"),
]


def _parse(soup, scope: str, base_url: str) -> list[dict]:
    items: list[dict] = []
    # TOI sprinkles headlines across figcaption, .w_tle, span.w_tle and plain <a>.
    candidates = soup.select(
        "figcaption a, .w_tle a, span.w_tle a, "
        "div[class*='list'] a[title], a[data-articleshow]"
    )
    for a in candidates:
        title = a.get("title") or text_or_empty(a)
        href = a.get("href") or ""
        if not title or len(title) < 25 or not href:
            continue
        url = absolutize(base_url, href)
        if "indiatimes.com" not in url:
            continue
        items.append({
            "title": title,
            "url": url,
            "snippet": "",
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
