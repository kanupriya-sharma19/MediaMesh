"""TMDB MCP server for structured movie and credit data."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import requests
from mcp.server.fastmcp import FastMCP

from utils.config import load_settings


logger = logging.getLogger(__name__)

TMDB_API_URL = "https://api.themoviedb.org/3"
TMDB_IMAGE_URL = "https://image.tmdb.org/t/p/w500"


class TMDBAPIError(RuntimeError):
    """Raised when TMDB cannot fulfill a request."""


@dataclass
class TMDBClient:
    """Client for TMDB's API-key authenticated endpoints."""

    api_key: str
    session: requests.Session | None = None
    api_url: str = TMDB_API_URL
    image_url: str = TMDB_IMAGE_URL
    request_timeout: float = 20.0

    def __post_init__(self) -> None:
        self.session = self.session or requests.Session()

    def _request(self, path: str, **params: Any) -> dict[str, Any]:
        params["api_key"] = self.api_key
        try:
            response = self.session.get(
                f"{self.api_url}{path}",
                params=params,
                timeout=self.request_timeout,
            )
        except requests.RequestException as exc:
            raise TMDBAPIError("TMDB API request failed") from exc

        if response.status_code == 429:
            raise TMDBAPIError("TMDB rate limit reached; try again later")
        if response.status_code >= 400:
            raise TMDBAPIError(_response_message(response, "TMDB API request failed"))
        return _json_object(response, "TMDB returned malformed data")

    def search_movies(self, query: str) -> list[dict[str, Any]]:
        payload = self._request(
            "/search/movie", query=query, include_adult=False, page=1
        )
        results = payload.get("results")
        if not isinstance(results, list) or not all(
            isinstance(movie, dict) for movie in results
        ):
            raise TMDBAPIError("TMDB returned malformed movie results")
        return [self._normalize_movie(movie) for movie in results]

    def get_movie(self, movie_id: int) -> dict[str, Any]:
        return self._normalize_movie(self._request(f"/movie/{movie_id}"))

    def get_movie_credits(self, movie_id: int) -> dict[str, list[dict[str, Any]]]:
        payload = self._request(f"/movie/{movie_id}/credits")
        cast = payload.get("cast", [])
        crew = payload.get("crew", [])
        if not isinstance(cast, list) or not isinstance(crew, list):
            raise TMDBAPIError("TMDB returned malformed credit results")
        return {
            "cast": [
                _normalize_cast_member(member)
                for member in cast
                if isinstance(member, dict)
            ],
            "crew": [
                _normalize_crew_member(member)
                for member in crew
                if isinstance(member, dict)
            ],
        }

    def _normalize_movie(self, movie: dict[str, Any]) -> dict[str, Any]:
        poster_path = movie.get("poster_path")
        production_companies = movie.get("production_companies", [])
        if not isinstance(production_companies, list):
            production_companies = []
        return {
            "movie_id": movie.get("id"),
            "title": movie.get("title") or movie.get("original_title"),
            "release_date": movie.get("release_date"),
            "overview": movie.get("overview"),
            "poster_url": f"{self.image_url}{poster_path}" if poster_path else None,
            "production_companies": [
                _normalize_company(company)
                for company in production_companies
                if isinstance(company, dict)
            ],
        }


def _json_object(response: requests.Response, error_message: str) -> dict[str, Any]:
    try:
        payload = response.json()
    except ValueError as exc:
        raise TMDBAPIError(error_message) from exc
    if not isinstance(payload, dict):
        raise TMDBAPIError(error_message)
    return payload


def _response_message(response: requests.Response, fallback: str) -> str:
    try:
        payload = response.json()
    except ValueError:
        return fallback
    detail = payload.get("status_message") if isinstance(payload, dict) else None
    return f"{fallback}: {detail}" if detail else fallback


def _normalize_company(company: dict[str, Any]) -> dict[str, Any]:
    return {
        "company_id": company.get("id"),
        "name": company.get("name"),
        "origin_country": company.get("origin_country"),
    }


def _normalize_cast_member(member: dict[str, Any]) -> dict[str, Any]:
    return {
        "person_id": member.get("id"),
        "name": member.get("name"),
        "character": member.get("character"),
        "order": member.get("order"),
    }


def _normalize_crew_member(member: dict[str, Any]) -> dict[str, Any]:
    return {
        "person_id": member.get("id"),
        "name": member.get("name"),
        "department": member.get("department"),
        "job": member.get("job"),
    }


def _client_from_environment() -> TMDBClient:
    settings = load_settings()
    if not settings.tmdb_api_key:
        raise TMDBAPIError("TMDB API key is missing. Set TMDB_API_KEY in .env.")
    return TMDBClient(settings.tmdb_api_key)


def _validate_movie_id(movie_id: int) -> str | None:
    if movie_id <= 0:
        return "TMDB movie ID must be a positive integer"
    return None


def _tool_error(exc: TMDBAPIError) -> dict[str, str]:
    logger.warning("TMDB MCP tool failed: %s", exc)
    return {"error": str(exc)}


mcp = FastMCP("TMDB")


@mcp.tool()
def search_movies(query: str) -> dict[str, Any]:
    """Search TMDB and return normalized movie metadata."""
    if not query.strip():
        return {"error": "Movie search query cannot be empty"}
    try:
        return {"movies": _client_from_environment().search_movies(query)}
    except TMDBAPIError as exc:
        return _tool_error(exc)


@mcp.tool()
def get_movie(movie_id: int) -> dict[str, Any]:
    """Get normalized movie metadata, including structured production companies."""
    validation_error = _validate_movie_id(movie_id)
    if validation_error:
        return {"error": validation_error}
    try:
        return _client_from_environment().get_movie(movie_id)
    except TMDBAPIError as exc:
        return _tool_error(exc)


@mcp.tool()
def get_movie_credits(movie_id: int) -> dict[str, Any]:
    """Get normalized cast and crew credits for a TMDB movie."""
    validation_error = _validate_movie_id(movie_id)
    if validation_error:
        return {"error": validation_error}
    try:
        return _client_from_environment().get_movie_credits(movie_id)
    except TMDBAPIError as exc:
        return _tool_error(exc)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
    mcp.run(transport="stdio")
