"""The Indian Express — National + State."""
from .base import absolutize, dedupe_by_url, fetch, text_or_empty

SOURCES = [
    ("https://indianexpress.com/section/india/",  "national"),
    ("https://indianexpress.com/section/cities/", "state"),
]


def _parse(soup, scope: str, base_url: str) -> list[dict]:
    items: list[dict] = []
    # IE uses .articles .title a and .nation .title a structures.
    candidates = soup.select(
        ".articles .title a, .nation .title a, h2.title a, h3.title a, "
        "div[class*='story'] h2 a, div[class*='story'] h3 a"
    )
    for a in candidates:
        title = text_or_empty(a) or a.get("title", "")
        href = a.get("href") or ""
        if not title or len(title) < 25 or not href:
            continue
        url = absolutize(base_url, href)
        if "indianexpress.com" not in url:
            continue
        parent = a.find_parent()
        snippet_el = parent.find_next("p") if parent else None
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
