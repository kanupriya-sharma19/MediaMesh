"""Cached, normalized media artwork for the public landing page."""

from __future__ import annotations

import logging
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from time import monotonic
from typing import Any

from backend.mcp_servers.books_mcp import GoogleBooksClient
from backend.mcp_servers.musicbrainz_mcp import MusicBrainzClient
from backend.mcp_servers.tmdb_mcp import TMDBClient
from backend.utils.config import load_settings


logger = logging.getLogger(__name__)
_CACHE_TTL_SECONDS = 60 * 30
_MAX_ITEMS_PER_SOURCE = 8
_cache: dict[str, Any] | None = None
_cache_expires_at = 0.0
_cache_lock = Lock()


def get_landing_media() -> dict[str, list[dict[str, str]]]:
    """Return a small cached set of artwork, allowing sources to fail independently."""
    global _cache, _cache_expires_at
    with _cache_lock:
        if _cache is not None and monotonic() < _cache_expires_at:
            return _cache

    settings = load_settings()
    jobs: dict[str, Callable[[], list[dict[str, str]]]] = {
        "movies": lambda: _movies(settings.tmdb_api_key),
        "music": _music,
        "books": lambda: _books(settings.google_books_api_key),
    }
    result: dict[str, list[dict[str, str]]] = {key: [] for key in jobs}
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {executor.submit(job): source for source, job in jobs.items()}
        for future in as_completed(futures):
            source = futures[future]
            try:
                result[source] = future.result()
            except Exception:
                logger.warning("Landing media source failed: %s", source, exc_info=True)

    with _cache_lock:
        _cache = result
        _cache_expires_at = monotonic() + _CACHE_TTL_SECONDS
    return result


def _movies(api_key: str | None) -> list[dict[str, str]]:
    if not api_key:
        return []
    results = TMDBClient(api_key).search_movies("popular")
    return [
        {"type": "movie", "title": item["title"], "image_url": item["poster_url"]}
        for item in results
        if item.get("title") and item.get("poster_url")
    ][:_MAX_ITEMS_PER_SOURCE]


def _music() -> list[dict[str, str]]:
    results = MusicBrainzClient().search_recordings("tag:rock")
    return [
        {"type": "music", "title": item["title"], "image_url": item["cover_url"]}
        for item in results
        if item.get("title") and item.get("cover_url")
    ][:_MAX_ITEMS_PER_SOURCE]


def _books(api_key: str | None) -> list[dict[str, str]]:
    results = GoogleBooksClient(api_key).search_books("subject:fiction")
    return [
        {"type": "book", "title": item["title"], "image_url": item["thumbnail"]}
        for item in results
        if item.get("title") and item.get("thumbnail")
    ][:_MAX_ITEMS_PER_SOURCE]
