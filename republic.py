"""Republic World — National. (No state section published at this URL pattern.)"""
from .base import absolutize, dedupe_by_url, fetch, text_or_empty

SOURCES = [
    ("https://www.republicworld.com/india-news", "national"),
]


def _parse(soup, scope: str, base_url: str) -> list[dict]:
    items: list[dict] = []
    candidates = soup.select(
        "a[href*='/india-news/'], h2 a, h3 a, .story-card a, .news-card a"
    )
    for a in candidates:
        title = text_or_empty(a) or a.get("title", "")
        href = a.get("href") or ""
        if not title or len(title) < 25 or not href:
            continue
        url = absolutize(base_url, href)
        if "republicworld.com" not in url:
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
