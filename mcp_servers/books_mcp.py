"""Google Books MCP server for public book metadata."""

from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Any

import requests
from mcp.server.fastmcp import FastMCP

from utils.config import load_settings


logger = logging.getLogger(__name__)
GOOGLE_BOOKS_API_URL = "https://www.googleapis.com/books/v1"


class GoogleBooksAPIError(RuntimeError):
    """Raised when Google Books cannot fulfill a request."""


@dataclass
class GoogleBooksClient:
    """Client for the Google Books Volumes API."""

    api_key: str | None = None
    session: requests.Session | None = None
    api_url: str = GOOGLE_BOOKS_API_URL
    request_timeout: float = 20.0

    def __post_init__(self) -> None:
        self.session = self.session or requests.Session()

    def _request(self, path: str, **params: Any) -> dict[str, Any]:
        if self.api_key:
            params["key"] = self.api_key
        try:
            response = self.session.get(
                f"{self.api_url}{path}", params=params, timeout=self.request_timeout
            )
        except requests.RequestException as exc:
            raise GoogleBooksAPIError("Google Books API request failed") from exc
        if response.status_code == 429:
            raise GoogleBooksAPIError(
                "Google Books rate limit reached; try again later"
            )
        if response.status_code >= 400:
            raise GoogleBooksAPIError(
                _response_message(response, "Google Books API request failed")
            )
        return _json_object(response, "Google Books returned malformed data")

    def search_books(self, query: str) -> list[dict[str, Any]]:
        payload = self._request("/volumes", q=query, maxResults=20, printType="books")
        items = payload.get("items", [])
        if not isinstance(items, list) or not all(
            isinstance(item, dict) for item in items
        ):
            raise GoogleBooksAPIError("Google Books returned malformed book results")
        return [
            _normalize_book(item.get("volumeInfo", {}), item.get("id"))
            for item in items
        ]

    def get_book(self, book_id: str) -> dict[str, Any]:
        payload = self._request(f"/volumes/{book_id}")
        volume_info = payload.get("volumeInfo")
        if not isinstance(volume_info, dict):
            raise GoogleBooksAPIError("Google Books returned malformed book metadata")
        return _normalize_book(volume_info, payload.get("id") or book_id)


def _json_object(response: requests.Response, error_message: str) -> dict[str, Any]:
    try:
        payload = response.json()
    except ValueError as exc:
        raise GoogleBooksAPIError(error_message) from exc
    if not isinstance(payload, dict):
        raise GoogleBooksAPIError(error_message)
    return payload


def _response_message(response: requests.Response, fallback: str) -> str:
    try:
        payload = response.json()
    except ValueError:
        detail = getattr(response, "text", "").strip()
        return (
            f"{fallback} (HTTP {response.status_code}): {detail}"
            if detail
            else fallback
        )
    detail = (
        payload.get("error", {}).get("message")
        if isinstance(payload.get("error"), dict)
        else None
    )
    return f"{fallback} (HTTP {response.status_code}): {detail}" if detail else fallback


def _normalize_book(volume_info: dict[str, Any], book_id: Any) -> dict[str, Any]:
    image_links = volume_info.get("imageLinks", {})
    if not isinstance(image_links, dict):
        image_links = {}
    authors = volume_info.get("authors", [])
    if not isinstance(authors, list):
        authors = []
    return {
        "book_id": book_id,
        "title": volume_info.get("title"),
        "authors": [author for author in authors if isinstance(author, str)],
        "published_date": volume_info.get("publishedDate"),
        "description": volume_info.get("description"),
        "thumbnail": image_links.get("thumbnail"),
        "publisher": volume_info.get("publisher"),
        "categories": volume_info.get("categories", []),
        "page_count": volume_info.get("pageCount"),
        "language": volume_info.get("language"),
        "preview_link": volume_info.get("previewLink"),
    }


def _client_from_environment() -> GoogleBooksClient:
    settings = load_settings()
    return GoogleBooksClient(settings.google_books_api_key)


def _tool_error(exc: GoogleBooksAPIError) -> dict[str, str]:
    logger.warning("Google Books MCP tool failed: %s", exc)
    return {"error": str(exc)}


def _validate_id(book_id: str) -> str | None:
    return "Google Books book ID cannot be empty" if not book_id.strip() else None


mcp = FastMCP("GoogleBooks")


@mcp.tool()
def search_books(query: str) -> dict[str, Any]:
    """Search Google Books and return normalized book metadata."""
    if not query.strip():
        return {"error": "Book search query cannot be empty"}
    try:
        return {"books": _client_from_environment().search_books(query)}
    except GoogleBooksAPIError as exc:
        return _tool_error(exc)


@mcp.tool()
def get_book(book_id: str) -> dict[str, Any]:
    """Retrieve normalized metadata for one Google Books volume."""
    validation_error = _validate_id(book_id)
    if validation_error:
        return {"error": validation_error}
    try:
        return _client_from_environment().get_book(book_id)
    except GoogleBooksAPIError as exc:
        return _tool_error(exc)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
    mcp.run(transport="stdio")
