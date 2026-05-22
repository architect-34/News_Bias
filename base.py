"""Shared scraping primitives."""
from __future__ import annotations

import logging
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

log = logging.getLogger("scraper")

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "en-IN,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

REQUEST_TIMEOUT = 15


def fetch(url: str) -> BeautifulSoup | None:
    """GET a URL and return parsed soup, or None on failure."""
    try:
        r = requests.get(url, headers=DEFAULT_HEADERS, timeout=REQUEST_TIMEOUT)
        r.raise_for_status()
    except requests.RequestException as e:
        log.warning("fetch failed: %s — %s", url, e)
        return None
    return BeautifulSoup(r.text, "lxml")


def absolutize(base: str, href: str) -> str:
    return urljoin(base, href)


def text_or_empty(el) -> str:
    return el.get_text(strip=True) if el else ""


def dedupe_by_url(items: list[dict]) -> list[dict]:
    seen = set()
    out = []
    for it in items:
        u = it.get("url")
        if not u or u in seen:
            continue
        seen.add(u)
        out.append(it)
    return out
