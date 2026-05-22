"""Fetch full article bodies in parallel using trafilatura.

trafilatura is a modern, lightweight news-article extractor that handles
most major outlets without site-specific scrapers. We pair it with
ThreadPoolExecutor so a 40-article refresh completes in ~30s rather than
~10min sequentially.
"""
from __future__ import annotations

import concurrent.futures
import logging

import requests

log = logging.getLogger("body")

try:
    import trafilatura
    _HAS_TRAFILATURA = True
except ImportError:
    _HAS_TRAFILATURA = False
    log.warning("trafilatura not installed — full body fetching disabled")

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "en-IN,en;q=0.9",
}
REQUEST_TIMEOUT = 15
MAX_BODY_CHARS = 8000  # cap stored body length; ~1800 tokens, plenty for analysis


def is_available() -> bool:
    return _HAS_TRAFILATURA


def fetch_body(url: str) -> str:
    """Return clean article text for one URL, or empty string on any failure."""
    if not _HAS_TRAFILATURA:
        return ""
    try:
        r = requests.get(url, headers=DEFAULT_HEADERS, timeout=REQUEST_TIMEOUT)
        r.raise_for_status()
    except requests.RequestException as e:
        log.debug("body GET failed: %s — %s", url, e)
        return ""
    try:
        text = trafilatura.extract(
            r.text,
            include_comments=False,
            include_tables=False,
            no_fallback=False,
        ) or ""
    except Exception as e:  # pragma: no cover — defensive
        log.debug("trafilatura extract failed: %s — %s", url, e)
        text = ""
    return text[:MAX_BODY_CHARS]


def fetch_bodies_parallel(urls: list[str], max_workers: int = 8) -> dict[str, str]:
    """Fan-out body fetching across a thread pool. Returns {url: body}."""
    if not urls:
        return {}
    if not _HAS_TRAFILATURA:
        return {u: "" for u in urls}

    results: dict[str, str] = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as pool:
        future_to_url = {pool.submit(fetch_body, url): url for url in urls}
        for future in concurrent.futures.as_completed(future_to_url):
            url = future_to_url[future]
            try:
                results[url] = future.result()
            except Exception as e:  # pragma: no cover — defensive
                log.debug("body worker raised: %s — %s", url, e)
                results[url] = ""
    return results
