"""The Hindu — National + State."""
from .base import absolutize, dedupe_by_url, fetch, text_or_empty

SOURCES = [
    ("https://www.thehindu.com/news/national/", "national"),
    ("https://www.thehindu.com/news/states/",   "state"),
]


def _parse(soup, scope: str, base_url: str) -> list[dict]:
    items: list[dict] = []
    # The Hindu uses .title a / h3.title a + a .intro paragraph nearby.
    candidates = soup.select(
        "h3.title a, h2.title a, .title a, .story-card-news h3 a, "
        "div.element a[href*='/news/']"
    )
    for a in candidates:
        title = text_or_empty(a)
        href = a.get("href") or ""
        if not title or len(title) < 25 or not href:
            continue
        url = absolutize(base_url, href)
        if "thehindu.com" not in url:
            continue
        parent = a.find_parent()
        snippet_el = parent.select_one(".intro, p") if parent else None
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
